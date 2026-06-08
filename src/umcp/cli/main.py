"""uMCP CLI — administration command-line interface."""

import click
import uvicorn
from umcp.gateway.config import settings
from umcp.auth.key_manager import key_manager, KeyRole


@click.group()
def cli():
    """uMCP Security Framework CLI."""
    pass


@cli.command()
@click.option("--host", default=None, help="Host to bind to")
@click.option("--port", default=None, type=int, help="Port to bind to")
def serve(host: str = None, port: int = None):
    """Start the uMCP gateway server."""
    host = host or settings.server.host
    port = port or settings.server.port
    click.echo(f"Starting uMCP gateway on {host}:{port}")
    uvicorn.run(
        "umcp.gateway.server:app",
        host=host,
        port=port,
        log_level=settings.server.log_level.lower(),
    )


@cli.group()
def keys():
    """Manage API keys."""
    pass


@keys.command("generate")
@click.argument("role", type=click.Choice(["gateway", "admin", "audit"]))
@click.option("--label", default="", help="Label for the key")
def generate_key(role: str, label: str):
    """Generate a new API key for the given role."""
    key_role = KeyRole(role)
    raw_key, stored = key_manager.generate_key(key_role, label)
    click.echo(f"\n{'=' * 60}")
    click.echo(f"  Role:      {role}")
    click.echo(f"  Label:     {label or '(none)'}")
    click.echo(f"  Key:       {raw_key}")
    click.echo(f"  Hash:      {stored.key_hash[:16]}...")
    click.echo(f"{'=' * 60}")
    click.echo(f"\n  ⚠️  Store this key securely. It cannot be retrieved again.")
    click.echo(f"  You can revoke it with: umcp keys revoke <key>")


@keys.command("revoke")
@click.argument("key")
def revoke_key(key: str):
    """Revoke an API key."""
    success = key_manager.revoke_key(key)
    if success:
        click.echo(f"Key revoked successfully.")
    else:
        click.echo(f"Key not found.")


if __name__ == "__main__":
    cli()