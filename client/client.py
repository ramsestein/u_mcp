"""
uMCP Client — Cliente CLI para interactuar con el framework.

Uso:
    python client.py saludar --nombre "Juan"
    python client.py consultar_paciente --nhc "NHC_ABCD"
    python client.py enviar_alerta --paciente "PACIENTE_1A2B" --tipo recordatorio --mensaje "Cita médica"
    python client.py list-tools
    python client.py list-resources

Requiere: httpx (instalado con el proyecto)
"""

import httpx
import json
import sys
import os
from pathlib import Path


# Configuración por defecto
GATEWAY_URL = os.getenv("UMCP_URL", "http://localhost:8000")
GATEWAY_KEY = os.getenv("UMCP_GATEWAY_KEY", "dev-gateway-key")
ADMIN_KEY = os.getenv("UMCP_ADMIN_KEY", "dev-admin-key")


def print_response(label: str, data: any):
    """Imprime una respuesta formateada."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print()


async def list_tools():
    """Lista todas las herramientas disponibles."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GATEWAY_URL}/tools",
            headers={"X-Gateway-Key": GATEWAY_KEY},
        )
        if resp.status_code == 401:
            print("❌ Error de autenticación. Revisa UMCP_GATEWAY_KEY")
            return
        resp.raise_for_status()
        data = resp.json()
        print_response("HERRAMIENTAS DISPONIBLES", data)


async def list_resources():
    """Lista todos los resources disponibles."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GATEWAY_URL}/resources")
        resp.raise_for_status()
        print_response("RESOURCES DISPONIBLES", resp.json())


async def call_tool(tool_name: str, args: dict):
    """Ejecuta una herramienta local."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GATEWAY_URL}/tools/{tool_name}",
            headers={"X-Gateway-Key": GATEWAY_KEY},
            json=args,
        )
        if resp.status_code == 401:
            print("❌ Error de autenticación. Revisa UMCP_GATEWAY_KEY")
            return
        resp.raise_for_status()
        data = resp.json()
        print_response(f"RESULTADO: {tool_name}", data)


async def health():
    """Verifica el estado del servidor."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GATEWAY_URL}/health")
        resp.raise_for_status()
        print_response("ESTADO DEL SERVIDOR", resp.json())


async def audit_validate():
    """Valida la cadena de auditoría."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GATEWAY_URL}/audit/chain/validate",
            headers={"X-Audit-Key": os.getenv("UMCP_AUDIT_KEY", "dev-audit-key")},
        )
        resp.raise_for_status()
        print_response("VALIDACIÓN DE AUDITORÍA", resp.json())


async def admin_register_server(name: str, url: str):
    """Registra un servidor MCP remoto."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GATEWAY_URL}/admin/servers/register",
            headers={
                "X-Admin-Key": os.getenv("UMCP_ADMIN_KEY", "dev-admin-key"),
                "Content-Type": "application/json",
            },
            json={"name": name, "url": url},
        )
        if resp.status_code == 401:
            print("❌ Error de autenticación. Revisa UMCP_ADMIN_KEY")
            return
        resp.raise_for_status()
        print_response("SERVIDOR REGISTRADO", resp.json())


def print_help():
    """Muestra ayuda."""
    print(f"""
╔══════════════════════════════════════════════════════╗
║              uMCP CLI Client v0.1.0                 ║
╚══════════════════════════════════════════════════════╝

USO:
    python client.py <comando> [argumentos]

COMANDOS:
    saludar --nombre <texto>
        Saluda a una persona.

    consultar_paciente --nhc <codigo>
        Consulta datos de un paciente por NHC.
        Ej: --nhc NHC_ABCD

    enviar_alerta --paciente <id> --tipo <tipo> --mensaje <texto>
        Envía una alerta anonimizada.
        Tipos: urgencia, recordatorio, resultado

    list-tools
        Lista todas las herramientas disponibles.

    list-resources
        Lista los resources disponibles.

    health
        Verifica el estado del servidor.

    audit
        Valida la cadena de auditoría.

    register-server --name <nombre> --url <url>
        Registra un servidor MCP remoto.

VARIABLES DE ENTORNO:
    UMCP_URL          URL del gateway (defecto: http://localhost:8000)
    UMCP_GATEWAY_KEY  API Key de gateway (defecto: dev-gateway-key)
    UMCP_ADMIN_KEY    API Key de admin   (defecto: dev-admin-key)
    UMCP_AUDIT_KEY    API Key de auditoría (defecto: dev-audit-key)

EJEMPLOS RÁPIDOS:
    python client.py health
    python client.py list-tools
    python client.py list-resources
    python client.py saludar --nombre "Juan"
    python client.py consultar_paciente --nhc "NHC_ABCD"
    python client.py enviar_alerta --paciente "PACIENTE_1A2B" --tipo urgencia --mensaje "Paciente en observación"
""")


if __name__ == "__main__":
    import asyncio

    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print_help()
        sys.exit(0)

    cmd = args[0]

    if cmd == "list-tools":
        asyncio.run(list_tools())
    elif cmd == "list-resources":
        asyncio.run(list_resources())
    elif cmd == "health":
        asyncio.run(health())
    elif cmd == "audit":
        asyncio.run(audit_validate())
    elif cmd == "saludar":
        nombre = None
        for i, a in enumerate(args[1:]):
            if a == "--nombre" and i + 1 < len(args[1:]):
                nombre = args[1:][i + 1]
        if not nombre:
            print("❌ Uso: python client.py saludar --nombre <texto>")
            sys.exit(1)
        asyncio.run(call_tool("saludar", {"nombre": nombre}))
    elif cmd == "consultar_paciente":
        nhc = None
        for i, a in enumerate(args[1:]):
            if a == "--nhc" and i + 1 < len(args[1:]):
                nhc = args[1:][i + 1]
        if not nhc:
            print("❌ Uso: python client.py consultar_paciente --nhc <codigo>")
            sys.exit(1)
        asyncio.run(call_tool("consultar_paciente", {"nhc": nhc}))
    elif cmd == "enviar_alerta":
        params = {}
        for i, a in enumerate(args[1:]):
            if a == "--paciente" and i + 1 < len(args[1:]):
                params["paciente_id"] = args[1:][i + 1]
            elif a == "--tipo" and i + 1 < len(args[1:]):
                params["tipo_alerta"] = args[1:][i + 1]
            elif a == "--mensaje" and i + 1 < len(args[1:]):
                params["mensaje"] = args[1:][i + 1]
        if not params.get("paciente_id") or not params.get("tipo_alerta"):
            print("❌ Uso: python client.py enviar_alerta --paciente <id> --tipo <tipo> --mensaje <texto>")
            sys.exit(1)
        asyncio.run(call_tool("enviar_alerta", params))
    elif cmd == "register-server":
        name, url = None, None
        for i, a in enumerate(args[1:]):
            if a == "--name" and i + 1 < len(args[1:]):
                name = args[1:][i + 1]
            elif a == "--url" and i + 1 < len(args[1:]):
                url = args[1:][i + 1]
        if not name or not url:
            print("❌ Uso: python client.py register-server --name <nombre> --url <url>")
            sys.exit(1)
        asyncio.run(admin_register_server(name, url))
    else:
        print(f"❌ Comando desconocido: {cmd}")
        print("Usa: python client.py --help")
        sys.exit(1)