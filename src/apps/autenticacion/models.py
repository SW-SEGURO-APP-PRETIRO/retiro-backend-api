from django.db import models


class TokenRecuperacion(models.Model):
    """Token de un solo uso (30 min) para recuperar la clave. Solo se guarda el hash.

    No lleva institucion_id: pertenece a la cuenta (el Administrador del Sistema también recupera
    su clave y no tiene institución). `usuario_id` es referencia por id al módulo `cuentas`.
    """

    usuario_id = models.PositiveBigIntegerField(db_index=True)
    hash_token = models.CharField(max_length=64, unique=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    usado_en = models.DateTimeField(null=True, blank=True)