"""Servicio central de notificaciones (Bloque D).

Orden garantizado: primero se GUARDA en la base (persistencia), después se EMITE por Channels.
La emisión se difiere hasta que la transacción en curso se confirma (`on_commit`): si la operación de
negocio se revierte, nadie recibe una alerta de algo que no ocurrió. Si Redis no responde, el error se
registra pero NO rompe el flujo de negocio: la notificación ya está en la base y se ve por la API REST.

Formato del mensaje que recibe el navegador:
    {"evento": "notificacion.nueva", "subevento": "cuidador.solicitud", "notificacion": {...}}
`subevento` es `cuidador.solicitud`, `cuidador.aprobado` o `seguridad.anomalia` según el origen.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from apps.auditoria.models import GLOBAL

from .models import Notificacion

logger = logging.getLogger(__name__)

EVENTO_NUEVA = "notificacion.nueva"
GRUPO_ADMIN_SISTEMA = "rol_ADMIN_SISTEMA"


def grupo_usuario(usuario_id):
    return f"usuario_{usuario_id}"


def grupo_admin_escolar(institucion_id):
    return f"rol_ADMIN_ESCOLAR_{institucion_id}"


def datos_notificacion(n):
    return {
        "id": n.pk,
        "tipo": n.tipo,
        "titulo": n.titulo,
        "mensaje": n.mensaje,
        "referencia": n.referencia,
        "leida": n.leida,
        "creada_en": n.creada_en.isoformat() if n.creada_en else None,
    }


# ------------------------------------------------------------------------------ Crear y emitir
def crear_y_emitir_notificacion(
    *,
    destinatario_ids,
    institucion_id,
    tipo,
    titulo,
    mensaje,
    referencia="",
    emisor_id=None,
    subevento="",
    grupo=None,
):
    """Guarda una notificación por destinatario y la publica en Channels.

    - `destinatario_ids`: un id o una lista de ids de `cuentas.Usuario`.
    - `grupo`: grupo de rol (`rol_ADMIN_SISTEMA` o `rol_ADMIN_ESCOLAR_{institucion_id}`). Se publica UN solo
      mensaje al grupo con la copia de cada destinatario; cada socket reenvía únicamente la suya (con su id,
      para poder marcarla como leída). Sin `grupo`, se publica en `usuario_{id}` de cada destinatario.
    - El mensaje NUNCA debe llevar datos personales de menores ni credenciales.
    """
    if isinstance(destinatario_ids, int):
        destinatario_ids = [destinatario_ids]
    destinatario_ids = list(dict.fromkeys(destinatario_ids))

    creadas = [
        Notificacion._base_manager.create(
            institucion_id=GLOBAL if institucion_id is None else institucion_id,
            emisor_id=emisor_id,
            destinatario_id=destinatario_id,
            tipo=tipo,
            titulo=titulo[:200],
            mensaje=mensaje[:500],
            referencia=str(referencia)[:100],
            creada_en=timezone.now(),
        )
        for destinatario_id in destinatario_ids
    ]
    if creadas:
        por_usuario = {str(n.destinatario_id): datos_notificacion(n) for n in creadas}
        if grupo:
            destinos = [(grupo, por_usuario)]
        else:
            destinos = [(grupo_usuario(uid), {uid: datos}) for uid, datos in por_usuario.items()]
        transaction.on_commit(lambda: _emitir(destinos, subevento))
    return creadas


def _emitir(destinos, subevento):
    try:
        capa = get_channel_layer()
        if capa is None:
            return
        for grupo, por_usuario in destinos:
            async_to_sync(capa.group_send)(
                grupo,
                {
                    "type": "notificacion.mensaje",  # -> NotificacionesConsumer.notificacion_mensaje
                    "evento": EVENTO_NUEVA,
                    "subevento": subevento,
                    "por_usuario": por_usuario,
                },
            )
    except Exception:  # noqa: BLE001 - un fallo de Redis no debe romper la operación de negocio
        logger.exception("No se pudo emitir la notificación en tiempo real (queda guardada en la base).")


# ---------------------------------------------------------------------------- Consultas (REST/WS)
def notificaciones_de(usuario_id):
    return Notificacion._base_manager.filter(destinatario_id=usuario_id)


def contar_no_leidas(usuario_id):
    return notificaciones_de(usuario_id).filter(leida=False).count()


def marcar_leida(usuario_id, notificacion_id):
    """Devuelve la notificación, o None si no existe o NO es del usuario (no se distingue a propósito)."""
    notificacion = notificaciones_de(usuario_id).filter(pk=notificacion_id).first()
    if notificacion and not notificacion.leida:
        notificacion.leida = True
        notificacion.leida_en = timezone.now()
        notificacion.save(update_fields=["leida", "leida_en"])
    return notificacion


def marcar_todas_leidas(usuario_id):
    return notificaciones_de(usuario_id).filter(leida=False).update(leida=True, leida_en=timezone.now())


# ---------------------------------------------------------------------------- Chat (Salas y Mensajes)
from apps.cuentas.models import Rol, Usuario
from apps.instituciones.models import Institucion
from .models import MensajeChat, SalaChat, SalaParticipante

EVENTO_CHAT_MENSAJE = "chat.mensaje"


def _asegurar_sala_general(user):
    """Garantiza que exista la única SalaChat GENERAL de la institución (o de cada institución activa para ADMIN_SISTEMA)."""
    if user.rol == Rol.ADMIN_SISTEMA:
        for inst in Institucion.objects.all():
            sala, _ = SalaChat._base_manager.get_or_create(
                institucion_id=inst.pk,
                tipo=SalaChat.Tipo.GENERAL,
                defaults={"nombre": f"Sala general · {inst.nombre}"[:100]},
            )
            SalaParticipante._base_manager.get_or_create(
                institucion_id=inst.pk,
                sala=sala,
                usuario_id=user.pk,
            )
    elif user.institucion_id:
        inst = Institucion.objects.filter(pk=user.institucion_id).first()
        nombre_default = f"Sala general · {inst.nombre}"[:100] if inst else "Sala general de la institución"
        sala, _ = SalaChat._base_manager.get_or_create(
            institucion_id=user.institucion_id,
            tipo=SalaChat.Tipo.GENERAL,
            defaults={"nombre": nombre_default},
        )
        SalaParticipante._base_manager.get_or_create(
            institucion_id=user.institucion_id,
            sala=sala,
            usuario_id=user.pk,
        )


def listar_salas_de(user):
    """Devuelve únicamente la(s) Sala(s) General(es) del alcance del usuario."""
    _asegurar_sala_general(user)
    if user.rol == Rol.ADMIN_SISTEMA:
        return list(
            SalaChat._base_manager.filter(tipo=SalaChat.Tipo.GENERAL)
            .order_by("institucion_id", "id")
        )
    if not user.institucion_id:
        return []
    return list(
        SalaChat._base_manager.filter(
            institucion_id=user.institucion_id,
            tipo=SalaChat.Tipo.GENERAL,
        ).order_by("id")
    )


def usuario_puede_acceder_sala(user, sala):
    if sala.tipo != SalaChat.Tipo.GENERAL:
        return False
    if user.rol == Rol.ADMIN_SISTEMA:
        return True
    return bool(user.institucion_id and sala.institucion_id == user.institucion_id)



def crear_o_obtener_sala_privada(user, destinatario_id, nombre=""):
    destinatario = Usuario._base_manager.filter(pk=destinatario_id).first()
    if not destinatario:
        raise LookupError("El destinatario no existe.")
    if destinatario.pk == user.pk:
        raise ValueError("No puedes iniciar una conversación privada contigo mismo.")

    if user.rol == Rol.ADMIN_SISTEMA:
        inst_id = destinatario.institucion_id or GLOBAL
    else:
        if destinatario.rol != Rol.ADMIN_SISTEMA and destinatario.institucion_id != user.institucion_id:
            raise PermissionError("Solo puedes conversar con miembros de tu misma institución.")
        inst_id = user.institucion_id

    mis_salas = set(
        SalaParticipante._base_manager.filter(usuario_id=user.pk).values_list("sala_id", flat=True)
    )
    sus_salas = set(
        SalaParticipante._base_manager.filter(usuario_id=destinatario.pk).values_list("sala_id", flat=True)
    )
    comunes = mis_salas & sus_salas
    existente = (
        SalaChat._base_manager.filter(
            pk__in=comunes,
            tipo=SalaChat.Tipo.PRIVADA,
            institucion_id=inst_id,
        )
        .first()
    )
    if existente:
        return existente

    etiqueta = (
        nombre.strip()
        or f"{user.nombres} {user.apellidos} · {destinatario.nombres} {destinatario.apellidos}"
    )[:100]
    with transaction.atomic():
        sala = SalaChat._base_manager.create(
            institucion_id=inst_id,
            tipo=SalaChat.Tipo.PRIVADA,
            nombre=etiqueta,
        )
        SalaParticipante._base_manager.create(
            institucion_id=inst_id,
            sala=sala,
            usuario_id=user.pk,
        )
        SalaParticipante._base_manager.create(
            institucion_id=inst_id,
            sala=sala,
            usuario_id=destinatario.pk,
        )
    return sala


def listar_contactos_chat(user):
    if user.rol == Rol.ADMIN_SISTEMA:
        qs = Usuario._base_manager.filter(
            rol__in=[Rol.ADMIN_ESCOLAR, Rol.ADMIN_SISTEMA],
            estado=Usuario.Estado.ACTIVA,
        ).exclude(pk=user.pk)
    elif user.rol == Rol.PADRE:
        qs = Usuario._base_manager.filter(
            institucion_id=user.institucion_id,
            rol=Rol.ADMIN_ESCOLAR,
            estado=Usuario.Estado.ACTIVA,
        )
    else:
        qs = Usuario._base_manager.filter(
            institucion_id=user.institucion_id,
            rol__in=[Rol.PADRE, Rol.GUARDIA, Rol.CUIDADOR_FIJO, Rol.ADMIN_ESCOLAR],
            estado=Usuario.Estado.ACTIVA,
        ).exclude(pk=user.pk)
    return list(
        qs.order_by("rol", "nombres", "apellidos").values(
            "id", "nombres", "apellidos", "correo", "rol", "institucion_id"
        )
    )


def listar_mensajes_sala(user, sala_id=None, limite=100):
    _asegurar_sala_general(user)
    if sala_id is not None:
        sala = SalaChat._base_manager.filter(pk=sala_id, tipo=SalaChat.Tipo.GENERAL).first()
    elif user.institucion_id:
        sala = SalaChat._base_manager.filter(
            institucion_id=user.institucion_id, tipo=SalaChat.Tipo.GENERAL
        ).first()
    else:
        sala = SalaChat._base_manager.filter(tipo=SalaChat.Tipo.GENERAL).order_by("institucion_id", "id").first()
    if not sala or not usuario_puede_acceder_sala(user, sala):
        raise LookupError("La sala general no existe o no tienes acceso.")
    return list(
        MensajeChat._base_manager.filter(sala_id=sala.pk)
        .order_by("enviado_en", "id")[:limite]
    )


def enviar_mensaje_sala(user, sala_id, contenido):
    _asegurar_sala_general(user)
    if sala_id:
        sala = SalaChat._base_manager.filter(pk=sala_id, tipo=SalaChat.Tipo.GENERAL).first()
    elif user.institucion_id:
        sala = SalaChat._base_manager.filter(
            institucion_id=user.institucion_id, tipo=SalaChat.Tipo.GENERAL
        ).first()
    else:
        sala = SalaChat._base_manager.filter(tipo=SalaChat.Tipo.GENERAL).order_by("institucion_id", "id").first()

    if not sala or not usuario_puede_acceder_sala(user, sala):
        raise LookupError("La sala general no existe o no tienes acceso.")
    texto = (contenido or "").strip()
    if not texto:
        raise ValueError("El mensaje no puede estar vacío.")

    with transaction.atomic():
        SalaParticipante._base_manager.get_or_create(
            institucion_id=sala.institucion_id,
            sala=sala,
            usuario_id=user.pk,
        )
        mensaje = MensajeChat._base_manager.create(
            institucion_id=sala.institucion_id,
            sala=sala,
            autor_id=user.pk,
            contenido=texto[:2000],
            enviado_en=timezone.now(),
        )
        destinatarios = list(
            Usuario._base_manager.filter(
                institucion_id=sala.institucion_id,
                estado=Usuario.Estado.ACTIVA,
            ).values_list("pk", flat=True)
        ) + list(
            Usuario._base_manager.filter(
                rol=Rol.ADMIN_SISTEMA,
                estado=Usuario.Estado.ACTIVA,
            ).values_list("pk", flat=True)
        )

        payload_msg = {
            "id": mensaje.pk,
            "sala": sala.pk,
            "institucion_id": sala.institucion_id,
            "autor_id": user.pk,
            "autor_nombre": f"{user.nombres} {user.apellidos}".strip() or user.correo,
            "autor_rol": user.rol,
            "contenido": mensaje.contenido,
            "enviado_en": mensaje.enviado_en.isoformat(),
        }
        destinos_ws = list(dict.fromkeys(destinatarios))
        transaction.on_commit(lambda: _emitir_mensaje_chat(destinos_ws, payload_msg))
    return mensaje


def _emitir_mensaje_chat(usuario_ids, payload_msg):
    try:
        capa = get_channel_layer()
        if capa is None:
            return
        for uid in usuario_ids:
            async_to_sync(capa.group_send)(
                grupo_usuario(uid),
                {
                    "type": "chat.mensaje",
                    "evento": EVENTO_CHAT_MENSAJE,
                    "mensaje": payload_msg,
                },
            )
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo emitir el mensaje de chat en tiempo real.")

