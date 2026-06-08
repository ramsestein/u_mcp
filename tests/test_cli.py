"""Tests para CLI (umcp serve, umcp keys)."""

from click.testing import CliRunner
from umcp.cli.main import cli


class TestCLI:
    def test_cli_help(self):
        """CLI debe mostrar ayuda sin errores."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "uMCP" in result.output

    def test_serve_help(self):
        """Subcomando serve debe mostrar ayuda."""
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0

    def test_keys_help(self):
        """Subcomando keys debe mostrar ayuda."""
        runner = CliRunner()
        result = runner.invoke(cli, ["keys", "--help"])
        assert result.exit_code == 0

    def test_keys_generate_help(self):
        """Subcomando keys generate debe mostrar ayuda."""
        runner = CliRunner()
        result = runner.invoke(cli, ["keys", "generate", "--help"])
        assert result.exit_code == 0

    def test_keys_generate_gateway(self):
        """Generar key de gateway debe mostrar la key."""
        runner = CliRunner()
        result = runner.invoke(cli, ["keys", "generate", "gateway", "--label", "test"])
        assert result.exit_code == 0
        assert "gateway" in result.output
        assert "umcp-gateway-" in result.output

    def test_keys_generate_admin(self):
        """Generar key de admin."""
        runner = CliRunner()
        result = runner.invoke(cli, ["keys", "generate", "admin"])
        assert result.exit_code == 0
        assert "admin" in result.output

    def test_keys_generate_audit(self):
        """Generar key de audit."""
        runner = CliRunner()
        result = runner.invoke(cli, ["keys", "generate", "audit"])
        assert result.exit_code == 0
        assert "audit" in result.output

    def test_keys_revoke_not_found(self):
        """Revocar key inexistente debe mostrar mensaje."""
        runner = CliRunner()
        result = runner.invoke(cli, ["keys", "revoke", "nonexistent"])
        assert result.exit_code == 0
        assert "not found" in result.output