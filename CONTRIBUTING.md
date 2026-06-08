# Contributing to uMCP

Thanks for your interest in contributing to **uMCP — Unified MCP Security Framework**. Contributions of all kinds are welcome: bug reports, fixes, new detectors or tools, documentation, and tests.

## Ways to contribute

- **Report a bug** or **request a feature** by opening an issue. Please include the uMCP version, your OS and Python version, steps to reproduce, and the expected vs. actual behaviour.
- **Improve documentation** — clarifications, examples, and typo fixes are always appreciated.
- **Submit code** via a pull request (see below).

## Security disclosures

uMCP is a security and privacy tool, so please **do not** open public issues for vulnerabilities. Report them privately by email to the maintainer (see `C9` in the README / `CITATION.cff`). We will acknowledge the report and coordinate a fix and disclosure timeline.

## Development setup

```bash
git clone https://github.com/ramsestein/u_mcp.git
cd u_mcp
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

The Spanish clinical BERT models are **not** required for development. The test suite and the framework run without them using the Regex + Aho-Corasick detection stages, so you can contribute without downloading the ~470 MB models.

## Running the tests

All changes must keep the test suite green and should not reduce coverage.

```bash
pytest
pytest --cov=src/umcp --cov-report=term
```

If you add functionality, add tests for it. If you fix a bug, add a regression test that fails before your fix.

## Coding standards

- Target **Python 3.11+**.
- Follow PEP 8; keep functions small and typed (type hints on public functions).
- Keep tools and data resources in their editable files outside the Python source tree — do not hardcode policy or dictionaries into the core.
- Run the formatter/linter configured in `pyproject.toml` before committing.

## Pull request process

1. Fork the repo and create a feature branch (`git checkout -b feature/short-description`).
2. Make your change with tests and, if relevant, documentation updates.
3. Ensure `pytest` passes and coverage is maintained.
4. Open a pull request describing **what** changed and **why**, and link any related issue.
5. Be ready to iterate on review feedback.

## Adding a new tool

uMCP is designed to be extended without touching the core:

1. Create a folder under `tools/` with a `tool.json` (metadata + schema) and a `handler.py` (logic).
2. Restart the server (`umcp serve`). No core code changes are needed.

Please include a minimal test exercising your tool through the dispatcher.

## Do not commit sensitive data

This is critical for a privacy framework:

- **Never** commit real PHI/PII, patient data, or production datasets.
- **Never** commit API keys, credentials, or `.env` files (use `.env.example`).
- Use synthetic or fully de-identified samples in tests and examples.

## License

By contributing, you agree that your contributions will be licensed under the project's **MIT License**.
