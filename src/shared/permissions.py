from rest_framework.permissions import BasePermission

from apps.cuentas.models import Rol
from apps.instituciones.models import Institucion


class EsAdminSistema(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol == Rol.ADMIN_SISTEMA)


class EsAdminEscolar(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or user.rol != Rol.ADMIN_ESCOLAR:
            return False
        return Institucion.objects.filter(pk=user.institucion_id, estado=Institucion.Estado.ACTIVA).exists()


class EsAdminSistemaOEscolar(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.rol == Rol.ADMIN_SISTEMA
                or (user.rol == Rol.ADMIN_ESCOLAR and Institucion.objects.filter(
                    pk=user.institucion_id, estado=Institucion.Estado.ACTIVA
                ).exists())
            )
        )


class EsPadreOAdminEscolar(BasePermission):
    """PADRE (sobre sus hijos) o ADMIN_ESCOLAR de una institución activa."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.rol == Rol.PADRE:
            return user.institucion_id is not None
        if user.rol == Rol.ADMIN_ESCOLAR:
            return Institucion.objects.filter(pk=user.institucion_id, estado=Institucion.Estado.ACTIVA).exists()
        return False


class EsMiembroInstitucion(BasePermission):
    """Cualquier usuario perteneciente a una institución activa (ADMIN_ESCOLAR, PADRE, GUARDIA o CUIDADOR_FIJO)."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.institucion_id:
            return False
        if user.rol not in (Rol.ADMIN_ESCOLAR, Rol.PADRE, Rol.GUARDIA, Rol.CUIDADOR_FIJO):
            return False
        return Institucion.objects.filter(pk=user.institucion_id, estado=Institucion.Estado.ACTIVA).exists()



class PerteneceAMismaInstitucion(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "institucion_id", None) is not None
            and getattr(obj, "institucion_id", None) == user.institucion_id
        )


class NoRequiereCambioContrasena(BasePermission):
    message = "Debe cambiar su contraseña temporal antes de usar este endpoint."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and not getattr(user, "contrasena_temporal", False)
        )
