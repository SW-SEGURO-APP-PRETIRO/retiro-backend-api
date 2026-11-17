from rest_framework import serializers

from apps.cuentas.models import Rol

from .models import Curso, Institucion, Puerta


class AdminEscolarInicialSerializer(serializers.Serializer):
    correo = serializers.EmailField()
    cedula = serializers.CharField(max_length=10)
    nombres = serializers.CharField(max_length=100)
    apellidos = serializers.CharField(max_length=100)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)


class RegistroInstitucionSerializer(serializers.ModelSerializer):
    admin_escolar = AdminEscolarInicialSerializer(write_only=True)

    class Meta:
        model = Institucion
        fields = [
            "nombre",
            "ruc",
            "direccion",
            "telefono",
            "correo",
            "responsable",
            "admin_escolar",
        ]


class InstitucionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institucion
        fields = [
            "id",
            "nombre",
            "ruc",
            "direccion",
            "telefono",
            "correo",
            "responsable",
            "estado",
            "motivo_estado",
            "creada_en",
            "creada_por_id",
            "aprobada_en",
            "aprobada_por_id",
        ]
        read_only_fields = [
            "id",
            "estado",
            "motivo_estado",
            "creada_en",
            "creada_por_id",
            "aprobada_en",
            "aprobada_por_id",
        ]


class DecisionInstitucionSerializer(serializers.Serializer):
    aprobada = serializers.BooleanField()
    motivo = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs["aprobada"] and not attrs.get("motivo"):
            raise serializers.ValidationError({"motivo": "El motivo es obligatorio al rechazar."})
        return attrs


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = ["id", "institucion_id", "nombre", "hora_salida", "activo"]
        read_only_fields = ["id", "institucion_id"]


class PuertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Puerta
        fields = ["id", "institucion_id", "nombre", "activa"]
        read_only_fields = ["id", "institucion_id"]
