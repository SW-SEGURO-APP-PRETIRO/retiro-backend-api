from django.urls import path

from .views import (
    CambioContrasenaTemporalView,
    CerrarSesionView,
    ConfirmarRecuperacionView,
    IngresoView,
    PerfilView,
    SolicitarRecuperacionView,
)


urlpatterns = [
    path("ingresar/", IngresoView.as_view(), name="ingresar"),
    path("cerrar-sesion/", CerrarSesionView.as_view(), name="cerrar-sesion"),
    path("perfil/", PerfilView.as_view(), name="perfil"),
    path(
        "cambiar-contrasena-temporal/",
        CambioContrasenaTemporalView.as_view(),
        name="cambiar-contrasena-temporal",
    ),
    path("solicitar-recuperacion/", SolicitarRecuperacionView.as_view(), name="solicitar-recuperacion"),
    path(
        "confirmar-recuperacion/",
        ConfirmarRecuperacionView.as_view(),
        name="confirmar-recuperacion",
    ),
]
