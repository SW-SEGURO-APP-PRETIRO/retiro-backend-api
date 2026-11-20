import json

from rest_framework import serializers

from apps.cuentas.models import Usuario

from .models import EventoAuditoria


class EventoAuditoriaSerializer(serializers.ModelSerializer):
    """Solo lectura (FAU_STG.1): la bitácora no se modifica por la API."""

    detalle = serializers.SerializerMethodField()
    actor_nombre = serializers.SerializerMethodField()

    class Meta:
        model = EventoAuditoria
        fields = [
            "id",
            "institucion_id",
            "secuencia",
            "categoria",
            "tipo",
            "actor_id",
            "actor_nombre",
            "resultado",
            "detalle",
            "fecha",
            "hash_anterior",
            "hash_propio",
        ]
        read_only_fields = fields

    def get_detalle(self, obj) -> dict:
        try:
            return json.loads(obj.detalle)
        except (TypeError, ValueError):
            return {}

    def get_actor_nombre(self, obj) -> str:
        if not obj.actor_id:
            return "Sistema"
        actor = Usuario._base_manager.filter(pk=obj.actor_id).first()
        if not actor:
            return "Usuario eliminado"
        nombre = f"{actor.nombres} {actor.apellidos}".strip()
        return nombre or actor.correo


class FiltroAuditoriaSerializer(serializers.Serializer):
    """Parámetros de consulta: fechas inclusivas (AAAA-MM-DD), tipo exacto y usuario (actor)."""

    fecha_desde = serializers.DateField(required=False)
    fecha_hasta = serializers.DateField(required=False)
    tipo = serializers.CharField(required=False, max_length=60)
    usuario = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        desde, hasta = attrs.get("fecha_desde"), attrs.get("fecha_hasta")
        if desde and hasta and desde > hasta:
            raise serializers.ValidationError({"fecha_desde": "No puede ser posterior a fecha_hasta."})
        return attrs
