from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    CambioContrasenaSerializer,
    ConfirmacionRecuperacionSerializer,
    IngresoSerializer,
    RespuestaSerializer,
    SolicitudRecuperacionSerializer,
)
from .services import (
    autenticar,
    cambiar_contrasena,
    cerrar_sesion,
    confirmar_recuperacion,
    confirmar_recuperacion_por_hash,
    datos_usuario,
    solicitar_recuperacion,
    CLAVE_SESION_RECUPERACION,
)


def error(codigo, mensaje, detalles=None, http_status=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"error": {"codigo": codigo, "mensaje": mensaje, "detalles": detalles or {}}},
        status=http_status,
    )


class IngresoView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Autenticación"],
        request=IngresoSerializer,
        responses={200: RespuestaSerializer, 401: OpenApiResponse(description="Credenciales inválidas")},
    )
    def post(self, request):
        serializer = IngresoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, mensaje = autenticar(
            request, serializer.validated_data["correo"], serializer.validated_data["contrasena"]
        )
        if not user:
            return error("AUTENTICACION_FALLIDA", mensaje, http_status=status.HTTP_401_UNAUTHORIZED)
        return Response(
            {
                "datos": {
                    "usuario": datos_usuario(user),
                    "sesion": {
                        "autenticado": True,
                        "requiere_cambio_contrasena": user.contrasena_temporal,
                    },
                },
                "mensaje": "Inicio de sesión exitoso.",
            }
        )


class CerrarSesionView(APIView):
    @extend_schema(tags=["Autenticación"], request=None, responses=RespuestaSerializer)
    def post(self, request):
        cerrar_sesion(request)
        return Response({"datos": {}, "mensaje": "Sesión cerrada correctamente."})


class PerfilView(APIView):
    @extend_schema(tags=["Autenticación"], responses=RespuestaSerializer)
    def get(self, request):
        return Response(
            {
                "datos": {
                    "usuario": datos_usuario(request.user),
                    "requiere_cambio_contrasena": request.user.contrasena_temporal,
                },
                "mensaje": "Perfil obtenido correctamente.",
            }
        )


class CambioContrasenaTemporalView(APIView):
    @extend_schema(tags=["Autenticación"], request=CambioContrasenaSerializer, responses=RespuestaSerializer)
    def post(self, request):
        serializer = CambioContrasenaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cambiar_contrasena(
                request.user,
                serializer.validated_data["contrasena_actual"],
                serializer.validated_data["nueva_contrasena"],
            )
        except ValueError as exc:
            return error("CONTRASENA_ACTUAL_INVALIDA", str(exc))
        return Response({"datos": {}, "mensaje": "Contraseña actualizada correctamente."})


class SolicitarRecuperacionView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Autenticación"], request=SolicitudRecuperacionSerializer, responses=RespuestaSerializer)
    def post(self, request):
        serializer = SolicitudRecuperacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        solicitar_recuperacion(serializer.validated_data["correo"])
        datos = {}
        return Response(
            {
                "datos": datos,
                "mensaje": (
                    "Si el correo existe, recibirás un enlace para restablecerla. "
                    "Revisa también la carpeta de correo no deseado."
                ),
            }
        )


class ConfirmarRecuperacionView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["Autenticación"], request=ConfirmacionRecuperacionSerializer, responses=RespuestaSerializer)
    def post(self, request):
        serializer = ConfirmacionRecuperacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = serializer.validated_data.get("token")
            nueva_contrasena = serializer.validated_data["nueva_contrasena"]
            if token:
                confirmar_recuperacion(token, nueva_contrasena)
            else:
                confirmar_recuperacion_por_hash(
                    request.session.get(CLAVE_SESION_RECUPERACION),
                    nueva_contrasena,
                )
        except ValueError as exc:
            return error("TOKEN_INVALIDO", str(exc))
        request.session.pop(CLAVE_SESION_RECUPERACION, None)
        return Response({"datos": {}, "mensaje": "Contraseña restablecida correctamente."})
