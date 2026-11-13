"""Base abstracta para todas las tablas que pertenecen a una institución."""
from django.core.exceptions import PermissionDenied
from django.db import models

from .context import SIN_FILTRO, institucion_actual


class TenantQuerySet(models.QuerySet):
    pass


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    """Filtra por la institución actual. Falla cerrado: sin institución => ningún registro."""

    def get_queryset(self):
        qs = super().get_queryset()
        actual = institucion_actual()
        if actual is SIN_FILTRO:
            return qs
        if actual is None:
            return qs.none()
        return qs.filter(institucion_id=actual)


class TenantModel(models.Model):
    institucion_id = models.PositiveBigIntegerField(db_index=True)

    objects = TenantManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        actual = institucion_actual()
        if actual is not SIN_FILTRO and actual is not None:
            if self.institucion_id is None:
                self.institucion_id = actual
            elif self.institucion_id != actual:
                # Evita escribir datos de otra institución aunque la vista se equivoque
                raise PermissionDenied("No se puede escribir en otra institución.")
        super().save(*args, **kwargs)