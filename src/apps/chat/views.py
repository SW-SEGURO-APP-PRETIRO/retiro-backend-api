from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api import PaginacionEnvuelta

from . import services
from .serializers import FiltroNotificacionesSerializer, NotificacionSerializer

TAG = ["Notificaciones"]


class PaginacionNotificaciones(PaginacionEnvuelta):
    mensaje = "Notificaciones obtenidas."

    def get_paginated_response_schema(self, schema):
        esquema = super().get_paginated_response_schema(schema)
        esquema["properties"]["datos"]["properties"]["no_leidas"] = {"type": "integer"}
        return esquema


class NotificacionListView(ListAPIView):
    """Solo las notificaciones del usuario autenticado."""

    serializer_class = NotificacionSerializer
    pagination_class = PaginacionNotificaciones

    @extend_schema(
        tags=TAG,
        summary="Listar mis notificaciones (con contador de no leídas)",
        parameters=[OpenApiParameter("no_leidas", bool, description="true: solo las no leídas")],
        operation_id="notificaciones_list",
    )
    def get(self, request, *args, **kwargs):
        filtro = FiltroNotificacionesSerializer(data=request.query_params)
        filtro.is_valid(raise_exception=True)
        queryset = services.notificaciones_de(request.user.pk)
        if filtro.validated_data["no_leidas"]:
            queryset = queryset.filter(leida=False)
        pagina = self.paginate_queryset(queryset.order_by("-creada_en", "-id"))
        respuesta = self.get_paginated_response(self.get_serializer(pagina, many=True).data)
        respuesta.data["datos"]["no_leidas"] = services.contar_no_leidas(request.user.pk)
        return respuesta


class NotificacionLeidaView(APIView):
    serializer_class = NotificacionSerializer

    @extend_schema(
        tags=TAG,
        summary="Marcar una notificación como leída",
        request=None,
        responses=NotificacionSerializer,
        operation_id="notificaciones_leida",
    )
    def patch(self, request, pk):
        notificacion = services.marcar_leida(request.user.pk, pk)
        if notificacion is None:
            return Response(
                {"error": {"codigo": "NO_ENCONTRADO", "mensaje": "La notificación no existe.", "detalles": {}}},
                status=404,
            )
        return Response({"datos": NotificacionSerializer(notificacion).data, "mensaje": "Notificación marcada como leída."})


class MarcarTodasLeidasView(APIView):
    serializer_class = NotificacionSerializer

    @extend_schema(
        tags=TAG,
        summary="Marcar todas mis notificaciones como leídas",
        request=None,
        operation_id="notificaciones_marcar_todas_leidas",
    )
    def post(self, request):
        marcadas = services.marcar_todas_leidas(request.user.pk)
        return Response(
            {"datos": {"marcadas": marcadas, "no_leidas": 0}, "mensaje": "Notificaciones marcadas como leídas."}
        )
