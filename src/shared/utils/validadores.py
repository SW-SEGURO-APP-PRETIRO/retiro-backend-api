"""Validadores de cédula y RUC ecuatorianos (sin reglas de negocio)."""
from django.core.exceptions import ValidationError


def _es_cedula(valor: str) -> bool:
    if not (valor.isdigit() and len(valor) == 10):
        return False
    provincia = int(valor[:2])
    if not (1 <= provincia <= 24 or provincia == 30):
        return False
    if int(valor[2]) >= 6:
        return False
    suma = 0
    for i, c in enumerate(valor[:9]):
        n = int(c) * (2 if i % 2 == 0 else 1)
        suma += n - 9 if n > 9 else n
    verificador = (10 - suma % 10) % 10
    return verificador == int(valor[9])


def _es_ruc(valor: str) -> bool:
    """Valida la ESTRUCTURA del RUC, no su dígito verificador.

    El SRI emite RUCs de sociedades que ya no cumplen el módulo 11, así que exigirlo rechazaría RUCs
    reales (y obliga a usar RUCs calculados en las pruebas). Se comprueba:
    - 13 dígitos numéricos;
    - provincia 01-24 o 30;
    - tercer dígito 0-5 (persona natural), 6 (entidad pública) o 9 (sociedad privada);
    - establecimiento (últimos 3 dígitos) distinto de 000.
    """
    if not (valor.isdigit() and len(valor) == 13):
        return False
    provincia = int(valor[:2])
    if not (1 <= provincia <= 24 or provincia == 30):
        return False
    if valor[2] not in "0123456" + "9":
        return False
    return int(valor[10:]) >= 1


def validar_cedula_ec(valor: str) -> None:
    if not _es_cedula(valor or ""):
        raise ValidationError("Cédula ecuatoriana inválida.", code="cedula_invalida")


def validar_ruc_ec(valor: str) -> None:
    if not _es_ruc(valor or ""):
        raise ValidationError(
            "RUC inválido: deben ser 13 dígitos, empezar con un código de provincia (01-24 o 30) "
            "y terminar en el número de establecimiento (por ejemplo 001).",
            code="ruc_invalido",
        )