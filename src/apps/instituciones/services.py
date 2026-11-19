import secrets
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.cuentas.models import Rol, Usuario

from .models import Curso, Institucion, Puerta


def _notificar_institucion_pendiente(institucion):
    """Avisa a los ADMIN_SISTEMA que hay una institución esperando aprobación."""
    # Importes locales: evitan ciclos entre módulos al cargar
    from apps.chat.services import GRUPO_ADMIN_SISTEMA, crear_y_emitir_notificacion
    from apps.cuentas.services import ids_usuarios_por_rol

    crear_y_emitir_notificacion(
        destinatario_ids=ids_usuarios_por_rol(Rol.ADMIN_SISTEMA),
        grupo=GRUPO_ADMIN_SISTEMA,
        institucion_id=None,
        tipo="INSTITUCION_PENDIENTE",
        titulo="Institución pendiente de aprobación",
        mensaje=f"{institucion.nombre} solicitó registrarse y espera su aprobación.",
        referencia=institucion.pk,
        subevento="seguridad.anomalia",
    )


def registrar_institucion(datos, actor=None):
    from apps.autenticacion.services import _registrar_auditoria

    admin = datos["admin_escolar"]
    contrasena_temporal = secrets.token_urlsafe(12)
    with transaction.atomic():
        institucion = Institucion.objects.create(
            nombre=datos["nombre"],
            ruc=datos["ruc"],
            direccion=datos["direccion"],
            telefono=datos["telefono"],
            correo=datos["correo"],
            responsable=datos["responsable"],
            estado=Institucion.Estado.PENDIENTE_APROBACION,
            creada_por_id=actor.pk if actor else None,
        )
        usuario = Usuario.objects.crear_usuario(
            correo=admin["correo"],
            password=contrasena_temporal,
            cedula=admin["cedula"],
            nombres=admin["nombres"],
            apellidos=admin["apellidos"],
            telefono=admin.get("telefono", ""),
            rol=Rol.ADMIN_ESCOLAR,
            institucion_id=institucion.pk,
            estado=Usuario.Estado.PENDIENTE,
        )
        usuario.contrasena_temporal = True
        usuario.expira_temporal = timezone.now() + timedelta(hours=48)
        usuario.save(update_fields=["contrasena_temporal", "expira_temporal"])
        _registrar_auditoria(
            actor,
            "INSTITUCION_REGISTRADA",
            "EXITO",
            {"institucion_id": institucion.pk, "admin_escolar_id": usuario.pk},
            categoria=EventoAuditoria.Categoria.OPERATIVA,
        )
        _notificar_institucion_pendiente(institucion)
    return institucion, usuario, contrasena_temporal


def decidir_institucion(institucion, admin_sistema, aprobada, motivo):
    from apps.autenticacion.services import _registrar_auditoria

    if institucion.estado != Institucion.Estado.PENDIENTE_APROBACION:
        raise ValueError("La institución no está pendiente de aprobación.")
    institucion.estado = Institucion.Estado.ACTIVA if aprobada else Institucion.Estado.RECHAZADA
    institucion.motivo_estado = "" if aprobada else motivo
    institucion.aprobada_por_id = admin_sistema.pk
    institucion.aprobada_en = timezone.now()
    institucion.save(
        update_fields=["estado", "motivo_estado", "aprobada_por_id", "aprobada_en"]
    )
    if aprobada:
        Usuario.objects.filter(
            institucion_id=institucion.pk, rol=Rol.ADMIN_ESCOLAR
        ).update(estado=Usuario.Estado.ACTIVA)
    _registrar_auditoria(
        admin_sistema,
        "INSTITUCION_APROBADA" if aprobada else "INSTITUCION_RECHAZADA",
        "EXITO",
        {"institucion_id": institucion.pk, "motivo": motivo},
    )
    return institucion


def guardar_curso(usuario, datos, curso=None):
    nombre = datos.get("nombre", curso.nombre if curso else None)
    qs = Curso._base_manager.filter(institucion_id=usuario.institucion_id, nombre=nombre)
    if curso:
        qs = qs.exclude(pk=curso.pk)
    if qs.exists():
        raise IntegrityError("Ya existe un curso con ese nombre.")
    if curso:
        for campo, valor in datos.items():
            setattr(curso, campo, valor)
        curso.save()
        return curso
    return Curso.objects.create(institucion_id=usuario.institucion_id, **datos)


def guardar_puerta(usuario, datos, puerta=None):
    nombre = datos.get("nombre", puerta.nombre if puerta else None)
    qs = Puerta._base_manager.filter(institucion_id=usuario.institucion_id, nombre=nombre)
    if puerta:
        qs = qs.exclude(pk=puerta.pk)
    if qs.exists():
        raise IntegrityError("Ya existe una puerta con ese nombre.")
    if puerta:
        for campo, valor in datos.items():
            setattr(puerta, campo, valor)
        puerta.save()
        return puerta
    return Puerta.objects.create(institucion_id=usuario.institucion_id, **datos)


# ---------------------------------------------------------------------------------------------
# Consultas para otros módulos y para las pantallas web (solo lectura, filtradas por institución).
# ---------------------------------------------------------------------------------------------
def institucion_activa(institucion_id):
    return Institucion.objects.filter(pk=institucion_id, estado=Institucion.Estado.ACTIVA).exists()


def nombre_institucion(institucion_id):
    return Institucion.objects.filter(pk=institucion_id).values_list("nombre", flat=True).first() or ""


def ruc_en_uso(ruc):
    return Institucion.objects.filter(ruc=ruc).exists()


def correo_institucion_en_uso(correo):
    return Institucion.objects.filter(correo__iexact=correo).exists()


def cursos_activos(institucion_id, incluir_id=None):
    """[(id, nombre)] de los cursos activos de la institución (más `incluir_id`, aunque esté inactivo)."""
    qs = Curso._base_manager.filter(institucion_id=institucion_id)
    if incluir_id:
        qs = qs.filter(models_q_activo_o_id(incluir_id))
    else:
        qs = qs.filter(activo=True)
    return list(qs.order_by("nombre").values_list("pk", "nombre"))


def models_q_activo_o_id(curso_id):
    from django.db.models import Q

    return Q(activo=True) | Q(pk=curso_id)


def nombres_cursos(institucion_id):
    """{id: nombre} de todos los cursos de la institución."""
    return dict(Curso._base_manager.filter(institucion_id=institucion_id).values_list("pk", "nombre"))


def contar_cursos(institucion_id):
    return Curso._base_manager.filter(institucion_id=institucion_id, activo=True).count()


def nombre_puerta(institucion_id, puerta_id):
    if not puerta_id:
        return ""
    return (
        Puerta._base_manager.filter(institucion_id=institucion_id, pk=puerta_id)
        .values_list("nombre", flat=True)
        .first()
        or ""
    )


def listar_pendientes():
    return Institucion.objects.filter(estado=Institucion.Estado.PENDIENTE_APROBACION).order_by("creada_en")


def obtener_institucion(pk):
    return Institucion.objects.filter(pk=pk).first()


def resumen_instituciones():
    """{estado: cantidad} de todas las instituciones (para el Administrador del Sistema)."""
    from django.db.models import Count

    filas = Institucion.objects.values("estado").annotate(total=Count("id"))
    return {fila["estado"]: fila["total"] for fila in filas}
