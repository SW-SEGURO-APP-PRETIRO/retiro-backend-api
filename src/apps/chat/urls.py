from django.urls import path

from .views import (
    MarcarTodasLeidasView,
    MensajeChatListCreateView,
    NotificacionLeidaView,
    NotificacionListView,
    SalaChatListCreateView,
    SalaGeneralMensajesView,
    UsuariosConectadosView,
)

urlpatterns = [
    path("", NotificacionListView.as_view(), name="notificacion-list"),
    path("marcar-todas-leidas/", MarcarTodasLeidasView.as_view(), name="notificacion-marcar-todas"),
    path("<int:pk>/leida/", NotificacionLeidaView.as_view(), name="notificacion-leida"),
    path("salas/", SalaChatListCreateView.as_view(), name="chat-sala-list-create"),
    path("salas/<int:pk>/mensajes/", MensajeChatListCreateView.as_view(), name="chat-mensaje-list-create"),
    path("general/", SalaGeneralMensajesView.as_view(), name="chat-sala-general"),
    path("conectados/", UsuariosConectadosView.as_view(), name="chat-usuarios-conectados"),
]


