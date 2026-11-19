from django.urls import path

from .web_views import (
    estudiante_crear,
    estudiante_detalle,
    estudiante_editar,
    estudiante_eliminar,
    estudiantes_lista,
)

urlpatterns = [
    path("estudiantes/", estudiantes_lista, name="web-estudiantes"),
    path("estudiantes/nuevo/", estudiante_crear, name="web-estudiante-crear"),
    path("estudiantes/<int:pk>/", estudiante_detalle, name="web-estudiante-detalle"),
    path("estudiantes/<int:pk>/editar/", estudiante_editar, name="web-estudiante-editar"),
    path("estudiantes/<int:pk>/eliminar/", estudiante_eliminar, name="web-estudiante-eliminar"),
]