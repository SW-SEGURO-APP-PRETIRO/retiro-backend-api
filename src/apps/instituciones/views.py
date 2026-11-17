from django.db import IntegrityError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cuentas.models import Rol
from shared.permissions import EsAdminEscolar, EsAdminSistema

from .models import Curso, Institucion, Puerta
from .serializers import (
    CursoSerializer,
    DecisionInstitucionSerializer,
    InstitucionSerializer,
    PuertaSerializer,
    RegistroInstitucionSerializer,
)
from .services import decidir_institucion, guardar_curso, guardar_puerta, registrar_institucion


def ok(datos, mensaje, http_status=status.HTTP_200_OK):
    return Response({"datos": datos, "mensaje": mensaje}, status=http_status)


def error(codigo, mensaje, detalles=None, http_status=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"error": {"codigo": codigo, "mensaje": mensaje, "detalles": detalles or {}}},
        status=http_status,
    )


class RegistroInstitucionView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegistroInstitucionSerializer

    @extend_schema(tags=["Instituciones"], request=RegistroInstitucionSerializer)
    def post(self, request):
        serializer = RegistroInstitucionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            institucion, usuario, contrasena = registrar_institucion(serializer.validated_data)
        except IntegrityError as exc:
            return error("CONFLICTO", str(exc), http_status=status.HTTP_409_CONFLICT)
        return ok(
            {
                "institucion": InstitucionSerializer(institucion).data,
                "admin_escolar": {
                    "id": usuario.pk,
                    "correo": usuario.correo,
                    "contrasena_temporal": contrasena,
                },
            },
            "Institución registrada y pendiente de aprobación.",
            status.HTTP_201_CREATED,
        )


class InstitucionesPendientesView(APIView):
    permission_classes = [EsAdminSistema]
    serializer_class = InstitucionSerializer

    @extend_schema(tags=["Instituciones"], request=None, responses=InstitucionSerializer(many=True))
    def get(self, request):
        data = InstitucionSerializer(
            Institucion.objects.filter(
                estado=Institucion.Estado.PENDIENTE_APROBACION
            ).order_by("id"),
            many=True,
        ).data
        return ok(data, "Instituciones pendientes obtenidas.")


class AprobarInstitucionView(APIView):
    permission_classes = [EsAdminSistema]
    serializer_class = DecisionInstitucionSerializer

    @extend_schema(tags=["Instituciones"], request=DecisionInstitucionSerializer)
    def post(self, request, pk):
        serializer = DecisionInstitucionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            institucion = Institucion.objects.get(pk=pk)
            institucion = decidir_institucion(
                institucion,
                request.user,
                serializer.validated_data["aprobada"],
                serializer.validated_data.get("motivo", ""),
            )
        except Institucion.DoesNotExist:
            return error("NO_ENCONTRADO", "La institución no existe.", http_status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return error("ESTADO_INVALIDO", str(exc), http_status=status.HTTP_409_CONFLICT)
        return ok(InstitucionSerializer(institucion).data, "Decisión de institución registrada.")


class MiInstitucionView(APIView):
    permission_classes = [EsAdminEscolar]
    serializer_class = InstitucionSerializer

    @extend_schema(tags=["Instituciones"], request=None, responses=InstitucionSerializer)
    def get(self, request):
        return ok(
            InstitucionSerializer(Institucion.objects.get(pk=request.user.institucion_id)).data,
            "Institución obtenida.",
        )

    @extend_schema(tags=["Instituciones"], request=InstitucionSerializer)
    def patch(self, request):
        institucion = Institucion.objects.get(pk=request.user.institucion_id)
        serializer = InstitucionSerializer(institucion, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        institucion = serializer.save()
        return ok(InstitucionSerializer(institucion).data, "Institución actualizada.")


class CursoListCreateView(APIView):
    permission_classes = [EsAdminEscolar]
    serializer_class = CursoSerializer

    @extend_schema(tags=["Instituciones"], request=None, responses=CursoSerializer(many=True))
    def get(self, request):
        return ok(CursoSerializer(Curso.objects.all().order_by("id"), many=True).data, "Cursos obtenidos.")

    @extend_schema(tags=["Instituciones"], request=CursoSerializer)
    def post(self, request):
        serializer = CursoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            curso = guardar_curso(request.user, serializer.validated_data)
        except IntegrityError as exc:
            return error("CONFLICTO", str(exc), http_status=status.HTTP_409_CONFLICT)
        return ok(CursoSerializer(curso).data, "Curso creado.", status.HTTP_201_CREATED)


class CursoDetailView(APIView):
    permission_classes = [EsAdminEscolar]
    serializer_class = CursoSerializer

    def get_object(self, request, pk):
        return Curso.objects.get(pk=pk)

    @extend_schema(tags=["Instituciones"], request=None, responses=CursoSerializer)
    def get(self, request, pk):
        try:
            curso = self.get_object(request, pk)
        except Curso.DoesNotExist:
            return error("NO_ENCONTRADO", "El curso no existe.", http_status=status.HTTP_404_NOT_FOUND)
        return ok(CursoSerializer(curso).data, "Curso obtenido.")

    @extend_schema(tags=["Instituciones"], request=CursoSerializer)
    def patch(self, request, pk):
        try:
            curso = self.get_object(request, pk)
        except Curso.DoesNotExist:
            return error("NO_ENCONTRADO", "El curso no existe.", http_status=status.HTTP_404_NOT_FOUND)
        serializer = CursoSerializer(curso, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            curso = guardar_curso(request.user, serializer.validated_data, curso)
        except IntegrityError as exc:
            return error("CONFLICTO", str(exc), http_status=status.HTTP_409_CONFLICT)
        return ok(CursoSerializer(curso).data, "Curso actualizado.")

    @extend_schema(tags=["Instituciones"], request=None)
    def delete(self, request, pk):
        try:
            curso = self.get_object(request, pk)
        except Curso.DoesNotExist:
            return error("NO_ENCONTRADO", "El curso no existe.", http_status=status.HTTP_404_NOT_FOUND)
        curso.delete()
        return ok({}, "Curso eliminado.")


class PuertaListCreateView(APIView):
    permission_classes = [EsAdminEscolar]
    serializer_class = PuertaSerializer

    @extend_schema(tags=["Instituciones"], request=None, responses=PuertaSerializer(many=True))
    def get(self, request):
        return ok(PuertaSerializer(Puerta.objects.all().order_by("id"), many=True).data, "Puertas obtenidas.")

    @extend_schema(tags=["Instituciones"], request=PuertaSerializer)
    def post(self, request):
        serializer = PuertaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            puerta = guardar_puerta(request.user, serializer.validated_data)
        except IntegrityError as exc:
            return error("CONFLICTO", str(exc), http_status=status.HTTP_409_CONFLICT)
        return ok(PuertaSerializer(puerta).data, "Puerta creada.", status.HTTP_201_CREATED)


class PuertaDetailView(APIView):
    permission_classes = [EsAdminEscolar]
    serializer_class = PuertaSerializer

    def get_object(self, request, pk):
        return Puerta.objects.get(pk=pk)

    @extend_schema(tags=["Instituciones"], request=None, responses=PuertaSerializer)
    def get(self, request, pk):
        try:
            puerta = self.get_object(request, pk)
        except Puerta.DoesNotExist:
            return error("NO_ENCONTRADO", "La puerta no existe.", http_status=status.HTTP_404_NOT_FOUND)
        return ok(PuertaSerializer(puerta).data, "Puerta obtenida.")

    @extend_schema(tags=["Instituciones"], request=PuertaSerializer)
    def patch(self, request, pk):
        try:
            puerta = self.get_object(request, pk)
        except Puerta.DoesNotExist:
            return error("NO_ENCONTRADO", "La puerta no existe.", http_status=status.HTTP_404_NOT_FOUND)
        serializer = PuertaSerializer(puerta, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            puerta = guardar_puerta(request.user, serializer.validated_data, puerta)
        except IntegrityError as exc:
            return error("CONFLICTO", str(exc), http_status=status.HTTP_409_CONFLICT)
        return ok(PuertaSerializer(puerta).data, "Puerta actualizada.")

    @extend_schema(tags=["Instituciones"], request=None)
    def delete(self, request, pk):
        try:
            puerta = self.get_object(request, pk)
        except Puerta.DoesNotExist:
            return error("NO_ENCONTRADO", "La puerta no existe.", http_status=status.HTTP_404_NOT_FOUND)
        puerta.delete()
        return ok({}, "Puerta eliminada.")
