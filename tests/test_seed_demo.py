"""Script de datos de prueba (scripts/seed_demo.py): compatible con datos ya cargados y robusto ante ids grandes."""
from types import SimpleNamespace

import pytest

from apps.cuentas.models import Estudiante, Usuario
from apps.cuidadores.models import Cuidador
from apps.instituciones.models import Institucion
from scripts.seed_demo import _cedula, _codigo_cedula, sembrar
from shared.utils.validadores import _es_cedula


def _patrones(codigo):
    """Las cuatro formas en que la semilla arma cédulas a partir del código de la institución."""
    return [
        f"17{codigo}{1:02d}0001",  # cuentas (admin, padre, guardia, cuidador)
        f"17{codigo}20{codigo:02d}00",  # cuidador fijo
        f"17{codigo}30{codigo:02d}00",  # cuidador temporal
        f"17{codigo}10{1:04d}",  # estudiantes
    ]


@pytest.mark.parametrize("inst_id", [1, 2, 3, 4, 5])
def test_ids_pequenos_generan_exactamente_las_mismas_cedulas_que_antes(inst_id):
    """Quien ya cargó los datos (ids 1-5) obtiene las mismas cédulas: get_or_create no duplica nada."""
    inst = SimpleNamespace(id=inst_id)
    antes = [_cedula(p) for p in _patrones(inst_id)]  # fórmula original: inst.id directo
    ahora = [_cedula(p) for p in _patrones(_codigo_cedula(inst, posicion=1))]
    assert ahora == antes


@pytest.mark.parametrize("inst_id", [6, 9, 10, 1002, 10002])
@pytest.mark.parametrize("posicion", [1, 2])
def test_ids_grandes_generan_cedulas_validas(inst_id, posicion):
    for patron in _patrones(_codigo_cedula(SimpleNamespace(id=inst_id), posicion)):
        assert len(patron) == 9 and _es_cedula(_cedula(patron))


def _resumen():
    return (
        Institucion.objects.count(),
        Usuario._base_manager.count(),
        Estudiante._base_manager.count(),
        Cuidador._base_manager.count(),
    )


def _todo_valido():
    cedulas = list(Usuario._base_manager.values_list("cedula", flat=True))
    cedulas += list(Estudiante._base_manager.values_list("cedula", flat=True))
    cedulas += list(Cuidador._base_manager.values_list("cedula", flat=True))
    return all(_es_cedula(c) for c in cedulas)


@pytest.mark.django_db
def test_semilla_en_base_nueva_y_repetida_no_duplica():
    sembrar("Clave-De-Prueba#2026")
    primera = _resumen()
    assert primera[0] == 2 and primera[2] > 0 and _todo_valido()
    sembrar("Clave-De-Prueba#2026")
    assert _resumen() == primera


@pytest.mark.django_db
def test_semilla_funciona_cuando_los_ids_de_institucion_son_grandes():
    """Reproduce el caso de SQL Server: ya hay colegios y los nuevos reciben ids altos."""
    for n in range(8):
        Institucion.objects.create(
            nombre=f"Colegio previo {n}", ruc=f"17900000{n:02d}001", correo=f"previo{n}@example.test", estado="ACTIVA"
        )
    sembrar("Clave-De-Prueba#2026")
    nuevas = Institucion.objects.exclude(nombre__startswith="Colegio previo")
    assert nuevas.count() == 2 and min(nuevas.values_list("id", flat=True)) >= 9
    assert _todo_valido()
    antes = _resumen()
    sembrar("Clave-De-Prueba#2026")
    assert _resumen() == antes  # repetirla tampoco duplica
