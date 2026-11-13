from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from shared.tenancy.models import TenantModel
from shared.utils.validadores import validar_cedula_ec


class Rol(models.TextChoices):
    """Cinco roles inmutables. El cuidador temporal NO es un rol (no tiene cuenta)."""

    ADMIN_SISTEMA = "ADMIN_SISTEMA", "Administrador del Sistema"
    ADMIN_ESCOLAR = "ADMIN_ESCOLAR", "Administrador Escolar"
    PADRE = "PADRE", "Padre / representante"
    GUARDIA = "GUARDIA", "Guardia"
    CUIDADOR_FIJO = "CUIDADOR_FIJO", "Cuidador fijo"


class UsuarioManager(BaseUserManager):
    """SIN filtro por institución: el inicio de sesión busca por correo ANTES de conocer la institución.
    Para listar usuarios de una institución use `de_institucion()`."""

    use_in_migrations = False

    def de_institucion(self, institucion_id: int):
        return self.get_queryset().filter(institucion_id=institucion_id)

    def crear_usuario(self, correo, password=None, **campos):
        if not correo:
            raise ValueError("El correo es obligatorio.")
        usuario = self.model(correo=self.normalize_email(correo), **campos)
        usuario.set_password(password)  # Argon2 (primer hasher de settings)
        usuario.full_clean(exclude=["password"])
        usuario.save()
        return usuario


class Usuario(AbstractBaseUser):
    institucion_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    correo = models.EmailField(max_length=254, unique=True)
    cedula = models.CharField(max_length=10, validators=[validar_cedula_ec])
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True)
    rol = models.CharField(max_length=15, choices=Rol.choices)

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ACTIVA = "ACTIVA", "Activa"
        BLOQUEADA = "BLOQUEADA", "Bloqueada"
        SUSPENDIDA = "SUSPENDIDA", "Suspendida"

    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    puerta_id = models.PositiveBigIntegerField(null=True, blank=True)  # Puerta asignada al guardia (por id)

    # Seguridad (FIA)
    totp_secreto_cifrado = models.TextField(blank=True)  # nunca en claro
    contrasena_temporal = models.BooleanField(default=False)
    expira_temporal = models.DateTimeField(null=True, blank=True)  # 48 h
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)  # 15 min tras 3 fallos

    creado_en = models.DateTimeField(auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "correo"
    REQUIRED_FIELDS = ["cedula", "nombres", "apellidos", "rol"]

    class Meta:
        constraints = [
            # Solo el Administrador del Sistema carece de institución; todos los demás la tienen
            models.CheckConstraint(
                condition=(
                    (Q(rol="ADMIN_SISTEMA") & Q(institucion_id__isnull=True))
                    | (~Q(rol="ADMIN_SISTEMA") & Q(institucion_id__isnull=False))
                ),
                name="ck_usuario_rol_institucion",
            ),
            # Una persona (cédula) = una cuenta por institución
            models.UniqueConstraint(
                fields=["institucion_id", "cedula"],
                condition=Q(institucion_id__isnull=False),
                name="uq_usuario_inst_cedula",
            ),
        ]
        indexes = [models.Index(fields=["cedula"], name="ix_usuario_cedula")]

    @property
    def is_active(self):
        # PENDIENTE puede iniciar sesión solo para cambiar la clave temporal; el flujo lo restringe
        return self.estado in (self.Estado.ACTIVA, self.Estado.PENDIENTE)

    def save(self, *args, **kwargs):
        # El rol es inmutable (FMT_MSA.1): no se puede cambiar después de crear la cuenta
        if self.pk:
            rol_guardado = (
                type(self)._base_manager.filter(pk=self.pk).values_list("rol", flat=True).first()
            )
            if rol_guardado is not None and rol_guardado != self.rol:
                raise ValidationError("El rol de una cuenta no se puede modificar.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.correo} ({self.rol})"


class Estudiante(TenantModel):
    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        INACTIVO = "INACTIVO", "Inactivo"

    cedula = models.CharField(max_length=10, validators=[validar_cedula_ec])
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    curso_id = models.PositiveBigIntegerField()  # instituciones.Curso (por id)
    hora_salida_especial = models.TimeField(null=True, blank=True)
    foto_cifrada = models.BinaryField(null=True, blank=True, editable=False)
    estado = models.CharField(max_length=8, choices=Estado.choices, default=Estado.ACTIVO)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["institucion_id", "cedula"], name="uq_estudiante_inst_cedula"),
        ]
        indexes = [models.Index(fields=["institucion_id", "apellidos"], name="ix_estudiante_inst_apellidos")]

    def __str__(self):
        return f"{self.apellidos} {self.nombres}"


class RelacionPadreEstudiante(TenantModel):
    """Vínculo oficial padre-hijo, creado solo por el Administrador Escolar (FMT_MSA.1)."""

    padre = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="hijos")
    estudiante = models.ForeignKey(Estudiante, on_delete=models.PROTECT, related_name="representantes")
    vigente = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["padre", "estudiante"], name="uq_relacion_padre_estudiante"),
        ]