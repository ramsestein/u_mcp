"""Tests para resource_pipeline."""

import pytest
from umcp.pipeline.vault.vault import Vault
from umcp.pipeline.detectors.ensemble import EnsembleDetector
from umcp.pipeline.detectors.regex_detector import RegexDetector
from umcp.layers.resource_pipeline import ResourcePipeline
import tempfile
from pathlib import Path


@pytest.fixture
def vault():
    p = Path(tempfile.mktemp(suffix=".db"))
    v = Vault("test-resource", db_path=p)
    yield v
    v.secure_wipe()


@pytest.fixture
def pipeline(vault):
    detector = EnsembleDetector(regex=RegexDetector())
    return ResourcePipeline(vault=vault, detector=detector)


class TestResourcePipeline:
    @pytest.mark.asyncio
    async def test_process_clean_resource(self, pipeline):
        """Resource sin PII debe pasar sin cambios."""
        data = "El paciente está estable"
        result, log = await pipeline.process_resource("test1", data)
        assert "paciente" in result
        assert log["entity_count"] == 0

    @pytest.mark.asyncio
    async def test_process_pii_resource(self, pipeline):
        """Resource con email debe anonimizarlo."""
        data = "Contacto: juan@example.com"
        result, log = await pipeline.process_resource("test2", data)
        assert "juan@example.com" not in result
        assert log["entity_count"] >= 1

    @pytest.mark.asyncio
    async def test_cache_same_resource(self, pipeline):
        """Mismo resource debe cachearse."""
        data = "test data"
        r1, log1 = await pipeline.process_resource("cache_test", data)
        r2, log2 = await pipeline.process_resource("cache_test", data)
        assert log2.get("cached") is True

    @pytest.mark.asyncio
    async def test_process_with_dates(self, pipeline):
        """Fechas deben preservarse."""
        data = "Fecha: 12.05.2024"
        result, log = await pipeline.process_resource("dates", data)
        assert "12.05.2024" in result

    def test_clear_cache(self, pipeline):
        """Limpiar caché no debe fallar."""
        pipeline.clear_cache()
        assert pipeline._cache == {}