from rest_framework.views import exception_handler


def standard_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    details = response.data
    if isinstance(details, dict) and "detail" in details:
        message = str(details["detail"])
        details = {}
    else:
        message = "La solicitud no es válida."

    code = getattr(exc, "default_code", "ERROR").upper()
    response.data = {
        "error": {
            "codigo": code,
            "mensaje": message,
            "detalles": details,
        }
    }
    return response
