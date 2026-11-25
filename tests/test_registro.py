"""Registro (SignUp) de una institución con su Administrador Escolar y aprobación por el ADMIN_SISTEMA."""
import pytest
from django.test import Client

from apps.auditoria.models import EventoAuditoria
from apps.chat.models import Notificacion
from apps.cuentas.models import Usuario
from apps.instituciones.models import Institucion

CEDULA_VALIDA = "1723456701"
RUC_VALIDO = "1799123408001"
CONTRASENA = "Patio-Escolar#2026"
URL = "/autenticacion/registrar/"


def datos(**cambios):
    base = {
        "admin_nombres": "María José",
        "admin_apellidos": "Cárdenas Ortiz",
        "admin_cedula": CEDULA_VALIDA,
        "admin_telefono": "0991234567",
        "admin_correo": "maria.cardenas@example.test",
        "nombre": "Unidad Educativa Los Pinos",
        "ruc": RUC_VALIDO,
        "responsable": "Rector Juan Pérez",
        "telefono": "022345678",
        "correo": "secretaria@lospinos.example.test",
        "direccion": "Av. Principal 123 y Calle Secundaria",
        "contrasena": CONTRASENA,
        "confirmar_contrasena": CONTRASENA,
    }
    base.update(cambios)
    return base


@pytest.fixture
def admin_sistema(db):
    return Usuario.objects.create(
        correo="root@example.test", cedula="1700000002", nombres="Admin", apellidos="Sistema",
        rol="ADMIN_SISTEMA", institucion_id=None, estado="ACTIVA",
    )


def registrar(client, **cambios):
    return client.post(URL, datos(**cambios))


def ingresar(correo, contrasena):
    return Client().post(
        "/api/v1/autenticacion/ingresar/", {"correo": correo, "contrasena": contrasena}, content_type="application/json"
    )


# ------------------------------------------------------------------------------------- pantalla
@pytest.mark.django_db
def test_pantalla_de_registro_y_enlace_desde_el_login(client):
    pagina = client.get(URL)
    assert pagina.status_code == 200
    html = pagina.content.decode()
    for campo in ("admin_cedula", "admin_correo", "ruc", "nombre", "contrasena", "confirmar_contrasena"):
        assert f'name="{campo}"' in html
    # Validación en el cliente: obligatorios, solo números y longitudes
    assert 'pattern="[0-9]{10}"' in html and 'pattern="(0[1-9]|1[0-9]|2[0-4]|30)[0-69][0-9]{10}"' in html
    assert "required" in html and 'maxlength="13"' in html
    assert "csrfmiddlewaretoken" in html
    assert URL in client.get("/autenticacion/ingresar/").content.decode()


@pytest.mark.django_db
def test_usuario_con_sesion_no_ve_el_registro(client, admin_sistema):
    client.force_login(admin_sistema)
    assert client.get(URL).status_code == 302


@pytest.mark.django_db
def test_registro_exige_csrf(db):
    respuesta = Client(enforce_csrf_checks=True).post(URL, datos())
    assert respuesta.status_code == 403
    assert not Institucion.objects.exists()


# ---------------------------------------------------------------------------- registro válido
@pytest.mark.django_db
def test_registro_valido_queda_pendiente_con_contrasena_elegida(client, admin_sistema):
    respuesta = registrar(client)
    assert respuesta.status_code == 302 and respuesta.url.endswith("?enviado=1")

    institucion = Institucion.objects.get(ruc=RUC_VALIDO)
    assert institucion.estado == Institucion.Estado.PENDIENTE_APROBACION
    admin = Usuario.objects.get(correo="maria.cardenas@example.test")
    assert admin.rol == "ADMIN_ESCOLAR" and admin.institucion_id == institucion.pk
    assert admin.estado == Usuario.Estado.PENDIENTE
    assert admin.check_password(CONTRASENA) and not admin.contrasena_temporal
    assert admin.password != CONTRASENA  # se guarda como hash, nunca en texto plano

    # Bitácora y aviso en tiempo real al Administrador del Sistema
    assert EventoAuditoria.objects.filter(tipo="INSTITUCION_REGISTRADA").exists()
    assert Notificacion._base_manager.filter(destinatario_id=admin_sistema.pk, tipo="INSTITUCION_PENDIENTE").exists()

    confirmacion = client.get(respuesta.url)
    assert "pendiente de aprobación" in confirmacion.content.decode()
    # Recargar la confirmación no reenvía nada y vuelve al formulario
    assert client.get(respuesta.url).status_code == 302
    assert Institucion.objects.count() == 1


@pytest.mark.django_db
def test_no_puede_ingresar_hasta_ser_aprobada_y_no_se_revela_a_terceros(client):
    registrar(client)
    sin_clave = ingresar("maria.cardenas@example.test", "otra-clave-cualquiera")
    assert sin_clave.status_code == 401
    assert sin_clave.json()["error"]["mensaje"] == "Credenciales inválidas."
    con_clave = ingresar("maria.cardenas@example.test", CONTRASENA)
    assert con_clave.status_code == 401
    assert "pendiente de aprobación" in con_clave.json()["error"]["mensaje"]


# ------------------------------------------------------------------- aprobación del ADMIN_SISTEMA
@pytest.mark.django_db
def test_admin_sistema_aprueba_y_el_administrador_escolar_ya_ingresa(
    client, admin_sistema, mailoutbox, django_capture_on_commit_callbacks
):
    registrar(client)
    institucion = Institucion.objects.get(ruc=RUC_VALIDO)
    panel = Client()
    panel.force_login(admin_sistema)
    pendientes = panel.get("/api/v1/instituciones/pendientes/").json()["datos"]
    assert [i["ruc"] for i in pendientes] == [RUC_VALIDO]

    with django_capture_on_commit_callbacks(execute=True):
        decision = panel.post(
            f"/api/v1/instituciones/{institucion.pk}/aprobar/", {"aprobada": True}, content_type="application/json"
        )
    assert decision.status_code == 200
    institucion.refresh_from_db()
    assert institucion.estado == Institucion.Estado.ACTIVA
    assert Usuario.objects.get(correo="maria.cardenas@example.test").estado == Usuario.Estado.ACTIVA
    assert [m.to for m in mailoutbox] == [["maria.cardenas@example.test"]]
    assert "aprobada" in mailoutbox[0].subject

    ingreso = ingresar("maria.cardenas@example.test", CONTRASENA)
    assert ingreso.status_code == 200
    assert ingreso.json()["datos"]["usuario"]["rol"] == "ADMIN_ESCOLAR"


@pytest.mark.django_db
def test_admin_sistema_rechaza_con_motivo(client, admin_sistema, mailoutbox, django_capture_on_commit_callbacks):
    registrar(client)
    institucion = Institucion.objects.get(ruc=RUC_VALIDO)
    panel = Client()
    panel.force_login(admin_sistema)
    with django_capture_on_commit_callbacks(execute=True):
        panel.post(
            f"/api/v1/instituciones/{institucion.pk}/aprobar/",
            {"aprobada": False, "motivo": "El RUC no corresponde a una institución educativa."},
            content_type="application/json",
        )
    institucion.refresh_from_db()
    assert institucion.estado == Institucion.Estado.RECHAZADA
    assert "no corresponde" in mailoutbox[0].body
    rechazo = ingresar("maria.cardenas@example.test", CONTRASENA)
    assert rechazo.status_code == 401 and "no fue aprobada" in rechazo.json()["error"]["mensaje"]


# ------------------------------------------------------------------------ validación en servidor
@pytest.mark.django_db
@pytest.mark.parametrize(
    "cambios, campo, mensaje",
    [
        ({"admin_cedula": "1234567890"}, "admin_cedula", "Cédula ecuatoriana inválida"),
        ({"admin_cedula": "17234ABC01"}, "admin_cedula", "Cédula ecuatoriana inválida"),
        ({"ruc": "179123456700"}, "ruc", "13 dígitos"),
        ({"ruc": "9991234567001"}, "ruc", "código de provincia"),
        ({"ruc": "1771234567001"}, "ruc", "RUC inválido"),
        ({"ruc": "1791234567000"}, "ruc", "establecimiento"),
        ({"ruc": "17912345670AB"}, "ruc", "RUC inválido"),
        ({"telefono": "02-234-567"}, "telefono", "Solo números"),
        ({"admin_correo": "no-es-un-correo"}, "admin_correo", "Escribe un correo válido"),
        ({"confirmar_contrasena": "Distinta#2026xx"}, "confirmar_contrasena", "no coinciden"),
        ({"contrasena": "12345678901", "confirmar_contrasena": "12345678901"}, "contrasena", "numérica"),
        ({"contrasena": "corta#1", "confirmar_contrasena": "corta#1"}, "contrasena", "al menos 10"),
        ({"nombre": ""}, "nombre", "Nombre de la institución es obligatorio."),
        ({"correo": "maria.cardenas@example.test"}, "admin_correo", "distinto al correo institucional"),
    ],
)
def test_datos_invalidos_se_rechazan_con_mensaje_claro(client, cambios, campo, mensaje):
    respuesta = registrar(client, **cambios)
    assert respuesta.status_code == 200
    errores = respuesta.context["form"].errors
    assert campo in errores and mensaje in " ".join(errores[campo])
    assert not Institucion.objects.exists() and not Usuario.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize("ruc", ["1791234567001", "0990000000001", "1712345678001", "1760000000001"])
def test_ruc_inventado_con_estructura_correcta_se_acepta(client, ruc):
    """No se exige el dígito verificador: el SRI emite RUCs que ya no lo cumplen."""
    respuesta = registrar(client, ruc=ruc)
    assert respuesta.status_code == 302
    assert Institucion.objects.filter(ruc=ruc, estado=Institucion.Estado.PENDIENTE_APROBACION).exists()


@pytest.mark.django_db
def test_ruc_y_correo_duplicados_se_rechazan(client):
    registrar(client)
    otro = Client().post(
        URL, datos(admin_cedula="1723456719", admin_correo="maria.cardenas@example.test")
    )
    errores = otro.context["form"].errors
    assert "Ya existe una institución registrada con este RUC." in errores["ruc"]
    assert "Ya existe una cuenta con este correo." in errores["admin_correo"]
    assert "Ya existe una institución registrada con este correo." in errores["correo"]
    assert Institucion.objects.count() == 1


@pytest.mark.django_db
def test_html_de_errores_se_escapa(client):
    respuesta = registrar(client, nombre="<script>alert(1)</script>", ruc="1")
    html = respuesta.content.decode()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
