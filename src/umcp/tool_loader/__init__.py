"""Tool Loader — auto-descubre herramientas en tools/ y resources/ en resources/.

Sistema plug-and-play: cada carpeta dentro de tools/ con tool.json + handler.py
es automáticamente detectada y registrada como herramienta MCP.
"""

import importlib
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Ruta base del proyecto (raíz de mcp_proyect)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
TOOLS_DIR = PROJECT_ROOT / "tools"
RESOURCES_DIR = PROJECT_ROOT / "resources"


# ── Resource Loader ───────────────────────────────────────────────────────


class ResourceLoader:
    """Carga y expone resources desde resources/."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def load_json(self, name: str) -> Optional[List[Dict]]:
        path = RESOURCES_DIR / name
        if not path.exists():
            path = RESOURCES_DIR / f"{name}.json"
        if not path.exists():
            return None
        if str(path) not in self._cache:
            with open(path, encoding="utf-8") as f:
                self._cache[str(path)] = json.load(f)
        return self._cache[str(path)]

    def list_resources(self) -> List[str]:
        if not RESOURCES_DIR.exists():
            return []
        return sorted(p.name for p in RESOURCES_DIR.iterdir()
                      if p.is_file() and p.name.endswith(".json"))

    def clear_cache(self):
        self._cache.clear()


resource_loader = ResourceLoader()


# ── Tool Registry ─────────────────────────────────────────────────────────


@dataclass
class ToolDefinition:
    """Definición completa de una herramienta cargada dinámicamente."""
    name: str
    description: str
    security: str  # "secure" o "insecure"
    handler: Callable
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    version: str = "1.0.0"
    examples: list = field(default_factory=list)
    tool_dir: Path = field(default_factory=Path)


class ToolRegistry:
    """Registro central de herramientas descubiertas automáticamente."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def discover_tools(self) -> int:
        """Escanea tools/ y registra todas las herramientas encontradas.

        Returns: número de herramientas cargadas.
        """
        if not TOOLS_DIR.exists():
            logger.warning(f"Directorio tools/ no encontrado en {TOOLS_DIR}")
            return 0

        count = 0
        for tool_dir in sorted(TOOLS_DIR.iterdir()):
            if not tool_dir.is_dir():
                continue
            try:
                self._load_tool(tool_dir)
                count += 1
                logger.info(f"Tool cargada: {tool_dir.name}")
            except Exception as e:
                logger.error(f"Error cargando tool {tool_dir.name}: {e}")

        logger.info(f"Total herramientas cargadas: {count}")
        return count

    def _load_tool(self, tool_dir: Path) -> None:
        """Carga una herramienta desde su directorio."""
        json_path = tool_dir / "tool.json"
        handler_path = tool_dir / "handler.py"

        if not json_path.exists():
            raise FileNotFoundError(f"Falta tool.json en {tool_dir}")
        if not handler_path.exists():
            raise FileNotFoundError(f"Falta handler.py en {tool_dir}")

        # Cargar metadata del JSON
        with open(json_path, encoding="utf-8") as f:
            meta = json.load(f)

        # Cargar handler dinámicamente
        spec = importlib.util.spec_from_file_location(
            f"tool_{tool_dir.name}", str(handler_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Validar que el handler tenga los atributos requeridos
        if not hasattr(module, "run"):
            raise AttributeError(f"handler.py en {tool_dir.name} debe tener función 'run'")

        # Crear definición
        definition = ToolDefinition(
            name=meta.get("name", tool_dir.name),
            description=meta.get("description", ""),
            security=meta.get("security", getattr(module, "TOOL_SECURITY", "insecure")),
            handler=module.run,
            input_schema=meta.get("input_schema", {}),
            output_schema=meta.get("output_schema", {}),
            version=meta.get("version", "1.0.0"),
            examples=meta.get("examples", []),
            tool_dir=tool_dir,
        )

        self._tools[definition.name] = definition

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "security": t.security,
                "input_schema": t.input_schema,
                "output_schema": t.output_schema,
                "version": t.version,
            }
            for t in self._tools.values()
        ]

    def get_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    async def call_tool(self, name: str, args: dict, context: dict = None) -> Any:
        """Ejecuta una herramienta por su nombre."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' no encontrada")
        if context is None:
            context = {}
        return await tool.handler(args, context)

    @property
    def count(self) -> int:
        return len(self._tools)


# Singleton
tool_registry = ToolRegistry()