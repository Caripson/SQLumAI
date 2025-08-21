# Repository Guidelines

## Project Structure & Module Organization
- Source code lives under `src/` (e.g., `src/proxy`, `src/capture`).
- Database adapters in `connectors/` (e.g., `connectors/mssql/`).
- LLM analysis and heuristics in `agents/` with clear interfaces.
- Tests mirror layout in `tests/` (unit, integration).
- Helper scripts in `scripts/`, configuration in `config/`, examples in `examples/`.

## Build, Test, and Development Commands
- Prefer Makefile shims to standardize workflows:
  - `make setup`: install toolchain and dependencies.
  - `make dev`: run the proxy locally against a test SQL Server.
  - `make test`: run unit/integration tests with coverage.
  - `make fmt` / `make lint`: auto-format and lint.
- Docker usage (when applicable):
  - `docker compose up dev` to start a local stack.
  - Example SQL Server: `docker run -e ACCEPT_EULA=Y -e SA_PASSWORD='Your_strong_Pa55' -p 1433:1433 mcr.microsoft.com/mssql/server:2022-latest`.
  - Docs: `mkdocs serve` to preview `docs/` (if installed); config in `mkdocs.yml`.

## Coding Style & Naming Conventions
- Indentation: 4 spaces; keep lines readable and functions small.
- Naming: `snake_case` for files/functions, `camelCase` for variables, `PascalCase` for types/classes (adjust per language norms).
- Module boundaries: keep proxy, capture, and analysis concerns separate; avoid circular deps.
- Formatters/linters: Python (black, ruff), Go (gofmt), Rust (rustfmt, clippy), TypeScript (prettier, eslint). Run via `make fmt`/`make lint`.

## Testing Guidelines
- Place unit tests in `tests/` using `test_*.py` or `*_test.{go,rs,ts}` patterns.
- Gate integration tests with env like `MSSQL_DSN`; skip if not set.
- Target ≥80% coverage for core proxy/capture logic; exclude external setup code.
- Include fixtures for sample queries and snapshot payloads.
 - Prefer `python3 -m pytest` to avoid interpreter mismatches; `make test` does this automatically.

## Commit & Pull Request Guidelines
- Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- PRs must include: concise summary, rationale, scope of changes, test plan, logs/screenshots, and linked issues.
- Keep PRs small and focused; document any changes to snapshot schema or wire formats.

## Security & Configuration Tips
- Never commit credentials; use `.env` and provide `.env.example`.
- Default to non-blocking proxy behavior; do not send data to external LLMs by default.
- Redact PII in logs and snapshots; document opt-in telemetry and configuration flags.

## Git Hooks (optional)
- Validate rules on commit: `cp scripts/git-hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit`.
- CI also validates rules via `make validate-rules`.
