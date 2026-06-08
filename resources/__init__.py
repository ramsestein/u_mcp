"""Resources — acceso a datos locales (BBDD, ficheros, APIs).

Las herramientas en tools/ pueden consumir estos resources.
Cada resource expone una interfaz simple de consulta.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


RESOURCES_DIR = Path(__file__).parent


class ResourceLoader:
    """Carga y expone resources desde el directorio resources/."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def load_json(self, name: str) -> Optional[List[Dict]]:
        """Carga un archivo JSON de resources/."""
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
        """Lista todos los resources disponibles."""
        return sorted(p.name for p in RESOURCES_DIR.iterdir() if p.is_file() and p.name != "__init__.py")

    def clear_cache(self):
        self._cache.clear()


# Singleton
resource_loader = ResourceLoader()