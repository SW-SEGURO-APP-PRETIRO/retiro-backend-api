from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from shared.api import PaginacionEnvuelta

from . import services
from .serializers import (
    CrearSalaPrivadaSerializer,
    EnviarMensajeChatSerializer,
    FiltroNotificacionesSerializer,
    MensajeChatSerializer,
    NotificacionSerializer,
    SalaChatSerializer,
)

TAG = ["Notificaciones"]
TAG_CHAT = ["Chat"]


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


class SalaChatListCreateView(APIView):
    serializer_class = SalaChatSerializer

    @extend_schema(tags=TAG_CHAT, summary="Listar mis salas de chat", responses=SalaChatSerializer(many=True))
    def get(self, request):
        salas = services.listar_salas_de(request.user)
        return Response({"datos": SalaChatSerializer(salas, many=True).data, "mensaje": "Salas de chat obtenidas."})

    @extend_schema(
        tags=TAG_CHAT,
        summary="Iniciar o recuperar una conversación privada",
        request=CrearSalaPrivadaSerializer,
        responses={201: SalaChatSerializer},
    )
    def post(self, request):
        serializer = CrearSalaPrivadaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            sala = services.crear_o_obtener_sala_privada(
                request.user,
                serializer.validated_data["destinatario_id"],
                serializer.validated_data.get("nombre", ""),
            )
        except LookupError as exc:
            return Response(
                {"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(exc), "detalles": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionError as exc:
            return Response(
                {"error": {"codigo": "PERMISO_DENEGADO", "mensaje": str(exc), "detalles": {}}},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ValueError as exc:
            return Response(
                {"error": {"codigo": "CONFLICTO", "mensaje": str(exc), "detalles": {}}},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {"datos": SalaChatSerializer(sala).data, "mensaje": "Conversación lista."},
            status=status.HTTP_201_CREATED,
        )


class SalaGeneralMensajesView(APIView):
    """Atajo directo a la Sala General de la institución actual."""

    serializer_class = MensajeChatSerializer

    @extend_schema(tags=TAG_CHAT, summary="Listar mensajes de la sala general", responses=MensajeChatSerializer(many=True))
    def get(self, request):
        inst_id = request.query_params.get("institucion_id")
        salas = services.listar_salas_de(request.user)
        if inst_id and request.user.rol == "ADMIN_SISTEMA":
            salas = [s for s in salas if str(s.institucion_id) == str(inst_id)]
        if not salas:
            return Response({"datos": [], "mensaje": "Sin sala general disponible."})
        mensajes = services.listar_mensajes_sala(request.user, salas[0].pk)
        return Response(
            {
                "datos": {
                    "sala": SalaChatSerializer(salas[0]).data,
                    "mensajes": MensajeChatSerializer(mensajes, many=True).data,
                },
                "mensaje": "Mensajes de la sala general obtenidos.",
            }
        )

    @extend_schema(
        tags=TAG_CHAT,
        summary="Enviar mensaje a la sala general",
        request=EnviarMensajeChatSerializer,
        responses={201: MensajeChatSerializer},
    )
    def post(self, request):
        serializer = EnviarMensajeChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sala_id = request.data.get("sala_id")
        try:
            mensaje = services.enviar_mensaje_sala(
                request.user, sala_id, serializer.validated_data["contenido"]
            )
        except LookupError as exc:
            return Response(
                {"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(exc), "detalles": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response(
                {"error": {"codigo": "MENSAJE_INVALIDO", "mensaje": str(exc), "detalles": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"datos": MensajeChatSerializer(mensaje).data, "mensaje": "Mensaje enviado a la sala general."},
            status=status.HTTP_201_CREATED,
        )



class MensajeChatListCreateView(APIView):
    serializer_class = MensajeChatSerializer

    @extend_schema(tags=TAG_CHAT, summary="Listar mensajes de una sala", responses=MensajeChatSerializer(many=True))
    def get(self, request, pk):
        try:
            mensajes = services.listar_mensajes_sala(request.user, pk)
        except LookupError as exc:
            return Response(
                {"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(exc), "detalles": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"datos": MensajeChatSerializer(mensajes, many=True).data, "mensaje": "Mensajes obtenidos."})

    @extend_schema(
        tags=TAG_CHAT,
        summary="Enviar un mensaje a una sala de chat",
        request=EnviarMensajeChatSerializer,
        responses={201: MensajeChatSerializer},
    )
    def post(self, request, pk):
        serializer = EnviarMensajeChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            mensaje = services.enviar_mensaje_sala(
                request.user, pk, serializer.validated_data["contenido"]
            )
        except LookupError as exc:
            return Response(
                {"error": {"codigo": "NO_ENCONTRADO", "mensaje": str(exc), "detalles": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response(
                {"error": {"codigo": "MENSAJE_INVALIDO", "mensaje": str(exc), "detalles": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"datos": MensajeChatSerializer(mensaje).data, "mensaje": "Mensaje enviado."},
            status=status.HTTP_201_CREATED,
        )

