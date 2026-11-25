"""Indicación de usuarios conectados en el chat (presencia por WebSocket + consulta REST)."""
import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import Client

from apps.chat import services
from apps.chat.consumers import NotificacionesConsumer
from apps.cuentas.models import Usuario
from apps.instituciones.models import Institucion


@pytest.fixture
def colegios(db):
    a = Institucion.objects.create(nombre="Colegio A", ruc="1790000000001", correo="a@example.test", estado="ACTIVA")
    b = Institucion.objects.create(nombre="Colegio B", ruc="1790000000002", correo="b@example.test", estado="ACTIVA")
    return a, b


def _usuario(correo, cedula, rol, institucion=None, **extra):
    return Usuario.objects.create(
        correo=correo, cedula=cedula, nombres=correo.split("@")[0].title(), apellidos="Prueba", rol=rol,
        institucion_id=institucion.pk if institucion else None, estado="ACTIVA", **extra,
    )


@pytest.fixture
def personas(colegios):
    a, b = colegios
    return {
        "admin_a": _usuario("admin.a@example.test", "1700000001", "ADMIN_ESCOLAR", a),
        "padre_a": _usuario("padre.a@example.test", "1700000002", "PADRE", a),
        "padre_b": _usuario("padre.b@example.test", "1700000003", "PADRE", b),
        "sistema": _usuario("root@example.test", "1700000004", "ADMIN_SISTEMA"),
    }


@pytest.fixture
def todos_en_linea(monkeypatch):
    """Simula Redis: todos los consultados tienen una conexión abierta."""
    monkeypatch.setattr(services, "_leer_presencias", lambda ids: {uid: "ACTIVO" for uid in ids})


def conectados(usuario, consulta=""):
    cliente = Client()
    cliente.force_login(usuario)
    return cliente.get(f"/api/v1/chat/conectados/{consulta}")


@pytest.mark.django_db
def test_lista_solo_usuarios_de_la_misma_institucion(personas, todos_en_linea):
    respuesta = conectados(personas["padre_a"])
    assert respuesta.status_code == 200
    datos = respuesta.json()["datos"]
    ids = {u["id"] for u in datos["usuarios"]}
    # Su colegio y el Administrador del Sistema (que también participa en la sala); nunca el otro colegio
    assert ids == {personas["admin_a"].pk, personas["padre_a"].pk, personas["sistema"].pk}
    assert datos["total"] == 3 and datos["disponible"] is True
    assert datos["usuarios"][0]["es_usted"] is True  # el propio usuario aparece primero
    assert "correo" not in datos["usuarios"][0] and "cedula" not in datos["usuarios"][0]


@pytest.mark.django_db
def test_usuario_de_colegio_no_puede_espiar_otra_institucion(personas, colegios, todos_en_linea):
    _, colegio_b = colegios
    ids = {u["id"] for u in conectados(personas["padre_a"], f"?institucion_id={colegio_b.pk}").json()["datos"]["usuarios"]}
    assert personas["padre_b"].pk not in ids


@pytest.mark.django_db
def test_admin_sistema_consulta_la_sala_que_elige(personas, colegios, todos_en_linea):
    _, colegio_b = colegios
    ids = {u["id"] for u in conectados(personas["sistema"], f"?institucion_id={colegio_b.pk}").json()["datos"]["usuarios"]}
    assert ids == {personas["padre_b"].pk, personas["sistema"].pk}
    assert conectados(personas["sistema"], "?institucion_id=abc").status_code == 400


@pytest.mark.django_db
def test_solo_aparecen_los_que_tienen_conexion_abierta(personas, monkeypatch):
    monkeypatch.setattr(services, "_leer_presencias", lambda ids: {personas["admin_a"].pk: "AUSENTE"})
    usuarios = conectados(personas["padre_a"]).json()["datos"]["usuarios"]
    assert [(u["id"], u["estado"]) for u in usuarios] == [(personas["admin_a"].pk, "AUSENTE")]


@pytest.mark.django_db
def test_sin_redis_el_chat_sigue_funcionando(personas, monkeypatch):
    def caido(ids):
        raise ConnectionError("Redis no responde")

    monkeypatch.setattr(services, "_leer_presencias", caido)
    respuesta = conectados(personas["padre_a"])
    assert respuesta.status_code == 200 and respuesta.json()["datos"]["disponible"] is False


@pytest.mark.django_db
def test_anonimo_no_consulta_presencia(db):
    assert Client().get("/api/v1/chat/conectados/").status_code in (401, 403)


@pytest.mark.django_db(transaction=True)
def test_websocket_anuncia_conexion_y_desconexion(personas, settings):
    settings.REDIS_URL = "redis://127.0.0.1:6399/0"  # sin Redis real: la presencia falla en silencio
    admin = personas["admin_a"]

    async def flujo():
        capa = get_channel_layer()
        oyente = await capa.new_channel()
        await capa.group_add(services.grupo_presencia(admin.institucion_id), oyente)
        socket = WebsocketCommunicator(NotificacionesConsumer.as_asgi(), "/ws/notificaciones/")
        socket.scope["user"] = admin  # la identidad sale de la sesión, nunca del cliente
        conectado, _ = await socket.connect()
        assert conectado
        aviso = await capa.receive(oyente)
        assert (aviso["type"], aviso["usuario_id"], aviso["conectado"]) == ("presencia.cambio", admin.pk, True)
        await socket.disconnect()
        aviso = await capa.receive(oyente)
        assert (aviso["usuario_id"], aviso["conectado"]) == (admin.pk, False)

    async_to_sync(flujo)()
