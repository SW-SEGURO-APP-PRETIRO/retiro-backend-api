from rest_framework import serializers

from .models import Notificacion


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ["id", "tipo", "titulo", "mensaje", "referencia", "leida", "creada_en", "leida_en"]
        read_only_fields = fields


class FiltroNotificacionesSerializer(serializers.Serializer):
    no_leidas = serializers.BooleanField(required=False, default=False)
