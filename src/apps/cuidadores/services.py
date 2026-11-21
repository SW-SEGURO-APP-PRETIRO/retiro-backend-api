"""Lógica del Bloque C: cuidadores fijos y su flujo de autorización.

Convenciones de errores (las vistas los traducen a HTTP):
- LookupError      -> 404 (no existe, o pertenece a otra institución: no se distingue a propósito)
- PermissionError  -> 403
- ValueError       -> 409 (regla de negocio / conflicto)
- ErrorEnvioCorreo -> 503 (falla cerrado: si no se puede entregar la clave, no se aprueba)
"""
import logging

from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.autenticacion.services import _registrar_auditoria
from apps.chat.services import crear_y_emitir_notificacion, grupo_admin_escolar
from apps.cuentas import services as cuentas
from apps.cuentas.models import Rol

from .models import AutorizacionCuidador, Cuidador, PersonaBloqueada

logger = logging.getLogger(__name__)

OPERATIVA = EventoAuditoria.Categoria.OPERATIVA
VIVAS = (
    AutorizacionCuidador.Estado.SOLICITADO,
    AutorizacionCuidador.Estado.ACCESO_EMITIDO,
    AutorizacionCuidador.Estado.ACTIVO,
)


class ErrorEnvioCorreo(Exception):
    pass


# ------------------------------------------------------------------------------ Consultas
def listar_cuidadores(actor):
    qs = Cuidador._base_manager.filter(institucion_id=actor.institucion_id)
    if actor.rol == Rol.PADRE:
        hijos_ids = cuentas.RelacionPadreEstudiante._base_manager.filter(
            institucion_id=actor.institucion_id, padre_id=actor.pk, vigente=True
        ).values_list("estudiante_id", flat=True)
        cuidadores_ids = AutorizacionCuidador._base_manager.filter(
            institucion_id=actor.institucion_id,
            estudiante_id__in=hijos_ids,
        ).values_list("cuidador_id", flat=True)
        qs = qs.filter(pk__in=cuidadores_ids)
    elif actor.rol == Rol.CUIDADOR_FIJO:
        qs = qs.filter(usuario_id=actor.pk)
    return qs.order_by("id")


def listar_autorizaciones(actor, estado=None):
    qs = AutorizacionCuidador._base_manager.filter(institucion_id=actor.institucion_id).select_related("cuidador")
    if actor.rol == Rol.PADRE:
        hijos_ids = cuentas.RelacionPadreEstudiante._base_manager.filter(
            institucion_id=actor.institucion_id, padre_id=actor.pk, vigente=True
        ).values_list("estudiante_id", flat=True)
        qs = qs.filter(estudiante_id__in=hijos_ids)
    elif actor.rol == Rol.CUIDADOR_FIJO:
        qs = qs.filter(cuidador__usuario_id=actor.pk)
    if estado:
        qs = qs.filter(estado=estado)
    return qs.order_by("-id")


def nombres_de_estudiantes(actor, autorizaciones):
    ids = {a.estudiante_id for a in autorizaciones}
    return cuentas.nombres_estudiantes(actor.institucion_id, ids)


# ------------------------------------------------------------------------------ Registro
def crear_cuidador(actor, datos):
    if actor.rol not in (Rol.PADRE, Rol.ADMIN_ESCOLAR):
        raise PermissionError("Solo PADRE o ADMIN_ESCOLAR pueden registrar cuidadores.")
    inst = actor.institucion_id
    existente = Cuidador._base_manager.filter(institucion_id=inst, cedula=datos["cedula"]).first()
    if existente:
        raise ValueError(
            f"Ya existe un cuidador con esa cédula en la institución (id {existente.pk}). "
            "Use ese id para solicitar la autorización."
        )
    if datos["tipo"] == Cuidador.Tipo.FIJO and cuentas.correo_en_uso(datos["correo"]):
        raise ValueError("Ya existe una cuenta con ese correo.")
    try:
        with transaction.atomic():
            cuidador = Cuidador.objects.create(institucion_id=inst, **datos)
            _registrar_auditoria(
                actor, "CUIDADOR_CREADO", "EXITO",
                {"cuidador_id": cuidador.pk, "tipo": cuidador.tipo}, categoria=OPERATIVA,
            )
    except IntegrityError:
        raise ValueError("Ya existe un cuidador fijo con ese correo en la institución.")
    return cuidador


def solicitar_autorizacion(actor, cuidador_id, estudiante_id):
    if actor.rol not in (Rol.PADRE, Rol.ADMIN_ESCOLAR):
        raise PermissionError("Solo PADRE o ADMIN_ESCOLAR pueden solicitar autorizaciones.")
    inst = actor.institucion_id
    cuidador = Cuidador._base_manager.filter(pk=cuidador_id, institucion_id=inst).first()
    if cuidador is None:
        raise LookupError("El cuidador no existe.")
    estudiante = cuentas.obtener_estudiante(inst, estudiante_id)
    if estudiante is None:
        raise LookupError("El estudiante no existe.")
    # Un padre solo puede pedir autorizaciones para SUS hijos vigentes
    if actor.rol == Rol.PADRE and not cuentas.padre_representa_estudiante(actor.pk, estudiante.pk):
        raise PermissionError("El estudiante no está vinculado a su cuenta.")
    if PersonaBloqueada._base_manager.filter(
        institucion_id=inst, estudiante_id=estudiante.pk, cedula=cuidador.cedula
    ).exists():
        raise ValueError("Esta persona está en la lista de bloqueados del estudiante.")
    if AutorizacionCuidador._base_manager.filter(
        cuidador=cuidador, estudiante_id=estudiante.pk, estado__in=VIVAS
    ).exists():
        raise ValueError("Ya existe una autorización vigente para este cuidador y estudiante.")

    try:
        with transaction.atomic():
            autorizacion = AutorizacionCuidador.objects.create(
                institucion_id=inst,
                cuidador=cuidador,
                estudiante_id=estudiante.pk,
                solicitada_por_id=actor.pk,
            )
            _registrar_auditoria(
                actor, "AUTORIZACION_SOLICITADA", "EXITO",
                {"autorizacion_id": autorizacion.pk, "cuidador_id": cuidador.pk, "estudiante_id": estudiante.pk},
                categoria=OPERATIVA,
            )
            if cuidador.tipo == Cuidador.Tipo.FIJO:
                crear_y_emitir_notificacion(
                    destinatario_ids=cuentas.ids_usuarios_por_rol(Rol.ADMIN_ESCOLAR, inst),
                    grupo=grupo_admin_escolar(inst),
                    institucion_id=inst,
                    emisor_id=actor.pk,
                    tipo="CUIDADOR_SOLICITADO",
                    titulo="Nueva solicitud de cuidador fijo",
                    mensaje=f"Se solicitó autorizar a {cuidador.nombres} {cuidador.apellidos} como cuidador fijo.",
                    referencia=autorizacion.pk,
                    subevento="cuidador.solicitud",
                )
    except IntegrityError:
        raise ValueError("Ya existe una autorización vigente para este cuidador y estudiante.")
    return autorizacion


# ------------------------------------------------------------------- Aprobación / revocación
def _autorizacion_de_institucion(actor, autorizacion_id):
    if actor.rol != Rol.ADMIN_ESCOLAR:
        raise PermissionError("Solo ADMIN_ESCOLAR puede resolver autorizaciones.")
    autorizacion = (
        AutorizacionCuidador._base_manager.select_for_update()
        .filter(pk=autorizacion_id, institucion_id=actor.institucion_id)
        .first()
    )
    if autorizacion is None:
        raise LookupError("La autorización no existe.")
    # El estudiante debe seguir perteneciendo a la institución del administrador
    if cuentas.obtener_estudiante(actor.institucion_id, autorizacion.estudiante_id) is None:
        raise LookupError("La autorización no existe.")
    return autorizacion


def aprobar_autorizacion(actor, autorizacion_id):
    """SOLICITADO -> ACCESO_EMITIDO. Para un FIJO sin cuenta crea el usuario y envía la clave por correo."""
    with transaction.atomic():
        autorizacion = _autorizacion_de_institucion(actor, autorizacion_id)
        if autorizacion.estado != AutorizacionCuidador.Estado.SOLICITADO:
            raise ValueError("Solo se pueden aprobar autorizaciones en estado SOLICITADO.")
        cuidador = Cuidador._base_manager.get(pk=autorizacion.cuidador_id)

        cuenta_creada = False
        contrasena = None
        if cuidador.tipo == Cuidador.Tipo.FIJO and cuidador.usuario_id is None:
            if cuentas.correo_en_uso(cuidador.correo):
                raise ValueError("Ya existe una cuenta con el correo del cuidador.")
            try:
                usuario, contrasena = cuentas.crear_cuenta_cuidador_fijo(
                    actor,
                    correo=cuidador.correo,
                    cedula=cuidador.cedula,
                    nombres=cuidador.nombres,
                    apellidos=cuidador.apellidos,
                    telefono=cuidador.telefono,
                )
            except (ValidationError, IntegrityError) as exc:
                raise ValueError(f"No se pudo crear la cuenta del cuidador: {_mensaje(exc)}")
            cuidador.usuario_id = usuario.pk
            cuidador.save(update_fields=["usuario_id"])
            cuenta_creada = True

        autorizacion.estado = AutorizacionCuidador.Estado.ACCESO_EMITIDO
        autorizacion.acceso_emitido_por_id = actor.pk
        autorizacion.acceso_emitido_en = timezone.now()
        autorizacion.save(update_fields=["estado", "acceso_emitido_por_id", "acceso_emitido_en"])

        _registrar_auditoria(
            actor, "CUIDADOR_AUTORIZACION_APROBADA", "EXITO",
            {
                "autorizacion_id": autorizacion.pk,
                "cuidador_id": cuidador.pk,
                "estudiante_id": autorizacion.estudiante_id,
                "cuenta_creada": cuenta_creada,
            },
            categoria=OPERATIVA,
        )
        # Avisa a quien hizo la solicitud (sin credenciales ni datos del menor)
        nombre = f"{cuidador.nombres} {cuidador.apellidos}".strip()
        if cuenta_creada:
            aviso = f"Se crearon las credenciales de {nombre} y se enviaron al correo registrado."
        else:
            aviso = f"Se aprobó la autorización de {nombre}."
        crear_y_emitir_notificacion(
            destinatario_ids=autorizacion.solicitada_por_id,
            institucion_id=actor.institucion_id,
            emisor_id=actor.pk,
            tipo="ACCESO_EMITIDO",
            titulo="Autorización de cuidador aprobada",
            mensaje=aviso,
            referencia=autorizacion.pk,
            subevento="cuidador.aprobado",
        )
        # Último paso dentro de la transacción: si el correo falla, TODO se revierte (falla cerrado)
        if cuenta_creada:
            _enviar_credenciales(cuidador, contrasena)
    return autorizacion


def revocar_autorizacion(actor, autorizacion_id):
    with transaction.atomic():
        autorizacion = _autorizacion_de_institucion(actor, autorizacion_id)
        if autorizacion.estado not in VIVAS:
            raise ValueError("Solo se pueden revocar autorizaciones vigentes.")
        autorizacion.estado = AutorizacionCuidador.Estado.REVOCADO
        autorizacion.revocada_en = timezone.now()
        autorizacion.save(update_fields=["estado", "revocada_en"])
        _registrar_auditoria(
            actor, "CUIDADOR_AUTORIZACION_REVOCADA", "EXITO",
            {
                "autorizacion_id": autorizacion.pk,
                "cuidador_id": autorizacion.cuidador_id,
                "estudiante_id": autorizacion.estudiante_id,
            },
            categoria=OPERATIVA,
        )
    return autorizacion


def rechazar_autorizacion(actor, autorizacion_id, motivo=""):
    with transaction.atomic():
        autorizacion = _autorizacion_de_institucion(actor, autorizacion_id)
        if autorizacion.estado != AutorizacionCuidador.Estado.SOLICITADO:
            raise ValueError("Solo se pueden rechazar solicitudes pendientes.")
        autorizacion.estado = AutorizacionCuidador.Estado.RECHAZADO
        autorizacion.rechazada_por_id = actor.pk
        autorizacion.rechazada_en = timezone.now()
        autorizacion.motivo_rechazo = motivo.strip()
        autorizacion.save(
            update_fields=[
                "estado",
                "rechazada_por_id",
                "rechazada_en",
                "motivo_rechazo",
            ]
        )
        _registrar_auditoria(
            actor,
            "CUIDADOR_AUTORIZACION_RECHAZADA",
            "EXITO",
            {
                "autorizacion_id": autorizacion.pk,
                "cuidador_id": autorizacion.cuidador_id,
                "estudiante_id": autorizacion.estudiante_id,
                "motivo": autorizacion.motivo_rechazo,
            },
            categoria=OPERATIVA,
        )
        cuidador = Cuidador._base_manager.get(pk=autorizacion.cuidador_id)
        crear_y_emitir_notificacion(
            destinatario_ids=autorizacion.solicitada_por_id,
            institucion_id=actor.institucion_id,
            emisor_id=actor.pk,
            tipo="ACCESO_RECHAZADO",
            titulo="Solicitud de cuidador rechazada",
            mensaje=f"No se aprobó la solicitud para {cuidador.nombres} {cuidador.apellidos}.",
            referencia=autorizacion.pk,
            subevento="cuidador.rechazado",
        )
    return autorizacion


# --------------------------------------------------------------------------------- Auxiliares
def _mensaje(exc):
    if isinstance(exc, ValidationError):
        return "; ".join(exc.messages)
    return "dato duplicado"


def _enviar_credenciales(cuidador, contrasena):
    cuerpo = (
        f"Hola {cuidador.nombres},\n\n"
        "Se aprobó su acceso como cuidador fijo en Retiro Escolar Seguro.\n\n"
        f"Usuario: {cuidador.correo}\n"
        f"Contraseña temporal: {contrasena}\n\n"
        "La contraseña temporal vence en 48 horas y deberá cambiarla en su primer ingreso.\n"
        "Si no esperaba este mensaje, ignórelo y avise a la institución.\n"
    )
    try:
        send_mail(
            subject="Acceso a Retiro Escolar Seguro",
            message=cuerpo,
            from_email=None,  # usa DEFAULT_FROM_EMAIL
            recipient_list=[cuidador.correo],
            fail_silently=False,
        )
    except Exception as exc:  # noqa: BLE001 - cualquier fallo de transporte debe revertir la aprobación
        logger.error("No se pudo enviar el correo de credenciales (cuidador %s): %s", cuidador.pk, type(exc).__name__)
        raise ErrorEnvioCorreo("No se pudo enviar el correo con las credenciales.") from exc
