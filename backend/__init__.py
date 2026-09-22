"""BB610 Market backend package bootstrap.

Loads backend/.env for local and simple deployments when python-dotenv is available.
Real environment variables keep priority over values in the file, so production
secret managers can override it. Maintenance scripts must remain runnable in a
minimal Python environment where python-dotenv is not installed.
"""
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # Optional helper; production may use systemd/env vars.
    load_dotenv = None

_ENV_FILE = Path(__file__).resolve().parent / '.env'
if load_dotenv is not None:
    load_dotenv(_ENV_FILE, override=False)

# One-time, idempotent V5 migration. It only extends Plantlogic application
# sections/products/SKUs/media and never rebuilds the persistent V5 database.
try:
    from .services.plantlogic_sections_runtime_migration import apply as _apply_plantlogic_sections_v5
    _apply_plantlogic_sections_v5()
except Exception as exc:  # Fail startup loudly rather than serving a half-migrated catalog.
    raise RuntimeError(f"Plantlogic V5 runtime migration failed: {exc}") from exc
