import secrets
import string
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.autenticacion.services import _registrar_auditoria
from apps.instituciones.models import Curso

from .models import Estudiante, RelacionPadreEstudiante, Rol, Usuario


def generar_contrasena_temporal():
    caracteres = string.ascii_letters + string.digits + "!@#$%^&*"
    base = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    return "".join(base + [secrets.choice(caracteres) for _ in range(12)])


def crear_usuario_institucional(actor, datos):
    if datos["rol"] not in (Rol.PADRE, Rol.GUARDIA):
        raise ValueError("Solo se pueden crear cuentas PADRE o GUARDIA.")
    contrasena = generar_contrasena_temporal()
    usuario = Usuario.objects.crear_usuario(
        correo=datos["correo"],
        password=contrasena,
        cedula=datos["cedula"],
        nombres=datos["nombres"],
        apellidos=datos["apellidos"],
        telefono=datos.get("telefono", ""),
        rol=datos["rol"],
        institucion_id=actor.institucion_id,
        estado=Usuario.Estado.PENDIENTE,
        puerta_id=datos.get("puerta_id"),
    )
    usuario.contrasena_temporal = True
    usuario.expira_temporal = timezone.now() + timedelta(hours=48)
    usuario.save(update_fields=["contrasena_temporal", "expira_temporal"])
    _registrar_auditoria(
        actor,
        "USUARIO_CREADO",
        "EXITO",
        {"usuario_id": usuario.pk, "rol": usuario.rol},
        categoria=EventoAuditoria.Categoria.OPERATIVA,
    )
    return usuario, contrasena


def editar_usuario(actor, usuario, datos):
    if usuario.institucion_id != actor.institucion_id:
        raise PermissionError("El usuario no pertenece a su institución.")
    for campo, valor in datos.items():
        setattr(usuario, campo, valor)
    usuario.save()
    _registrar_auditoria(
        actor,
        "USUARIO_ACTUALIZADO",
        "EXITO",
        {"usuario_id": usuario.pk},
        categoria=EventoAuditoria.Categoria.OPERATIVA,
    )
    return usuario


def crear_estudiante(actor, datos):
    curso_id = datos["curso_id"]
    if not Curso._base_manager.filter(pk=curso_id, institucion_id=actor.institucion_id).exists():
        raise ValueError("El curso no pertenece a la institución del usuario.")
    estudiante = Estudiante.objects.create(institucion_id=actor.institucion_id, **datos)
    _registrar_auditoria(
        actor,
        "ESTUDIANTE_CREADO",
        "EXITO",
        {"estudiante_id": estudiante.pk},
        categoria=EventoAuditoria.Categoria.OPERATIVA,
    )
    return estudiante


def editar_estudiante(actor, estudiante, datos):
    if "curso_id" in datos and not Curso._base_manager.filter(
        pk=datos["curso_id"], institucion_id=actor.institucion_id
    ).exists():
        raise ValueError("El curso no pertenece a la institución del usuario.")
    for campo, valor in datos.items():
        setattr(estudiante, campo, valor)
    estudiante.save()
    _registrar_auditoria(
        actor,
        "ESTUDIANTE_ACTUALIZADO",
        "EXITO",
        {"estudiante_id": estudiante.pk},
        categoria=EventoAuditoria.Categoria.OPERATIVA,
    )
    return estudiante


def crear_relacion(actor, datos):
    padre = datos["padre"]
    estudiante = datos["estudiante"]
    if padre.institucion_id != actor.institucion_id or estudiante.institucion_id != actor.institucion_id:
        raise ValueError("Padre y estudiante deben pertenecer a la misma institución.")
    relacion = RelacionPadreEstudiante.objects.create(
        institucion_id=actor.institucion_id,
        padre=padre,
        estudiante=estudiante,
        vigente=datos.get("vigente", True),
    )
    _registrar_auditoria(
        actor,
        "RELACION_PADRE_ESTUDIANTE_CREADA",
        "EXITO",
        {"relacion_id": relacion.pk},
        categoria=EventoAuditoria.Categoria.OPERATIVA,
    )
    return relacion


def cambiar_estado_usuario(actor, usuario, estado):
    usuario.estado = estado
    if estado == Usuario.Estado.ACTIVA:
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.save(update_fields=["estado", "intentos_fallidos", "bloqueado_hasta"])
    else:
        usuario.save(update_fields=["estado"])
    _registrar_auditoria(
        actor,
        "USUARIO_BLOQUEADO" if estado == Usuario.Estado.BLOQUEADA else "USUARIO_DESBLOQUEADO",
        "EXITO",
        {"usuario_id": usuario.pk},
        categoria=EventoAuditoria.Categoria.OPERATIVA,
    )
    return usuario


# ---------------------------------------------------------------------------------------------
# Consultas y operaciones que otros módulos (cuidadores, chat) necesitan de `cuentas`.
# Así no importan sus modelos directamente (regla del monolito modular).
# ---------------------------------------------------------------------------------------------
def obtener_estudiante(institucion_id, estudiante_id):
    """Estudiante de ESA institución o None. Nunca devuelve uno de otra institución."""
    return Estudiante._base_manager.filter(pk=estudiante_id, institucion_id=institucion_id).first()


def nombres_estudiantes(institucion_id, ids):
    """{id: "Apellidos Nombres"} de los estudiantes de la institución indicada."""
    filas = Estudiante._base_manager.filter(institucion_id=institucion_id, pk__in=list(ids)).values_list(
        "pk", "apellidos", "nombres"
    )
    return {pk: f"{apellidos} {nombres}" for pk, apellidos, nombres in filas}


def padre_representa_estudiante(padre_id, estudiante_id):
    return RelacionPadreEstudiante._base_manager.filter(
        padre_id=padre_id, estudiante_id=estudiante_id, vigente=True
    ).exists()


def correo_en_uso(correo):
    return Usuario._base_manager.filter(correo__iexact=correo).exists()


def ids_usuarios_por_rol(rol, institucion_id=None):
    """Ids de las cuentas ACTIVAS de un rol (y de una institución, si se indica)."""
    qs = Usuario._base_manager.filter(rol=rol, estado=Usuario.Estado.ACTIVA)
    if institucion_id is not None:
        qs = qs.filter(institucion_id=institucion_id)
    return list(qs.values_list("pk", flat=True))


def crear_cuenta_cuidador_fijo(actor, *, correo, cedula, nombres, apellidos, telefono=""):
    """Crea la cuenta CUIDADOR_FIJO con contraseña temporal (secrets, 48 h, cambio obligatorio).

    Devuelve (usuario, contrasena_temporal). La contraseña solo se entrega por correo: nunca se
    registra en bitácora, notificaciones ni respuestas de la API.
    """
    contrasena = generar_contrasena_temporal()
    usuario = Usuario.objects.crear_usuario(
        correo=correo,
        password=contrasena,
        cedula=cedula,
        nombres=nombres,
        apellidos=apellidos,
        telefono=telefono,
        rol=Rol.CUIDADOR_FIJO,
        institucion_id=actor.institucion_id,
        estado=Usuario.Estado.PENDIENTE,
    )
    usuario.contrasena_temporal = True
    usuario.expira_temporal = timezone.now() + timedelta(hours=48)
    usuario.save(update_fields=["contrasena_temporal", "expira_temporal"])
    return usuario, contrasena
