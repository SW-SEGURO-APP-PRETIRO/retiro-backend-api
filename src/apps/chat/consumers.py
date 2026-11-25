"""WebSocket de notificaciones (/ws/notificaciones/).

Seguridad:
- La identidad sale SOLO de la sesión de Django (`scope["user"]`, vía AuthMiddlewareStack). El cliente
  nunca envía su `usuario_id`; cualquier campo de ese tipo en un mensaje se ignora.
- Los anónimos se aceptan un instante y se cierran con el código 4001 (así el navegador lo ve en `onclose`).
- Cada socket solo recibe SU copia de cada notificación y solo puede marcar como leídas las suyas.

Presencia: hash de Redis `presencia:{usuario_id}` con un campo por conexión (varias pestañas) y expiración
de 120 s que se renueva con cada `ping`; al cerrar el socket se elimina su campo.
"""
import json
import logging

import redis.asyncio as redis
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from . import services

logger = logging.getLogger(__name__)

CODIGO_NO_AUTENTICADO = 4001
ESTADOS_PRESENCIA = {"ACTIVO", "AUSENTE"}
PRESENCIA_TTL = 120  # segundos
MAX_BYTES_MENSAJE = 4096


class NotificacionesConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        self.user = None
        self.grupos = []
        self._redis = None
        if user is None or not user.is_authenticated:
            await self.accept()
            await self.close(code=CODIGO_NO_AUTENTICADO)
            return
        self.user = user

        self.grupos = [services.grupo_usuario(user.pk)]
        if user.rol == "ADMIN_SISTEMA":
            self.grupos.append(services.GRUPO_ADMIN_SISTEMA)
        elif user.rol == "ADMIN_ESCOLAR" and user.institucion_id:
            self.grupos.append(services.grupo_admin_escolar(user.institucion_id))
        if user.institucion_id:
            # Para enterarse de quién se conecta o desconecta en su institución (lista «En línea»)
            self.grupos.append(services.grupo_presencia(user.institucion_id))
        for grupo in self.grupos:
            await self.channel_layer.group_add(grupo, self.channel_name)

        await self.accept()
        await self._guardar_presencia("ACTIVO")
        await self._anunciar_presencia(conectado=True)
        await self.send_json(
            {
                "evento": "conexion_establecida",
                "usuario_id": user.pk,
                "rol": user.rol,
                "grupos": self.grupos,
            }
        )

    async def disconnect(self, code):
        if self.user is None:
            return
        for grupo in self.grupos:
            await self.channel_layer.group_discard(grupo, self.channel_name)
        conexiones_restantes = 0
        try:
            cliente = self._cliente_redis()
            await cliente.hdel(self._clave_presencia(), self.channel_name)
            conexiones_restantes = await cliente.hlen(self._clave_presencia())
        except Exception:  # noqa: BLE001
            logger.warning("No se pudo limpiar la presencia en Redis.", exc_info=True)
        finally:
            await self._cerrar_redis()
        # Con otra pestaña abierta el usuario sigue en línea: solo se avisa al cerrar la última
        if not conexiones_restantes:
            await self._anunciar_presencia(conectado=False)

    # ------------------------------------------------------------------ mensajes del cliente
    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data is None or len(text_data) > MAX_BYTES_MENSAJE:
            await self.close(code=1009)
            return
        try:
            contenido = json.loads(text_data)
        except ValueError:
            await self._error("JSON_INVALIDO")
            return
        await self.receive_json(contenido)

    async def receive_json(self, content, **kwargs):
        if not isinstance(content, dict):
            await self._error("MENSAJE_INVALIDO")
            return
        evento = content.get("evento")

        if evento == "ping":
            await self._renovar_presencia()
            await self.send_json({"evento": "pong"})
        elif evento == "presencia":
            estado = content.get("estado")
            if estado not in ESTADOS_PRESENCIA:
                await self._error("ESTADO_INVALIDO", validos=sorted(ESTADOS_PRESENCIA))
                return
            await self._guardar_presencia(estado)
            await self.send_json({"evento": "presencia.actualizada", "estado": estado})
        elif evento == "notificacion.leer":
            notificacion_id = content.get("notificacion_id")
            if not isinstance(notificacion_id, int) or isinstance(notificacion_id, bool):
                await self._error("NOTIFICACION_INVALIDA")
                return
            # Siempre contra el usuario de la sesión: no se puede marcar la de otra persona
            notificacion = await database_sync_to_async(services.marcar_leida)(self.user.pk, notificacion_id)
            if notificacion is None:
                await self._error("NOTIFICACION_NO_ENCONTRADA", notificacion_id=notificacion_id)
            else:
                await self.send_json({"evento": "notificacion.leida", "notificacion_id": notificacion_id})
        else:
            await self._error("EVENTO_DESCONOCIDO")

    # ------------------------------------------------------------- mensajes desde Channels
    async def notificacion_mensaje(self, event):
        """Llega por el grupo del usuario o del rol; reenvía solo la copia de ESTE usuario."""
        copia = event["por_usuario"].get(str(self.user.pk))
        if copia is None:
            return
        await self.send_json(
            {"evento": event["evento"], "subevento": event.get("subevento", ""), "notificacion": copia}
        )

    async def chat_mensaje(self, event):
        """Reenvía mensajes de chat en tiempo real a los miembros de la sala."""
        await self.send_json(
            {"evento": event.get("evento", "chat.mensaje"), "mensaje": event.get("mensaje", {})}
        )

    async def presencia_cambio(self, event):
        """Alguien de la institución se conectó o desconectó: el navegador refresca la lista «En línea»."""
        await self.send_json(
            {
                "evento": services.EVENTO_PRESENCIA,
                "usuario_id": event["usuario_id"],
                "institucion_id": event.get("institucion_id"),
                "conectado": event["conectado"],
            }
        )

    # ------------------------------------------------------------------------- auxiliares
    async def _anunciar_presencia(self, conectado):
        """Publica el cambio en la institución del usuario y a los Administradores del Sistema.
        Solo viaja el id (sin nombres ni datos personales); el navegador consulta la lista por la API."""
        destinos = [services.GRUPO_ADMIN_SISTEMA]
        if self.user.institucion_id:
            destinos.append(services.grupo_presencia(self.user.institucion_id))
        mensaje = {
            "type": "presencia.cambio",
            "usuario_id": self.user.pk,
            "institucion_id": self.user.institucion_id,
            "conectado": conectado,
        }
        try:
            for grupo in destinos:
                await self.channel_layer.group_send(grupo, mensaje)
        except Exception:  # noqa: BLE001 - la presencia es accesoria: nunca cierra el socket
            logger.warning("No se pudo anunciar el cambio de presencia.", exc_info=True)

    async def _error(self, codigo, **extra):
        await self.send_json({"evento": "error", "codigo": codigo, **extra})

    def _clave_presencia(self):
        return f"presencia:{self.user.pk}"

    def _cliente_redis(self):
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def _cerrar_redis(self):
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:  # noqa: BLE001
                pass
            self._redis = None

    async def _guardar_presencia(self, estado):
        try:
            cliente = self._cliente_redis()
            clave = self._clave_presencia()
            await cliente.hset(clave, self.channel_name, estado)
            await cliente.expire(clave, PRESENCIA_TTL)
        except Exception:  # noqa: BLE001 - la presencia es accesoria: no cierra el socket
            logger.warning("No se pudo guardar la presencia en Redis.", exc_info=True)

    async def _renovar_presencia(self):
        try:
            await self._cliente_redis().expire(self._clave_presencia(), PRESENCIA_TTL)
        except Exception:  # noqa: BLE001
            logger.warning("No se pudo renovar la presencia en Redis.", exc_info=True)
