"""CRUD de estudiantes: paginación y búsqueda en el servidor, y eliminación segura."""
import datetime

import pytest
from django.test import Client

from apps.auditoria.models import EventoAuditoria
from apps.cuentas.models import Estudiante, RelacionPadreEstudiante, Usuario
from apps.instituciones.models import Curso, Institucion

URL = "/api/v1/cuentas/estudiantes/"


@pytest.fixture
def colegio(db):
    return Institucion.objects.create(nombre="Colegio", ruc="1790000000001", correo="c@example.test", estado="ACTIVA")


@pytest.fixture
def otro_colegio(db):
    return Institucion.objects.create(nombre="Otro", ruc="1790000000002", correo="o@example.test", estado="ACTIVA")


@pytest.fixture
def curso(colegio):
    return Curso.objects.create(institucion_id=colegio.pk, nombre="1ro A", hora_salida=datetime.time(13, 0))


@pytest.fixture
def admin(colegio):
    return Usuario.objects.create(
        correo="admin@example.test", cedula="1700000001", nombres="Ana", apellidos="Admin",
        rol="ADMIN_ESCOLAR", institucion_id=colegio.pk, estado="ACTIVA",
    )


@pytest.fixture
def cliente(admin):
    c = Client()
    c.force_login(admin)
    return c


def crear_estudiante(colegio, curso, n, **extra):
    datos = dict(
        institucion_id=colegio.pk, cedula=f"17{n:08d}", nombres=f"Nombre{n:02d}", apellidos=f"Apellido{n:02d}",
        fecha_nacimiento=datetime.date(2015, 1, 1), curso_id=curso.pk,
    )
    datos.update(extra)
    return Estudiante.objects.create(**datos)


# ---------------------------------------------------------------------------------- paginación
@pytest.mark.django_db
def test_listado_paginado_en_el_servidor(cliente, colegio, curso):
    for n in range(25):
        crear_estudiante(colegio, curso, n)
    primera = cliente.get(f"{URL}?page=1").json()["datos"]
    assert primera["total"] == 25 and len(primera["resultados"]) == 20
    assert primera["siguiente"] and primera["anterior"] is None
    segunda = cliente.get(f"{URL}?page=2").json()["datos"]
    assert len(segunda["resultados"]) == 5
    # Sin repetidos entre páginas y en orden alfabético por apellido
    ids = [e["id"] for e in primera["resultados"] + segunda["resultados"]]
    assert len(set(ids)) == 25
    assert primera["resultados"][0]["apellidos"] == "Apellido00"


@pytest.mark.django_db
def test_pagina_fuera_de_rango_devuelve_la_ultima(cliente, colegio, curso):
    for n in range(3):
        crear_estudiante(colegio, curso, n)
    respuesta = cliente.get(f"{URL}?page=99")
    assert respuesta.status_code == 200
    assert len(respuesta.json()["datos"]["resultados"]) == 3


@pytest.mark.django_db
def test_sin_page_responde_la_lista_completa_como_antes(cliente, colegio, curso):
    for n in range(25):
        crear_estudiante(colegio, curso, n)
    datos = cliente.get(URL).json()["datos"]
    assert isinstance(datos, list) and len(datos) == 25


@pytest.mark.django_db
def test_busqueda_por_nombre_apellido_o_cedula_y_filtro_de_estado(cliente, colegio, curso):
    crear_estudiante(colegio, curso, 1, nombres="Luis", apellidos="Andrade")
    crear_estudiante(colegio, curso, 2, nombres="Sofía", apellidos="Andrade", estado="INACTIVO")
    crear_estudiante(colegio, curso, 3, nombres="Pedro", apellidos="Mora", cedula="1799999990")

    def buscar(consulta):
        return [e["nombres"] for e in cliente.get(f"{URL}?page=1&{consulta}").json()["datos"]["resultados"]]

    assert buscar("q=andrade") == ["Luis", "Sofía"]
    assert buscar("q=Luis%20Andrade") == ["Luis"]  # cada palabra en cualquier campo
    assert buscar("q=99999") == ["Pedro"]  # por cédula
    assert buscar("q=andrade&estado=INACTIVO") == ["Sofía"]
    assert buscar("estado=NO_EXISTE") == ["Luis", "Sofía", "Pedro"]  # estado desconocido se ignora


@pytest.mark.django_db
def test_paginacion_no_mezcla_instituciones(cliente, colegio, otro_colegio, curso):
    crear_estudiante(colegio, curso, 1)
    crear_estudiante(otro_colegio, curso, 2)
    assert cliente.get(f"{URL}?page=1").json()["datos"]["total"] == 1


# ---------------------------------------------------------------------------- eliminación segura
@pytest.mark.django_db
def test_eliminar_con_representantes_responde_409_y_no_borra(cliente, colegio, curso):
    estudiante = crear_estudiante(colegio, curso, 1)
    padre = Usuario.objects.create(
        correo="padre@example.test", cedula="1700000009", nombres="Pedro", apellidos="Padre",
        rol="PADRE", institucion_id=colegio.pk, estado="ACTIVA",
    )
    RelacionPadreEstudiante.objects.create(institucion_id=colegio.pk, padre=padre, estudiante=estudiante)

    respuesta = cliente.delete(f"{URL}{estudiante.pk}/")
    assert respuesta.status_code == 409
    mensaje = respuesta.json()["error"]["mensaje"]
    assert "representantes vinculados" in mensaje and "inactivo" in mensaje
    assert Estudiante._base_manager.filter(pk=estudiante.pk).exists()


@pytest.mark.django_db
def test_eliminar_sin_historial_borra_y_queda_en_bitacora(cliente, colegio, curso):
    estudiante = crear_estudiante(colegio, curso, 1)
    assert cliente.delete(f"{URL}{estudiante.pk}/").status_code == 200
    assert not Estudiante._base_manager.filter(pk=estudiante.pk).exists()
    assert EventoAuditoria.objects.filter(tipo="ESTUDIANTE_ELIMINADO").exists()


@pytest.mark.django_db
def test_no_se_elimina_estudiante_de_otra_institucion(cliente, otro_colegio, curso):
    ajeno = crear_estudiante(otro_colegio, curso, 1)
    assert cliente.delete(f"{URL}{ajeno.pk}/").status_code == 404
    assert Estudiante._base_manager.filter(pk=ajeno.pk).exists()
