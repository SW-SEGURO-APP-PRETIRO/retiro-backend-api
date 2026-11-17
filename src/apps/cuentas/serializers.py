from rest_framework import serializers

from .models import Estudiante, RelacionPadreEstudiante, Rol, Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            "id",
            "correo",
            "cedula",
            "nombres",
            "apellidos",
            "telefono",
            "rol",
            "estado",
            "institucion_id",
            "puerta_id",
            "contrasena_temporal",
            "expira_temporal",
            "intentos_fallidos",
            "bloqueado_hasta",
            "creado_en",
        ]
        read_only_fields = [
            "id",
            "institucion_id",
            "estado",
            "contrasena_temporal",
            "expira_temporal",
            "intentos_fallidos",
            "bloqueado_hasta",
            "creado_en",
        ]


class CrearUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["correo", "cedula", "nombres", "apellidos", "telefono", "rol", "puerta_id"]

    def validate_rol(self, value):
        if value not in (Rol.PADRE, Rol.GUARDIA):
            raise serializers.ValidationError("Solo se pueden crear cuentas PADRE o GUARDIA.")
        return value


class EditarUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["correo", "cedula", "nombres", "apellidos", "telefono", "puerta_id"]


class EstudianteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estudiante
        fields = [
            "id",
            "institucion_id",
            "cedula",
            "nombres",
            "apellidos",
            "fecha_nacimiento",
            "curso_id",
            "hora_salida_especial",
            "estado",
        ]
        read_only_fields = ["id", "institucion_id"]


class RelacionPadreEstudianteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelacionPadreEstudiante
        fields = ["id", "institucion_id", "padre", "estudiante", "vigente"]
        read_only_fields = ["id", "institucion_id"]

    def validate_padre(self, value):
        if value.rol != Rol.PADRE:
            raise serializers.ValidationError("La cuenta debe tener rol PADRE.")
        return value
