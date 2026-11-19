from django.db import IntegrityError
from django.utils import timezone

from apps.cuentas.services import nombres_usuarios

from .models import MensajeChat, SalaChat, SalaParticipante


def sala_general(institucion_id):
    sala = SalaChat._base_manager.filter(
        institucion_id=institucion_id, tipo=SalaChat.Tipo.GENERAL
    ).first()
    if sala:
        return sala
    try:
        return SalaChat._base_manager.create(
            institucion_id=institucion_id,
            tipo=SalaChat.Tipo.GENERAL,
            nombre="Sala general",
        )
    except IntegrityError:
        return SalaChat._base_manager.get(
            institucion_id=institucion_id, tipo=SalaChat.Tipo.GENERAL
        )


def registrar_participante(sala, usuario_id):
    SalaParticipante._base_manager.get_or_create(
        institucion_id=sala.institucion_id, sala=sala, usuario_id=usuario_id
    )


def historial(sala, limite=50):
    mensajes = list(
        MensajeChat._base_manager.filter(sala=sala).order_by("-enviado_en", "-id")[:limite]
    )
    usuarios = nombres_usuarios([mensaje.autor_id for mensaje in mensajes])
    return [datos_mensaje(mensaje, usuarios) for mensaje in reversed(mensajes)]


def guardar_mensaje(sala, usuario_id, contenido):
    contenido = contenido.strip()
    if not contenido or len(contenido) > 2000:
        raise ValueError("El mensaje debe tener entre 1 y 2000 caracteres.")
    mensaje = MensajeChat._base_manager.create(
        institucion_id=sala.institucion_id,
        sala=sala,
        autor_id=usuario_id,
        contenido=contenido,
        enviado_en=timezone.now(),
    )
    usuarios = nombres_usuarios([usuario_id])
    return datos_mensaje(mensaje, usuarios)


def datos_mensaje(mensaje, usuarios=None):
    usuario = (usuarios or nombres_usuarios([mensaje.autor_id])).get(mensaje.autor_id, {})
    return {
        "id": mensaje.pk,
        "contenido": mensaje.contenido,
        "autor_id": mensaje.autor_id,
        "autor": usuario.get("nombre", "Usuario"),
        "enviado_en": mensaje.enviado_en.isoformat(),
    }