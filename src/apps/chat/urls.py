from django.urls import path

from .views import MarcarTodasLeidasView, NotificacionLeidaView, NotificacionListView

urlpatterns = [
    path("", NotificacionListView.as_view(), name="notificacion-list"),
    path("marcar-todas-leidas/", MarcarTodasLeidasView.as_view(), name="notificacion-marcar-todas"),
    path("<int:pk>/leida/", NotificacionLeidaView.as_view(), name="notificacion-leida"),
]
