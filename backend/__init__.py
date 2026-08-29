"""BB610 Market backend package bootstrap.

Loads backend/.env for local and simple deployments. Real environment variables keep
priority over values in the file, so production secret managers can override it.
"""
from pathlib import Path
from dotenv import load_dotenv

_ENV_FILE = Path(__file__).resolve().parent / '.env'
load_dotenv(_ENV_FILE, override=False)
