from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler


class PaginacionEnvuelta(PageNumberPagination):
    """Paginación que responde con el mismo sobre {"datos": ..., "mensaje": ...} del resto de la API."""

    page_size = 20
    page_size_query_param = "tamano"
    max_page_size = 100
    mensaje = "Listado obtenido."

    def get_paginated_response(self, data):
        return Response(
            {
                "datos": {
                    "total": self.page.paginator.count,
                    "siguiente": self.get_next_link(),
                    "anterior": self.get_previous_link(),
                    "resultados": data,
                },
                "mensaje": self.mensaje,
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "datos": {
                    "type": "object",
                    "properties": {
                        "total": {"type": "integer"},
                        "siguiente": {"type": "string", "nullable": True},
                        "anterior": {"type": "string", "nullable": True},
                        "resultados": schema,
                    },
                },
                "mensaje": {"type": "string"},
            },
        }


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
