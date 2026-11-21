from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.permissions import EsAdminEscolar, EsPadreOAdminEscolar

from . import services
from .serializers import (
    AutorizacionSerializer,
    CrearCuidadorSerializer,
    CuidadorSerializer,
    FiltroAutorizacionesSerializer,
    RechazarAutorizacionSerializer,
    SolicitarAutorizacionSerializer,
)

TAG = ["Cuidadores"]


def ok(datos, mensaje, http_status=status.HTTP_200_OK):
    return Response({"datos": datos, "mensaje": mensaje}, status=http_status)


def error(codigo, mensaje, detalles=None, http_status=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"error": {"codigo": codigo, "mensaje": mensaje, "detalles": detalles or {}}}, status=http_status
    )


def _traducir(exc):
    """Convierte las excepciones del servicio en la respuesta de error estándar."""
    if isinstance(exc, LookupError):
        return error("NO_ENCONTRADO", str(exc.args[0]), http_status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, PermissionError):
        return error("PERMISO_DENEGADO", str(exc), http_status=status.HTTP_403_FORBIDDEN)
    if isinstance(exc, services.ErrorEnvioCorreo):
        return error(
            "CORREO_NO_ENVIADO",
            "No se pudo enviar el correo con las credenciales; la aprobación no se aplicó. Intente de nuevo.",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return error("CONFLICTO", str(exc), http_status=status.HTTP_409_CONFLICT)


_ERRORES = (LookupError, PermissionError, ValueError, services.ErrorEnvioCorreo)


class CuidadorListCreateView(APIView):
    permission_classes = [EsPadreOAdminEscolar]
    serializer_class = CuidadorSerializer

    @extend_schema(
        tags=TAG,
        summary="Listar cuidadores de la institución",
        request=None,
        responses=CuidadorSerializer(many=True),
        operation_id="cuidadores_list",
    )
    def get(self, request):
        return ok(CuidadorSerializer(services.listar_cuidadores(request.user), many=True).data, "Cuidadores obtenidos.")

    @extend_schema(
        tags=TAG,
        summary="Registrar un cuidador",
        request=CrearCuidadorSerializer,
        responses={201: CuidadorSerializer},
        operation_id="cuidadores_create",
    )
    def post(self, request):
        serializer = CrearCuidadorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cuidador = services.crear_cuidador(request.user, serializer.validated_data)
        except _ERRORES as exc:
            return _traducir(exc)
        return ok(CuidadorSerializer(cuidador).data, "Cuidador registrado.", status.HTTP_201_CREATED)


class SolicitarAutorizacionView(APIView):
    permission_classes = [EsPadreOAdminEscolar]
    serializer_class = SolicitarAutorizacionSerializer

    @extend_schema(
        tags=TAG,
        summary="Solicitar la autorización de un cuidador para un estudiante",
        request=SolicitarAutorizacionSerializer,
        responses={201: AutorizacionSerializer},
        operation_id="cuidadores_solicitar_autorizacion",
    )
    def post(self, request, pk):
        serializer = SolicitarAutorizacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            autorizacion = services.solicitar_autorizacion(
                request.user, pk, serializer.validated_data["estudiante_id"]
            )
        except _ERRORES as exc:
            return _traducir(exc)
        return ok(AutorizacionSerializer(autorizacion).data, "Autorización solicitada.", status.HTTP_201_CREATED)


class AutorizacionListView(APIView):
    permission_classes = [EsPadreOAdminEscolar]
    serializer_class = AutorizacionSerializer

    @extend_schema(
        tags=TAG,
        summary="Listar solicitudes de autorización de la institución",
        parameters=[OpenApiParameter("estado", str, description="SOLICITADO, ACCESO_EMITIDO, ACTIVO, EXPIRADO, REVOCADO o RECHAZADO")],
        request=None,
        responses=AutorizacionSerializer(many=True),
        operation_id="cuidadores_autorizaciones_list",
    )
    def get(self, request):
        filtro = FiltroAutorizacionesSerializer(data=request.query_params)
        filtro.is_valid(raise_exception=True)
        autorizaciones = list(services.listar_autorizaciones(request.user, filtro.validated_data.get("estado")))
        contexto = {"estudiantes": services.nombres_de_estudiantes(request.user, autorizaciones)}
        return ok(AutorizacionSerializer(autorizaciones, many=True, context=contexto).data, "Autorizaciones obtenidas.")


class _ResolverAutorizacionView(APIView):
    permission_classes = [EsAdminEscolar]
    serializer_class = AutorizacionSerializer
    accion = None
    mensaje = ""

    def post(self, request, pk):
        try:
            autorizacion = self.accion(request.user, pk)
        except _ERRORES as exc:
            return _traducir(exc)
        return ok(AutorizacionSerializer(autorizacion).data, self.mensaje)


class AprobarAutorizacionView(_ResolverAutorizacionView):
    accion = staticmethod(services.aprobar_autorizacion)
    mensaje = "Autorización aprobada."

    @extend_schema(
        tags=TAG,
        summary="Aprobar una autorización (crea la cuenta del cuidador fijo y envía la clave por correo)",
        request=None,
        responses=AutorizacionSerializer,
        operation_id="cuidadores_autorizacion_aprobar",
    )
    def post(self, request, pk):
        return super().post(request, pk)


class RevocarAutorizacionView(_ResolverAutorizacionView):
    accion = staticmethod(services.revocar_autorizacion)
    mensaje = "Autorización revocada."

    @extend_schema(
        tags=TAG,
        summary="Revocar una autorización vigente",
        request=None,
        responses=AutorizacionSerializer,
        operation_id="cuidadores_autorizacion_revocar",
    )
    def post(self, request, pk):
        return super().post(request, pk)


class RechazarAutorizacionView(APIView):
    permission_classes = [EsAdminEscolar]
    serializer_class = RechazarAutorizacionSerializer

    @extend_schema(
        tags=TAG,
        summary="Rechazar una solicitud de cuidador pendiente",
        request=RechazarAutorizacionSerializer,
        responses={200: AutorizacionSerializer},
        operation_id="cuidadores_autorizacion_rechazar",
    )
    def post(self, request, pk):
        serializer = RechazarAutorizacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            autorizacion = services.rechazar_autorizacion(
                request.user,
                pk,
                serializer.validated_data["motivo"],
            )
        except _ERRORES as exc:
            return _traducir(exc)
        contexto = {
            "estudiantes": services.nombres_de_estudiantes(
                request.user,
                [autorizacion],
            )
        }
        return ok(
            AutorizacionSerializer(autorizacion, context=contexto).data,
            "Solicitud rechazada.",
        )
