"""Tests para tool_dispatcher (secure/insecure dispatch)."""

import pytest
from umcp.pipeline.vault.vault import Vault
from umcp.pipeline.detectors.ensemble import EnsembleDetector
from umcp.pipeline.detectors.regex_detector import RegexDetector
from umcp.layers.tool_dispatcher import ToolDispatcher
from umcp.policies.tool_security import tool_security, ToolSecurityMode
import tempfile
from pathlib import Path


@pytest.fixture
def vault():
    p = Path(tempfile.mktemp(suffix=".db"))
    v = Vault("test-dispatcher", db_path=p)
    yield v
    v.secure_wipe()


@pytest.fixture
def dispatcher(vault):
    detector = EnsembleDetector(regex=RegexDetector())
    return ToolDispatcher(vault=vault, detector=detector)


class TestToolDispatcher:
    @pytest.mark.asyncio
    async def test_insecure_tool_default(self, dispatcher):
        """Tool sin config específica debe ser insecure."""
        result, log = await dispatcher.dispatch("unknown_tool", {"data": "test"})
        assert log["mode"] == "insecure"
        assert "insecure" in result["status"]

    @pytest.mark.asyncio
    async def test_secure_tool_deanonymizes(self, dispatcher, vault):
        """Tool secure debe deanonymizar args."""
        # Crear mapping real
        surr = vault.get_or_create_surrogate("PERSON", "Juan")
        tool_security.add_rule("secure_tool", ToolSecurityMode.SECURE, "needs real")
        result, log = await dispatcher.dispatch("secure_tool", {"name": surr})
        assert log["mode"] == "secure"
        assert len(log["deanonymized_args"]) >= 1

    @pytest.mark.asyncio
    async def test_insecure_tool_no_deanon(self, dispatcher):
        """Tool insecure no debe deanonymizar."""
        result, log = await dispatcher.dispatch("insecure_tool", {"name": "PACIENTE_1234"})
        assert log["mode"] == "insecure"
        assert len(log["deanonymized_args"]) == 0