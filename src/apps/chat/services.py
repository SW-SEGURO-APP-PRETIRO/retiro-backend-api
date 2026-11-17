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
