"""Consulta de la bitácora (solo lectura).

Todas las vistas son `ListAPIView`/`RetrieveAPIView`: DRF responde 405 a POST, PUT, PATCH y DELETE,
y el modelo además rechaza cualquier modificación (FAU_STG.1).
"""
from datetime import datetime, time, timedelta

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from shared.api import PaginacionEnvuelta
from shared.permissions import EsAdminEscolar, EsAdminSistema, EsAdminSistemaOEscolar

from .models import EventoAuditoria
from .serializers import EventoAuditoriaSerializer, FiltroAuditoriaSerializer

TAG = ["Auditoría"]
Categoria = EventoAuditoria.Categoria

PARAMETROS = [
    OpenApiParameter("fecha_desde", str, description="AAAA-MM-DD (inclusive)"),
    OpenApiParameter("fecha_hasta", str, description="AAAA-MM-DD (inclusive)"),
    OpenApiParameter("tipo", str, description="Tipo de evento exacto, p. ej. INTENTO_INGRESO_FALLIDO"),
    OpenApiParameter("usuario", int, description="Id del usuario que realizó la acción"),
]


class PaginacionAuditoria(PaginacionEnvuelta):
    mensaje = "Eventos de auditoría obtenidos."


def _inicio_del_dia(dia):
    return timezone.make_aware(datetime.combine(dia, time.min))


def _filtrar(queryset, params):
    filtro = FiltroAuditoriaSerializer(data=params)
    filtro.is_valid(raise_exception=True)
    datos = filtro.validated_data
    if "fecha_desde" in datos:
        queryset = queryset.filter(fecha__gte=_inicio_del_dia(datos["fecha_desde"]))
    if "fecha_hasta" in datos:
        queryset = queryset.filter(fecha__lt=_inicio_del_dia(datos["fecha_hasta"] + timedelta(days=1)))
    if "tipo" in datos:
        queryset = queryset.filter(tipo=datos["tipo"])
    if "usuario" in datos:
        queryset = queryset.filter(actor_id=datos["usuario"])
    return queryset.order_by("-id")


class _ListaAuditoria(ListAPIView):
    serializer_class = EventoAuditoriaSerializer
    pagination_class = PaginacionAuditoria

    def base_queryset(self):
        raise NotImplementedError

    def get_queryset(self):
        return _filtrar(self.base_queryset(), self.request.query_params)


class AuditoriaTecnicaView(_ListaAuditoria):
    permission_classes = [EsAdminSistema]

    def base_queryset(self):
        return EventoAuditoria.objects.filter(categoria=Categoria.TECNICA)

    @extend_schema(
        tags=TAG,
        summary="Bitácora técnica (ADMIN_SISTEMA)",
        parameters=PARAMETROS,
        operation_id="auditoria_tecnica_list",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AuditoriaOperativaView(_ListaAuditoria):
    permission_classes = [EsAdminEscolar]

    def base_queryset(self):
        # Solo los eventos de la institución del administrador autenticado
        return EventoAuditoria.objects.filter(
            categoria=Categoria.OPERATIVA, institucion_id=self.request.user.institucion_id
        )

    @extend_schema(
        tags=TAG,
        summary="Bitácora operativa de la institución (ADMIN_ESCOLAR)",
        parameters=PARAMETROS,
        operation_id="auditoria_operativa_list",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AuditoriaDetalleView(RetrieveAPIView):
    permission_classes = [EsAdminSistemaOEscolar]
    serializer_class = EventoAuditoriaSerializer

    def get_queryset(self):
        user = self.request.user
        if user.rol == "ADMIN_SISTEMA":
            return EventoAuditoria.objects.filter(categoria=Categoria.TECNICA)
        return EventoAuditoria.objects.filter(
            categoria=Categoria.OPERATIVA, institucion_id=user.institucion_id
        )

    @extend_schema(tags=TAG, summary="Detalle de un evento de auditoría", operation_id="auditoria_detail")
    def get(self, request, *args, **kwargs):
        # Un evento fuera del alcance del rol/institución responde 404 (no revela que existe)
        instancia = self.get_object()
        return Response({"datos": self.get_serializer(instancia).data, "mensaje": "Evento obtenido."})
