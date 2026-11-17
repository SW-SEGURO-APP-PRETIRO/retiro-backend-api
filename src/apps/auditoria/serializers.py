import json

from rest_framework import serializers

from .models import EventoAuditoria


class EventoAuditoriaSerializer(serializers.ModelSerializer):
    """Solo lectura (FAU_STG.1): la bitácora no se modifica por la API."""

    detalle = serializers.SerializerMethodField()

    class Meta:
        model = EventoAuditoria
        fields = [
            "id",
            "institucion_id",
            "secuencia",
            "categoria",
            "tipo",
            "actor_id",
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
