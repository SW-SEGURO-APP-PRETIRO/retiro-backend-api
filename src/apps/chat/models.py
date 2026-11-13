from django.db import models
from django.db.models import Q

from shared.tenancy.models import TenantModel


class Notificacion(TenantModel):
    """Bandeja de notificaciones (con historial). El mensaje NUNCA lleva datos personales de menores."""

    emisor_id = models.PositiveBigIntegerField(null=True, blank=True)  # cuentas.Usuario; nulo = sistema
    destinatario_id = models.PositiveBigIntegerField()
    tipo = models.CharField(max_length=50)  # p. ej. RETIRO_REALIZADO, CUIDADOR_SOLICITADO, ACCESO_EMITIDO
    titulo = models.CharField(max_length=200)
    mensaje = models.CharField(max_length=500)
    referencia = models.CharField(max_length=100, blank=True)  # id del objeto relacionado
    leida = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)
    leida_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["destinatario_id", "leida", "creada_en"], name="ix_notif_dest_leida_fecha"),
        ]


class SalaChat(TenantModel):
    class Tipo(models.TextChoices):
        GENERAL = "GENERAL", "Sala general de la institución"
        PRIVADA = "PRIVADA", "Conversación privada"

    tipo = models.CharField(max_length=7, choices=Tipo.choices)
    nombre = models.CharField(max_length=100, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Una sola sala general por institución
            models.UniqueConstraint(
                fields=["institucion_id"], condition=Q(tipo="GENERAL"), name="uq_sala_general_por_inst"
            ),
        ]


class SalaParticipante(TenantModel):
    sala = models.ForeignKey(SalaChat, on_delete=models.CASCADE, related_name="participantes")
    usuario_id = models.PositiveBigIntegerField()  # cuentas.Usuario

    class Meta:
        constraints = [models.UniqueConstraint(fields=["sala", "usuario_id"], name="uq_sala_participante")]


class MensajeChat(TenantModel):
    """Retención de 90 días (una tarea programada borra los más antiguos)."""

    sala = models.ForeignKey(SalaChat, on_delete=models.CASCADE, related_name="mensajes")
    autor_id = models.PositiveBigIntegerField()
    contenido = models.CharField(max_length=2000)  # validado y sanitizado en services
    enviado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["sala", "enviado_en"], name="ix_mensaje_sala_fecha")]