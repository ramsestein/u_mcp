"""Tool: consultar_paciente — consulta datos desde la BBDD de resources."""

import json
from pathlib import Path


# Ruta a la base de datos de pacientes (archivo JSON en resources/)
PACIENTES_DB = Path(__file__).parent.parent.parent / "resources" / "pacientes.json"


async def run(args: dict, context: dict) -> dict:
    """Ejecuta la herramienta consultar_paciente."""
    nhc = args.get("nhc", "")
    if not nhc:
        return {"error": "NHC es requerido"}

    # Cargar BBDD de pacientes
    if PACIENTES_DB.exists():
        with open(PACIENTES_DB, encoding="utf-8") as f:
            pacientes = json.load(f)
    else:
        pacientes = []

    # Buscar por NHC
    for p in pacientes:
        if p.get("nhc") == nhc:
            return {
                "nombre": p.get("nombre", "Desconocido"),
                "edad": p.get("edad", 0),
                "diagnostico": p.get("diagnostico", "Sin diagnóstico"),
            }

    return {"error": f"Paciente con NHC {nhc} no encontrado"}


TOOL_NAME = "consultar_paciente"
TOOL_DESCRIPTION = "Consulta los datos de un paciente por su NHC usando la base de datos local."
TOOL_SECURITY = "secure"