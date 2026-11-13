from shared.tenancy.context import fijar_institucion, restaurar_institucion


class TenancyMiddleware:
    """Fija la institución del usuario autenticado para toda la petición.

    - Usuario con institución  -> solo ve datos de esa institución.
    - Anónimo o Administrador del Sistema (sin institución) -> no ve datos de negocio.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        institucion_id = getattr(user, "institucion_id", None) if user and user.is_authenticated else None
        token = fijar_institucion(institucion_id)
        try:
            return self.get_response(request)
        finally:
            restaurar_institucion(token)