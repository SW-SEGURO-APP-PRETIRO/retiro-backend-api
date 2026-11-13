from django.db import models
from django.db.models import Q
from django.utils import timezone

from shared.tenancy.models import TenantModel


class SesionSalida(TenantModel):
    """Sesión de salida de 20 min: el QR dinámico se rota cada 30 s dentro de ella."""

    class Estado(models.TextChoices):
        VIGENTE = "VIGENTE", "Vigente"
        EXPIRADA = "EXPIRADA", "Expirada"
        ANULADA = "ANULADA", "Anulada"

    cuidador_id = models.PositiveBigIntegerField()  # cuidadores.Cuidador (por id)
    inicia_en = models.DateTimeField(default=timezone.now)
    expira_en = models.DateTimeField()
    rotacion_actual = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=8, choices=Estado.choices, default=Estado.VIGENTE)


class PaseQR(TenantModel):
    """Pase de retiro. En la BD solo vive el HASH del token; el token en claro viaja solo en el QR."""

    class Tipo(models.TextChoices):
        ESTATICO = "ESTATICO", "Estático (cuidador temporal)"
        DINAMICO = "DINAMICO", "Dinámico (sesión de salida)"

    class Estado(models.TextChoices):
        VIGENTE = "VIGENTE", "Vigente"
        USADO = "USADO", "Usado"
        EXPIRADO = "EXPIRADO", "Expirado"
        ANULADO = "ANULADO", "Anulado"

    cuidador_id = models.PositiveBigIntegerField()
    tipo = models.CharField(max_length=8, choices=Tipo.choices)
    sesion = models.ForeignKey(SesionSalida, null=True, blank=True, on_delete=models.PROTECT, related_name="pases")
    hash_token = models.CharField(max_length=64, unique=True)
    numero_rotacion = models.PositiveIntegerField(default=0)
    creado_en = models.DateTimeField(default=timezone.now)
    expira_en = models.DateTimeField()
    usado_en = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=8, choices=Estado.choices, default=Estado.VIGENTE)

    class Meta:
        constraints = [
            # Coherencia: un pase USADO tiene fecha de uso y los demás no
            models.CheckConstraint(
                condition=(Q(estado="USADO", usado_en__isnull=False) | (~Q(estado="USADO") & Q(usado_en__isnull=True))),
                name="ck_pase_usado_coherente",
            ),
        ]
        indexes = [models.Index(fields=["institucion_id", "estado", "expira_en"], name="ix_pase_inst_estado_expira")]


class PaseEstudiante(TenantModel):
    """Un pase puede cubrir varios estudiantes (hermanos)."""

    pase = models.ForeignKey(PaseQR, on_delete=models.PROTECT, related_name="estudiantes")
    estudiante_id = models.PositiveBigIntegerField()  # cuentas.Estudiante (por id)
    retirado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pase", "estudiante_id"], name="uq_pase_estudiante"),
        ]


class Retiro(TenantModel):
    """Registro histórico de una entrega. Un estudiante solo puede retirarse UNA vez por día."""

    pase = models.ForeignKey(PaseQR, on_delete=models.PROTECT, related_name="retiros")
    guardia_id = models.PositiveBigIntegerField()
    puerta_id = models.PositiveBigIntegerField()
    estudiante_id = models.PositiveBigIntegerField()
    foto_entrega_cifrada = models.BinaryField(null=True, blank=True, editable=False)
    fecha_hora = models.DateTimeField(default=timezone.now)
    fecha = models.DateField(editable=False)  # día local del retiro; sostiene la regla "una vez por día"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["estudiante_id", "fecha"], name="uq_retiro_estudiante_dia"),
        ]
        indexes = [models.Index(fields=["institucion_id", "fecha_hora"], name="ix_retiro_inst_fecha")]

    def save(self, *args, **kwargs):
        self.fecha = timezone.localtime(self.fecha_hora).date()
        super().save(*args, **kwargs)