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


def _digito_modulo11(digitos: str, coeficientes: list[int]) -> int:
    suma = sum(int(d) * c for d, c in zip(digitos, coeficientes))
    residuo = suma % 11
    return 0 if residuo == 0 else 11 - residuo


def _es_ruc(valor: str) -> bool:
    if not (valor.isdigit() and len(valor) == 13):
        return False
    provincia = int(valor[:2])
    if not (1 <= provincia <= 24 or provincia == 30):
        return False
    tercero = int(valor[2])
    if tercero < 6:  # persona natural: cédula + establecimiento
        return _es_cedula(valor[:10]) and int(valor[10:]) >= 1
    if tercero == 6:  # entidad pública: dígito 9, establecimiento de 4 dígitos
        dv = _digito_modulo11(valor[:8], [3, 2, 7, 6, 5, 4, 3, 2])
        return dv == int(valor[8]) and int(valor[9:]) >= 1
    if tercero == 9:  # sociedad privada: dígito 10, establecimiento de 3 dígitos
        dv = _digito_modulo11(valor[:9], [4, 3, 2, 7, 6, 5, 4, 3, 2])
        return dv == int(valor[9]) and int(valor[10:]) >= 1
    return False


def validar_cedula_ec(valor: str) -> None:
    if not _es_cedula(valor or ""):
        raise ValidationError("Cédula ecuatoriana inválida.", code="cedula_invalida")


def validar_ruc_ec(valor: str) -> None:
    if not _es_ruc(valor or ""):
        raise ValidationError("RUC ecuatoriano inválido.", code="ruc_invalido")