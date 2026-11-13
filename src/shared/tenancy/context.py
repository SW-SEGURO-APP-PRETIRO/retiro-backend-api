"""Institución "actual" de la petición (aislamiento multi-institución).

Es un único punto: el middleware la fija a partir del usuario autenticado y el
`TenantManager` la aplica a TODA consulta. Sin institución resuelta no se obtiene ningún dato.
"""
from contextlib import contextmanager
from contextvars import ContextVar

SIN_FILTRO = object()  # uso interno: semillas, migraciones de datos, verificación de bitácora

_institucion_actual: ContextVar = ContextVar("institucion_actual", default=None)


def institucion_actual():
    """Devuelve el id de la institución, `SIN_FILTRO` o `None` (sin resolver = no ver nada)."""
    return _institucion_actual.get()


def fijar_institucion(valor):
    """Fija la institución y devuelve el token para restaurar el valor anterior."""
    return _institucion_actual.set(valor)


def restaurar_institucion(token):
    _institucion_actual.reset(token)


@contextmanager
def contexto_institucion(institucion_id: int):
    token = _institucion_actual.set(institucion_id)
    try:
        yield
    finally:
        _institucion_actual.reset(token)


@contextmanager
def sin_filtro():
    """Desactiva el filtro. Solo para procesos internos del sistema, NUNCA desde una vista."""
    token = _institucion_actual.set(SIN_FILTRO)
    try:
        yield
    finally:
        _institucion_actual.reset(token)