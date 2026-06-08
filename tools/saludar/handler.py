"""Tool: saludar — saluda a una persona."""


async def run(args: dict, context: dict) -> dict:
    """Ejecuta la herramienta saludar."""
    nombre = args.get("nombre", "Mundo")
    mensaje = f"¡Hola, {nombre}! Bienvenido al sistema."
    return {"mensaje": mensaje}


# Metadatos para el auto-descubrimiento
TOOL_NAME = "saludar"
TOOL_DESCRIPTION = "Saluda a una persona por su nombre. Tool de demostración."
TOOL_SECURITY = "insecure"