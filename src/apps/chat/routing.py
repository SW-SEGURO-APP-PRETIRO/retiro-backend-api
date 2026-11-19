from django.urls import path

from .consumers import NotificacionesConsumer
from .sala_consumer import SalaGeneralConsumer

websocket_urlpatterns = [
    path("ws/notificaciones/", NotificacionesConsumer.as_asgi()),
    path("ws/chat/general/", SalaGeneralConsumer.as_asgi()),
]
