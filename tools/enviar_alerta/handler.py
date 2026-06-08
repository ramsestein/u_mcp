"""Tool: enviar_alerta — envía alertas a servicios externos (todo anonimizado)."""

import uuid


async def run(args: dict, context: dict) -> dict:
    """Ejecuta la herramienta enviar_alerta."""
    paciente_id = args.get("paciente_id", "")
    tipo_alerta = args.get("tipo_alerta", "recordatorio")
    mensaje = args.get("mensaje", "")

    # Simular envío (en producción sería una llamada HTTP/API)
    alerta_id = f"ALT_{uuid.uuid4().hex[:8].upper()}"

    return {
        "status": "enviada",
        "alerta_id": alerta_id,
        "destino": f"servicio_externo/alertas/{tipo_alerta}",
        "paciente": paciente_id,
    }


TOOL_NAME = "enviar_alerta"
TOOL_DESCRIPTION = "Envía una alerta a un servicio externo. Los datos viajan siempre anonimizados."
TOOL_SECURITY = "insecure"