from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from backend import tools_migrate_pcv3_all_remaining as migrate_all
from backend import tools_verify_pcv3_all_catalog as verify_all
from backend.services import product_cards_v3 as svc

ROOT = Path(__file__).resolve().parents[1]
BACKUPS = ROOT / 'var' / 'pcv3-backups'


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')


def _backup() -> Path:
    src = svc.BASE
    dst = BACKUPS / f'before-complete-catalog-{_stamp()}'
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.copytree(src, dst)
    else:
        dst.mkdir(parents=True, exist_ok=True)
    return dst


def main() -> None:
    backup = _backup()
    print(f'PCV3 BACKUP: {backup}')
    try:
        migrate_all.main()
        verify_all.main()
    except BaseException:
        print('PCV3 COMPLETE CATALOG FAILED.')
        print(f'Backup preserved at: {backup}')
        raise
    print('PCV3 COMPLETE CATALOG: PASS')
    print('All real catalog products are now covered by Product Card v3.')
    print('Prices, stock, availability, publication and orders were not written by the migration.')


if __name__ == '__main__':
    main()
