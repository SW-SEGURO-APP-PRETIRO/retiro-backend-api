from django.db import models
from django.db.models import Q

from shared.tenancy.models import TenantModel
from shared.utils.validadores import validar_cedula_ec


class Cuidador(TenantModel):
    class Tipo(models.TextChoices):
        TEMPORAL = "TEMPORAL", "Temporal (solo QR, sin cuenta)"
        FIJO = "FIJO", "Fijo (con cuenta)"

    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    usuario_id = models.PositiveBigIntegerField(null=True, blank=True)  # cuentas.Usuario, solo si es FIJO
    cedula = models.CharField(max_length=10, validators=[validar_cedula_ec])
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.EmailField(max_length=254, blank=True)  # correo personal del cuidador fijo
    foto_cifrada = models.BinaryField(null=True, blank=True, editable=False)
    firma_hmac = models.CharField(max_length=64, blank=True)  # integridad del registro
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # El correo de un cuidador fijo es único dentro de la institución
            models.UniqueConstraint(
                fields=["institucion_id", "correo"],
                condition=Q(tipo="FIJO", correo__gt=""),
                name="uq_cuidador_fijo_inst_correo",
            ),
            # Un cuidador temporal no tiene cuenta de usuario
            models.CheckConstraint(
                condition=Q(tipo="FIJO") | Q(usuario_id__isnull=True),
                name="ck_cuidador_temporal_sin_usuario",
            ),
        ]
        indexes = [models.Index(fields=["institucion_id", "cedula"], name="ix_cuidador_inst_cedula")]

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.tipo})"


class AutorizacionCuidador(TenantModel):
    """Qué cuidador puede retirar a qué estudiante, y en qué estado está esa autorización."""

    class Estado(models.TextChoices):
        SOLICITADO = "SOLICITADO", "Solicitado por el padre"
        ACCESO_EMITIDO = "ACCESO_EMITIDO", "Acceso emitido por el Admin Escolar"
        ACTIVO = "ACTIVO", "Activo (primer ingreso hecho)"
        EXPIRADO = "EXPIRADO", "Expirado"
        REVOCADO = "REVOCADO", "Revocado"

    cuidador = models.ForeignKey(Cuidador, on_delete=models.PROTECT, related_name="autorizaciones")
    estudiante_id = models.PositiveBigIntegerField()  # cuentas.Estudiante (por id)
    solicitada_por_id = models.PositiveBigIntegerField()  # cuentas.Usuario (padre)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.SOLICITADO)
    solicitada_en = models.DateTimeField(auto_now_add=True)
    acceso_emitido_por_id = models.PositiveBigIntegerField(null=True, blank=True)
    acceso_emitido_en = models.DateTimeField(null=True, blank=True)
    revocada_en = models.DateTimeField(null=True, blank=True)
    firma_hmac = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            # Un cuidador no puede tener dos autorizaciones vivas para el mismo estudiante
            models.UniqueConstraint(
                fields=["cuidador", "estudiante_id"],
                condition=Q(estado__in=["SOLICITADO", "ACCESO_EMITIDO", "ACTIVO"]),
                name="uq_autorizacion_viva",
            ),
        ]
        indexes = [
            models.Index(fields=["institucion_id", "estudiante_id", "estado"], name="ix_autoriz_inst_est_estado"),
        ]


class PersonaBloqueada(TenantModel):
    """Personas que un padre no quiere como cuidadores de un estudiante (lista de bloqueados)."""

    estudiante_id = models.PositiveBigIntegerField()
    cedula = models.CharField(max_length=10, validators=[validar_cedula_ec])
    registrada_por_id = models.PositiveBigIntegerField()
    registrada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["institucion_id", "estudiante_id", "cedula"], name="uq_bloqueada_inst_est_cedula"
            ),
        ]