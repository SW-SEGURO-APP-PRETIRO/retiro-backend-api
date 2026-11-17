from django.urls import path

from .views import (
    CambiarEstadoUsuarioView,
    EstudianteDetailView,
    EstudianteListCreateView,
    RelacionDetailView,
    RelacionListCreateView,
    UsuarioDetailView,
    UsuarioListCreateView,
)


urlpatterns = [
    path("usuarios/", UsuarioListCreateView.as_view(), name="usuario-list-create"),
    path("usuarios/<int:pk>/", UsuarioDetailView.as_view(), name="usuario-detail"),
    path(
        "usuarios/<int:pk>/<str:estado>/",
        CambiarEstadoUsuarioView.as_view(),
        name="usuario-cambiar-estado",
    ),
    path("estudiantes/", EstudianteListCreateView.as_view(), name="estudiante-list-create"),
    path("estudiantes/<int:pk>/", EstudianteDetailView.as_view(), name="estudiante-detail"),
    path(
        "relaciones-padre-estudiante/",
        RelacionListCreateView.as_view(),
        name="relacion-list-create",
    ),
    path(
        "relaciones-padre-estudiante/<int:pk>/",
        RelacionDetailView.as_view(),
        name="relacion-detail",
    ),
]
