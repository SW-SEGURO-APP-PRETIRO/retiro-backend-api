from django.urls import path

from .views import (
    AprobarInstitucionView,
    CambiarEstadoInstitucionView,
    CursoDetailView,
    CursoListCreateView,
    InstitucionDetailView,
    InstitucionesPendientesView,
    MiInstitucionView,
    PuertaDetailView,
    PuertaListCreateView,
    RegistroInstitucionView,
)


urlpatterns = [
    path("", RegistroInstitucionView.as_view(), name="institucion-registro"),
    path("pendientes/", InstitucionesPendientesView.as_view(), name="instituciones-pendientes"),
    path("mi-institucion/", MiInstitucionView.as_view(), name="mi-institucion"),
    path("cursos/", CursoListCreateView.as_view(), name="curso-list-create"),
    path("cursos/<int:pk>/", CursoDetailView.as_view(), name="curso-detail"),
    path("puertas/", PuertaListCreateView.as_view(), name="puerta-list-create"),
    path("puertas/<int:pk>/", PuertaDetailView.as_view(), name="puerta-detail"),
    path("<int:pk>/", InstitucionDetailView.as_view(), name="institucion-detail"),
    path("<int:pk>/aprobar/", AprobarInstitucionView.as_view(), name="institucion-aprobar"),
    path(
        "<int:pk>/<str:accion>/",
        CambiarEstadoInstitucionView.as_view(),
        name="institucion-cambiar-estado",
    ),
]
