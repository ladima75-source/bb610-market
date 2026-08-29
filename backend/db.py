from __future__ import annotations
import os, sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv('BB610_DB_PATH', str(BASE_DIR / 'runtime' / 'bb610-orders.sqlite3')))
MIGRATIONS = BASE_DIR / 'migrations'

def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys = ON')
    con.execute('PRAGMA journal_mode = WAL')
    return con

def migrate() -> None:
    with connect() as con:
        for sql_file in sorted(MIGRATIONS.glob('*.sql')):
            con.executescript(sql_file.read_text(encoding='utf-8'))
        con.commit()
