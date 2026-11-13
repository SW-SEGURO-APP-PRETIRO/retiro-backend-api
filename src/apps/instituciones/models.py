from django.db import models

from shared.tenancy.models import TenantModel
from shared.utils.validadores import validar_ruc_ec


class Institucion(models.Model):
    """El colegio cliente. Es la única tabla de negocio SIN institucion_id (ella es la institución)."""

    class Estado(models.TextChoices):
        PENDIENTE_VERIFICACION = "PENDIENTE_VERIFICACION", "Pendiente de verificación de correo"
        PENDIENTE_APROBACION = "PENDIENTE_APROBACION", "Pendiente de aprobación"
        ACTIVA = "ACTIVA", "Activa"
        SUSPENDIDA = "SUSPENDIDA", "Suspendida"
        RECHAZADA = "RECHAZADA", "Rechazada"

    nombre = models.CharField(max_length=200)
    ruc = models.CharField(max_length=13, unique=True, validators=[validar_ruc_ec])
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20)
    correo = models.EmailField(max_length=254, unique=True)
    responsable = models.CharField(max_length=150)
    estado = models.CharField(max_length=25, choices=Estado.choices, default=Estado.PENDIENTE_VERIFICACION)
    motivo_estado = models.CharField(max_length=255, blank=True)  # motivo de rechazo o suspensión
    creada_en = models.DateTimeField(auto_now_add=True)
    aprobada_en = models.DateTimeField(null=True, blank=True)
    aprobada_por_id = models.PositiveBigIntegerField(null=True, blank=True)  # Usuario (referencia por id)

    class Meta:
        verbose_name_plural = "instituciones"

    def __str__(self):
        return self.nombre


class Curso(TenantModel):
    nombre = models.CharField(max_length=80)
    hora_salida = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["institucion_id", "nombre"], name="uq_curso_inst_nombre"),
        ]

    def __str__(self):
        return self.nombre


class Puerta(TenantModel):
    nombre = models.CharField(max_length=80)
    activa = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["institucion_id", "nombre"], name="uq_puerta_inst_nombre"),
        ]

    def __str__(self):
        return self.nombre


class TokenVerificacion(TenantModel):
    """Enlace de verificación de correo (24 h). Solo se guarda el hash del token."""

    hash_token = models.CharField(max_length=64, unique=True)
    expira_en = models.DateTimeField()
    usado_en = models.DateTimeField(null=True, blank=True)