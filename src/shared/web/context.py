def sitio(request):
    """Contexto mínimo compartido por la navegación HTML."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"sitio": {"usuario": None}}
    return {
        "sitio": {
            "usuario": user,
            "nombre_usuario": f"{user.nombres} {user.apellidos}".strip(),
            "rol": user.rol,
            "institucion_id": user.institucion_id,
        }
    }