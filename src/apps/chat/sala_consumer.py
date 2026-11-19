import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .sala_services import guardar_mensaje, historial, registrar_participante, sala_general


class SalaGeneralConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not user.institucion_id:
            await self.close(code=4001)
            return
        self.user = user
        self.sala = await database_sync_to_async(sala_general)(user.institucion_id)
        self.grupo = f"sala_general_{user.institucion_id}"
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await database_sync_to_async(registrar_participante)(self.sala, user.pk)
        await self.accept()
        await self.send_json(
            {"evento": "historial", "mensajes": await database_sync_to_async(historial)(self.sala)}
        )

    async def disconnect(self, code):
        if hasattr(self, "grupo"):
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            payload = json.loads(text_data or "{}")
        except ValueError:
            await self.send_json({"evento": "error", "mensaje": "Mensaje inválido."})
            return
        if payload.get("evento") == "ping":
            await self.send_json({"evento": "pong"})
            return
        if payload.get("evento") != "mensaje":
            await self.send_json({"evento": "error", "mensaje": "Evento no soportado."})
            return
        try:
            mensaje = await database_sync_to_async(guardar_mensaje)(
                self.sala, self.user.pk, str(payload.get("contenido", ""))
            )
        except ValueError as exc:
            await self.send_json({"evento": "error", "mensaje": str(exc)})
            return
        await self.channel_layer.group_send(
            self.grupo, {"type": "chat.mensaje", "mensaje": mensaje}
        )

    async def chat_mensaje(self, event):
        await self.send_json({"evento": "mensaje", "mensaje": event["mensaje"]})