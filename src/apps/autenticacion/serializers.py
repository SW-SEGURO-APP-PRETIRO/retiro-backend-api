from rest_framework import serializers


class IngresoSerializer(serializers.Serializer):
    correo = serializers.EmailField()
    contrasena = serializers.CharField(write_only=True, trim_whitespace=False)
    # TOTP reservado para el 2.º bimestre; no forma parte del login del alcance actual.
    codigo_totp = serializers.CharField(required=False, allow_blank=True, write_only=True)


class CambioContrasenaSerializer(serializers.Serializer):
    contrasena_actual = serializers.CharField(write_only=True, trim_whitespace=False)
    nueva_contrasena = serializers.CharField(write_only=True, trim_whitespace=False, min_length=8)

    def validate_nueva_contrasena(self, value):
        if (
            not any(c.isupper() for c in value)
            or not any(c.islower() for c in value)
            or not any(c.isdigit() for c in value)
            or not any(not c.isalnum() for c in value)
        ):
            raise serializers.ValidationError(
                "La contraseña debe incluir mayúscula, minúscula, número y símbolo."
            )
        return value


class SolicitudRecuperacionSerializer(serializers.Serializer):
    correo = serializers.EmailField()


class ConfirmacionRecuperacionSerializer(serializers.Serializer):
    token = serializers.CharField(required=False, write_only=True)
    nueva_contrasena = serializers.CharField(write_only=True, min_length=8)

    def validate_nueva_contrasena(self, value):
        if (
            not any(c.isupper() for c in value)
            or not any(c.islower() for c in value)
            or not any(c.isdigit() for c in value)
            or not any(not c.isalnum() for c in value)
        ):
            raise serializers.ValidationError(
                "La contraseña debe incluir mayúscula, minúscula, número y símbolo."
            )
        return value


class RespuestaSerializer(serializers.Serializer):
    datos = serializers.DictField()
    mensaje = serializers.CharField()
