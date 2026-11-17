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
