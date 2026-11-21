from rest_framework import serializers

from apps.cuentas.models import Usuario
from apps.instituciones.models import Institucion

from .models import MensajeChat, Notificacion, SalaChat


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ["id", "tipo", "titulo", "mensaje", "referencia", "leida", "creada_en", "leida_en"]
        read_only_fields = fields


class FiltroNotificacionesSerializer(serializers.Serializer):
    no_leidas = serializers.BooleanField(required=False, default=False)


class SalaChatSerializer(serializers.ModelSerializer):
    institucion_nombre = serializers.SerializerMethodField()
    ultimo_mensaje = serializers.SerializerMethodField()

    class Meta:
        model = SalaChat
        fields = ["id", "institucion_id", "institucion_nombre", "tipo", "nombre", "creada_en", "ultimo_mensaje"]
        read_only_fields = fields

    def get_institucion_nombre(self, obj) -> str:
        if not obj.institucion_id:
            return "Plataforma global"
        inst = Institucion.objects.filter(pk=obj.institucion_id).only("nombre").first()
        return inst.nombre if inst else f"Institución #{obj.institucion_id}"

    def get_ultimo_mensaje(self, obj):
        msg = MensajeChat._base_manager.filter(sala_id=obj.pk).order_by("-enviado_en", "-id").first()
        if not msg:
            return None
        return {
            "contenido": msg.contenido,
            "enviado_en": msg.enviado_en,
            "autor_id": msg.autor_id,
        }


class CrearSalaPrivadaSerializer(serializers.Serializer):
    destinatario_id = serializers.IntegerField(min_value=1)
    nombre = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")


class MensajeChatSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField()
    autor_rol = serializers.SerializerMethodField()

    class Meta:
        model = MensajeChat
        fields = ["id", "sala", "institucion_id", "autor_id", "autor_nombre", "autor_rol", "contenido", "enviado_en"]
        read_only_fields = fields

    def _get_autor(self, obj):
        cache = getattr(self, "_autores_cache", None)
        if cache is None:
            self._autores_cache = {}
            cache = self._autores_cache
        if obj.autor_id not in cache:
            cache[obj.autor_id] = Usuario._base_manager.filter(pk=obj.autor_id).first()
        return cache[obj.autor_id]

    def get_autor_nombre(self, obj) -> str:
        autor = self._get_autor(obj)
        if not autor:
            return f"Usuario #{obj.autor_id}"
        return f"{autor.nombres} {autor.apellidos}".strip() or autor.correo

    def get_autor_rol(self, obj) -> str:
        autor = self._get_autor(obj)
        return autor.rol if autor else ""


class EnviarMensajeChatSerializer(serializers.Serializer):
    contenido = serializers.CharField(max_length=2000, trim_whitespace=True)

