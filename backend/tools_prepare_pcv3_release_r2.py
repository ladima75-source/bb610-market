from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from copy import deepcopy
from pathlib import Path

from backend.catalog_provider import load_catalog
from backend.db import DB_PATH, connect
from backend.services import product_cards_v3 as cards
from backend import tools_prepare_pcv3_release as base

MATERIALIZED_PARENTS: set[str] = set()


def _latest_release_backup() -> Path | None:
    paths = sorted(base.BACKUP_ROOT.glob('pcv3-release-prep-*'))
    return paths[-1] if paths else None


def _latest_success_report() -> dict | None:
    paths = sorted(base.REPORT_ROOT.glob('pcv3-release-prep-*.json'))
    for path in reversed(paths):
        try:
            obj = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        apply = obj.get('apply') if isinstance(obj, dict) else None
        if (
            obj.get('mode') == 'APPLY_SAFE'
            and isinstance(apply, dict)
            and apply.get('preexisting_commerce_unchanged') is True
            and apply.get('new_drafts_safe') is True
        ):
            return obj
    return None


def _backup_is_known_success(backup_dir: Path) -> bool:
    report = _latest_success_report()
    apply = report.get('apply') if isinstance(report, dict) else None
    if not isinstance(apply, dict):
        return False
    try:
        return Path(str(apply.get('backup_dir') or '')).resolve() == backup_dir.resolve()
    except Exception:
        return False


def _restore_backup(backup_dir: Path) -> None:
    db_backup = backup_dir / 'bb610-orders.sqlite3'
    cards_backup = backup_dir / 'product_cards_v3'
    if not db_backup.is_file():
        raise RuntimeError(f'backup DB missing: {db_backup}')
    if not cards_backup.is_dir():
        raise RuntimeError(f'backup Product Card v3 directory missing: {cards_backup}')

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(str(db_backup))
    try:
        dst = sqlite3.connect(str(DB_PATH))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    if cards.BASE.exists():
        shutil.rmtree(cards.BASE)
    shutil.copytree(cards_backup, cards.BASE)


def recover_latest_failed() -> bool:
    backup_dir = _latest_release_backup()
    if not backup_dir:
        print('RECOVERY: no release-prep backup found; nothing to restore')
        return False
    if _backup_is_known_success(backup_dir):
        print('RECOVERY: latest backup belongs to a completed safe run; restore skipped')
        return False
    _restore_backup(backup_dir)
    print('RECOVERY BACKUP:', backup_dir)
    print('RECOVERY RESULT: PASS')
    return True


def _static_product(product_id: str) -> dict | None:
    data = load_catalog()
    for row in data.get('products', []) or []:
        if isinstance(row, dict) and str(row.get('id') or '').strip() == product_id:
            return deepcopy(row)
    return None


def _ensure_dynamic_parent(con: sqlite3.Connection, product_id: str) -> bool:
    if con.execute('SELECT 1 FROM product_content WHERE product_id=?', (product_id,)).fetchone():
        return False

    product = _static_product(product_id)
    if not product:
        raise RuntimeError(
            f'{product_id}: dynamic SKU parent is absent from product_content and no static product exists'
        )

    slug = str(product.get('slug') or product_id).strip().lower()
    if not slug:
        raise RuntimeError(f'{product_id}: static product has no slug')
    collision = con.execute(
        'SELECT product_id FROM product_content WHERE slug=? AND product_id<>?',
        (slug, product_id),
    ).fetchone()
    if collision:
        raise RuntimeError(
            f'{product_id}: cannot materialize static parent; slug {slug} is used by {collision[0]}'
        )

    # A static catalog product is public by default when no CMS override exists.
    # Materializing the parent with published=1 preserves that exact state; it does
    # not publish a previously unpublished product. The content snapshot starts
    # from the static product itself so the override does not replace it with a
    # reduced draft representation.
    content = deepcopy(product)
    content['id'] = product_id
    content['slug'] = slug
    now = base._now()
    con.execute(
        'INSERT INTO product_content(product_id,slug,content_json,published,created_at,updated_at) '
        'VALUES(?,?,?,?,?,?)',
        (product_id, slug, json.dumps(content, ensure_ascii=False), 1, now, now),
    )
    MATERIALIZED_PARENTS.add(product_id)
    return True


def _insert_draft_sku_fixed(product_id: str, sku_key: str, package: str) -> None:
    volume_value, volume_unit = base._volume(package)
    now = base._now()
    with connect() as con:
        if con.execute('SELECT 1 FROM dynamic_skus WHERE sku=?', (sku_key,)).fetchone():
            return

        # dynamic_skus.product_id has a real FK to product_content. Existing
        # static catalog products normally do not have a product_content row,
        # which caused R1 to fail with FOREIGN KEY constraint failed. Create a
        # full mirror parent first, preserving the static product's public state.
        _ensure_dynamic_parent(con, product_id)

        con.execute(
            'INSERT INTO dynamic_skus(sku,product_id,variant,volume_value,volume_unit,image,currency,created_at,updated_at) '
            'VALUES(?,?,?,?,?,?,?,?,?)',
            (sku_key, product_id, package or '1 шт', volume_value, volume_unit, None, 'UAH', now, now),
        )
        con.execute(
            'INSERT OR IGNORE INTO sku_commerce(sku,price,sale_price,availability,stock_qty,enabled,updated_at) '
            'VALUES(?,?,?,?,?,?,?)',
            (sku_key, None, None, 'unknown', None, 0, now),
        )
        con.commit()


def _wrap_apply_with_rollback():
    original = base.apply_plan

    def safe_apply(plan: dict) -> dict:
        before = set(base.BACKUP_ROOT.glob('pcv3-release-prep-*'))
        try:
            result = original(plan)
            result['materialized_static_parents'] = len(MATERIALIZED_PARENTS)
            return result
        except Exception:
            after = set(base.BACKUP_ROOT.glob('pcv3-release-prep-*'))
            created = sorted(after - before)
            rollback = created[-1] if created else _latest_release_backup()
            if rollback and rollback.exists():
                _restore_backup(rollback)
                print('AUTO ROLLBACK BACKUP:', rollback)
                print('AUTO ROLLBACK RESULT: PASS')
            else:
                print('AUTO ROLLBACK RESULT: FAILED — backup not found')
            raise

    base.apply_plan = safe_apply


def main() -> None:
    ap = argparse.ArgumentParser(
        description='PCV3 release prep R2: recover failed R1, fix dynamic SKU FK parent handling, and rollback automatically on error.'
    )
    ap.add_argument(
        '--recover-latest-failed',
        action='store_true',
        help='Restore the latest incomplete release-prep backup before applying R2.',
    )
    ap.add_argument('--apply-safe', action='store_true')
    args = ap.parse_args()

    if args.recover_latest_failed:
        recover_latest_failed()

    _wrap_apply_with_rollback()
    base._insert_draft_sku = _insert_draft_sku_fixed

    forwarded = [sys.argv[0]]
    if args.apply_safe:
        forwarded.append('--apply-safe')
    sys.argv = forwarded
    base.main()

    if args.apply_safe:
        print('MATERIALIZED STATIC PARENTS:', len(MATERIALIZED_PARENTS))
        print('PCV3 RELEASE PREP R2: PASS')


if __name__ == '__main__':
    main()
