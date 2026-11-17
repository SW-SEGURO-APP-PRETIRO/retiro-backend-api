from rest_framework import serializers

from shared.utils.validadores import validar_cedula_ec

from .models import AutorizacionCuidador, Cuidador


class CuidadorSerializer(serializers.ModelSerializer):
    """Solo lectura. No expone la foto cifrada ni la firma."""

    class Meta:
        model = Cuidador
        fields = [
            "id",
            "institucion_id",
            "tipo",
            "usuario_id",
            "cedula",
            "nombres",
            "apellidos",
            "telefono",
            "correo",
            "creado_en",
        ]
        read_only_fields = fields


class CrearCuidadorSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=Cuidador.Tipo.choices)
    cedula = serializers.CharField(max_length=10, validators=[validar_cedula_ec])
    nombres = serializers.CharField(max_length=100)
    apellidos = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    correo = serializers.EmailField(max_length=254, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["tipo"] == Cuidador.Tipo.FIJO and not attrs.get("correo"):
            raise serializers.ValidationError({"correo": "El cuidador fijo requiere un correo."})
        if attrs["tipo"] == Cuidador.Tipo.FIJO and not attrs.get("apellidos"):
            raise serializers.ValidationError({"apellidos": "El cuidador fijo requiere apellidos."})
        return attrs


class SolicitarAutorizacionSerializer(serializers.Serializer):
    estudiante_id = serializers.IntegerField(min_value=1)


class AutorizacionSerializer(serializers.ModelSerializer):
    cuidador = CuidadorSerializer(read_only=True)
    estudiante_nombre = serializers.SerializerMethodField()

    class Meta:
        model = AutorizacionCuidador
        fields = [
            "id",
            "institucion_id",
            "cuidador",
            "estudiante_id",
            "estudiante_nombre",
            "solicitada_por_id",
            "estado",
            "solicitada_en",
            "acceso_emitido_por_id",
            "acceso_emitido_en",
            "revocada_en",
        ]
        read_only_fields = fields

    def get_estudiante_nombre(self, obj) -> str:
        return self.context.get("estudiantes", {}).get(obj.estudiante_id, "")


class FiltroAutorizacionesSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=AutorizacionCuidador.Estado.choices, required=False)
