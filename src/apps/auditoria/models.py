"""Bitácora inmutable (FAU_STG.1): append-only y encadenada por hash.

Protección en TRES capas:
1. Python: save() de un registro existente, delete(), update() y delete() masivos lanzan error.
2. Base de datos: disparadores (migración 0002) rechazan UPDATE y DELETE.
3. Cadena de hashes: cada evento incluye el hash del anterior; alterar uno rompe la cadena.

`institucion_id = 0` significa evento global (del sistema, sin institución).
"""
from django.db import models
from django.utils import timezone

GLOBAL = 0
HASH_INICIAL = "0" * 64


class BitacoraInmutable(Exception):
    pass


class EventoQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise BitacoraInmutable("La bitácora es inmutable: no se permite update().")

    def delete(self):
        raise BitacoraInmutable("La bitácora es inmutable: no se permite delete().")

    def bulk_create(self, *args, **kwargs):
        raise BitacoraInmutable("Use el servicio de auditoría para respetar la cadena de hashes.")

    def bulk_update(self, *args, **kwargs):
        raise BitacoraInmutable("La bitácora es inmutable: no se permite bulk_update().")


class EventoAuditoria(models.Model):
    class Resultado(models.TextChoices):
        EXITO = "EXITO", "Éxito"
        FALLO = "FALLO", "Fallo"

    institucion_id = models.PositiveBigIntegerField(default=GLOBAL)
    secuencia = models.PositiveBigIntegerField()  # 1, 2, 3... dentro de cada institución
    tipo = models.CharField(max_length=60)
    actor_id = models.PositiveBigIntegerField(null=True, blank=True)
    resultado = models.CharField(max_length=5, choices=Resultado.choices)
    detalle = models.TextField(default="{}")  # JSON, sin secretos
    fecha = models.DateTimeField(default=timezone.now)
    hash_anterior = models.CharField(max_length=64)
    hash_propio = models.CharField(max_length=64, unique=True)

    objects = EventoQuerySet.as_manager()

    class Meta:
        constraints = [
            # Dos escritores simultáneos no pueden bifurcar la cadena: el segundo falla y reintenta
            models.UniqueConstraint(fields=["institucion_id", "secuencia"], name="uq_auditoria_inst_secuencia"),
        ]
        indexes = [
            models.Index(fields=["institucion_id", "fecha"], name="ix_auditoria_inst_fecha"),
            models.Index(fields=["actor_id", "fecha"], name="ix_auditoria_actor_fecha"),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise BitacoraInmutable("La bitácora es inmutable: un evento no se puede modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise BitacoraInmutable("La bitácora es inmutable: un evento no se puede borrar.")

    def __str__(self):
        return f"[{self.institucion_id}#{self.secuencia}] {self.tipo} {self.resultado}"