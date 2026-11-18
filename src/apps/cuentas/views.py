from django.db import IntegrityError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.instituciones.models import Institucion
from shared.permissions import EsAdminEscolar, EsAdminSistema, EsAdminSistemaOEscolar

from .models import Estudiante, RelacionPadreEstudiante, Rol, Usuario
from .serializers import (
    CrearUsuarioSerializer,
    EditarUsuarioSerializer,
    EstudianteSerializer,
    RelacionPadreEstudianteSerializer,
    UsuarioSerializer,
)
from .services import (
    cambiar_estado_usuario,
    crear_estudiante,
    crear_relacion,
    crear_usuario_institucional,
    editar_estudiante,
    editar_usuario,
)


def ok(datos, mensaje, http_status=status.HTTP_200_OK):
    return Response({"datos": datos, "mensaje": mensaje}, status=http_status)


def error(codigo, mensaje, detalles=None, http_status=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"error": {"codigo": codigo, "mensaje": mensaje, "detalles": detalles or {}}},
        status=http_status,
    )


class UsuarioListCreateView(APIView):
    permission_classes = [EsAdminSistemaOEscolar]
    serializer_class = UsuarioSerializer

    @extend_schema(tags=["Cuentas"], request=None, responses=UsuarioSerializer(many=True), operation_id="cuentas_usuarios_list")
    def get(self, request):
        if request.user.rol == Rol.ADMIN_SISTEMA:
            queryset = Usuario._base_manager.all()
        else:
            queryset = Usuario.objects.de_institucion(request.user.institucion_id).filter(
                rol__in=[Rol.PADRE, Rol.GUARDIA, Rol.CUIDADOR_FIJO]
            )
        rol = request.query_params.get("rol")
        if rol:
            queryset = queryset.filter(rol=rol)
        return ok(UsuarioSerializer(queryset.order_by("id"), many=True).data, "Usuarios obtenidos.")

    @extend_schema(tags=["Cuentas"], request=CrearUsuarioSerializer)
    def post(self, request):
        if request.user.rol != Rol.ADMIN_ESCOLAR:
            return error("PERMISO_DENEGADO", "Solo ADMIN_ESCOLAR puede crear cuentas.", http_status=403)
        serializer = CrearUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            usuario, contrasena = crear_usuario_institucional(request.user, serializer.validated_data)
        except (IntegrityError, ValueError) as exc:
            return error("CONFLICTO", str(exc), http_status=status.HTTP_409_CONFLICT)
        return ok(
            {
                "usuario": UsuarioSerializer(usuario).data,
                "contrasena_temporal": contrasena,
            },
            "Cuenta creada con contraseña temporal.",
            status.HTTP_201_CREATED,
        )


class UsuarioDetailView(APIView):
    permission_classes = [EsAdminSistemaOEscolar]
    serializer_class = UsuarioSerializer

    def get_object(self, request, pk):
        if request.user.rol == Rol.ADMIN_SISTEMA:
            return Usuario._base_manager.get(pk=pk)
        return Usuario.objects.de_institucion(request.user.institucion_id).get(pk=pk)

    @extend_schema(tags=["Cuentas"], request=None, responses=UsuarioSerializer, operation_id="cuentas_usuario_detail")
    def get(self, request, pk):
        try:
            usuario = self.get_object(request, pk)
        except Usuario.DoesNotExist:
            return error("NO_ENCONTRADO", "El usuario no existe.", http_status=404)
        return ok(UsuarioSerializer(usuario).data, "Usuario obtenido.")

    @extend_schema(tags=["Cuentas"], request=EditarUsuarioSerializer)
    def patch(self, request, pk):
        if request.user.rol != Rol.ADMIN_ESCOLAR:
            return error("PERMISO_DENEGADO", "Solo ADMIN_ESCOLAR puede editar cuentas.", http_status=403)
        try:
            usuario = self.get_object(request, pk)
        except Usuario.DoesNotExist:
            return error("NO_ENCONTRADO", "El usuario no existe.", http_status=404)
        if usuario.rol not in (Rol.PADRE, Rol.GUARDIA):
            return error("PERMISO_DENEGADO", "Esta cuenta no puede editarse desde este endpoint.", http_status=403)
        serializer = EditarUsuarioSerializer(usuario, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            usuario = editar_usuario(request.user, usuario, serializer.validated_data)
        except IntegrityError as exc:
            return error("CONFLICTO", str(exc), http_status=409)
        return ok(UsuarioSerializer(usuario).data, "Usuario actualizado.")


class CambiarEstadoUsuarioView(APIView):
    permission_classes = [EsAdminSistema]
    serializer_class = UsuarioSerializer

    @extend_schema(tags=["Cuentas"], request=None, operation_id="cuentas_usuario_estado")
    def post(self, request, pk, estado):
        try:
            usuario = Usuario._base_manager.get(pk=pk)
        except Usuario.DoesNotExist:
            return error("NO_ENCONTRADO", "El usuario no existe.", http_status=404)
        if estado == "bloquear":
            nuevo_estado = Usuario.Estado.BLOQUEADA
        elif estado == "desbloquear":
            nuevo_estado = Usuario.Estado.ACTIVA
        else:
            return error("RUTA_INVALIDA", "Estado no soportado.", http_status=404)
        usuario = cambiar_estado_usuario(request.user, usuario, nuevo_estado)
        return ok(UsuarioSerializer(usuario).data, "Estado de usuario actualizado.")


class EstudianteListCreateView(APIView):
    permission_classes = [EsAdminEscolar]
    serializer_class = EstudianteSerializer

    @extend_schema(tags=["Cuentas"], request=None, responses=EstudianteSerializer(many=True))
    def get(self, request):
        return ok(
            EstudianteSerializer(Estudiante.objects.all().order_by("id"), many=True).data,
            "Estudiantes obtenidos.",
        )

    @extend_schema(tags=["Cuentas"], request=EstudianteSerializer)
    def post(self, request):
        serializer = EstudianteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            estudiante = crear_estudiante(request.user, serializer.validated_data)
        except (IntegrityError, ValueError) as exc:
            return error("CONFLICTO", str(exc), http_status=409)
        return ok(EstudianteSerializer(estudiante).data, "Estudiante creado.", status.HTTP_201_CREATED)


class EstudianteDetailView(APIView):
    permission_classes = [EsAdminEscolar]
    serializer_class = EstudianteSerializer

    def get_object(self, pk):
        return Estudiante.objects.get(pk=pk)

    @extend_schema(tags=["Cuentas"], request=None, responses=EstudianteSerializer)
    def get(self, request, pk):
        try:
            estudiante = self.get_object(pk)
        except Estudiante.DoesNotExist:
            return error("NO_ENCONTRADO", "El estudiante no existe.", http_status=404)
        return ok(EstudianteSerializer(estudiante).data, "Estudiante obtenido.")

    @extend_schema(tags=["Cuentas"], request=EstudianteSerializer)
    def patch(self, request, pk):
        try:
            estudiante = self.get_object(pk)
        except Estudiante.DoesNotExist:
            return error("NO_ENCONTRADO", "El estudiante no existe.", http_status=404)
        serializer = EstudianteSerializer(estudiante, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            estudiante = editar_estudiante(request.user, estudiante, serializer.validated_data)
        except (IntegrityError, ValueError) as exc:
            return error("CONFLICTO", str(exc), http_status=409)
        return ok(EstudianteSerializer(estudiante).data, "Estudiante actualizado.")

    @extend_schema(tags=["Cuentas"], request=None)
    def delete(self, request, pk):
        try:
            estudiante = self.get_object(pk)
        except Estudiante.DoesNotExist:
            return error("NO_ENCONTRADO", "El estudiante no existe.", http_status=404)
        estudiante.delete()
        return ok({}, "Estudiante eliminado.")


class RelacionListCreateView(APIView):
    permission_classes = [EsAdminEscolar]
    serializer_class = RelacionPadreEstudianteSerializer

    @extend_schema(tags=["Cuentas"], request=None, responses=RelacionPadreEstudianteSerializer(many=True))
    def get(self, request):
        return ok(
            RelacionPadreEstudianteSerializer(
                RelacionPadreEstudiante.objects.all().order_by("id"), many=True
            ).data,
            "Relaciones obtenidas.",
        )

    @extend_schema(tags=["Cuentas"], request=RelacionPadreEstudianteSerializer)
    def post(self, request):
        serializer = RelacionPadreEstudianteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            relacion = crear_relacion(request.user, serializer.validated_data)
        except (IntegrityError, ValueError) as exc:
            return error("CONFLICTO", str(exc), http_status=409)
        return ok(
            RelacionPadreEstudianteSerializer(relacion).data,
            "Relación creada.",
            status.HTTP_201_CREATED,
        )


class RelacionDetailView(APIView):
    permission_classes = [EsAdminEscolar]
    serializer_class = RelacionPadreEstudianteSerializer

    @extend_schema(tags=["Cuentas"], request=None)
    def delete(self, request, pk):
        try:
            relacion = RelacionPadreEstudiante.objects.get(pk=pk)
        except RelacionPadreEstudiante.DoesNotExist:
            return error("NO_ENCONTRADO", "La relación no existe.", http_status=404)
        relacion.delete()
        return ok({}, "Relación eliminada.")
