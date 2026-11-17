from django.urls import path

from .views import (
    AprobarAutorizacionView,
    AutorizacionListView,
    CuidadorListCreateView,
    RevocarAutorizacionView,
    SolicitarAutorizacionView,
)

urlpatterns = [
    path("", CuidadorListCreateView.as_view(), name="cuidador-list-create"),
    path("autorizaciones/", AutorizacionListView.as_view(), name="autorizacion-list"),
    path("autorizaciones/<int:pk>/aprobar/", AprobarAutorizacionView.as_view(), name="autorizacion-aprobar"),
    path("autorizaciones/<int:pk>/revocar/", RevocarAutorizacionView.as_view(), name="autorizacion-revocar"),
    path("<int:pk>/solicitar-autorizacion/", SolicitarAutorizacionView.as_view(), name="cuidador-solicitar-autorizacion"),
]
