"""Remove the local Stage-12 notification test order TEST-001.
Safe to run repeatedly. Does not touch any other order.
"""
from backend.db import connect

ORDER_ID = 'TEST-001'

with connect() as con:
    exists = con.execute('SELECT 1 FROM orders WHERE id=?', (ORDER_ID,)).fetchone()
    if not exists:
        print('TEST-001 not found; nothing to delete')
    else:
        # Child rows use ON DELETE CASCADE where applicable; explicitly remove
        # Stage 8-12 child rows that may not cascade in every local migration state.
        tables = [
            'notification_log', 'delivery_events', 'order_delivery', 'order_payments',
            'payment_events', 'order_status_history', 'order_items', 'idempotency_keys',
        ]
        for table in tables:
            try:
                key = 'order_id'
                con.execute(f'DELETE FROM {table} WHERE {key}=?', (ORDER_ID,))
            except Exception:
                pass
        # Automation rows can reference the aggregate id without a FK.
        for table, col in [('commerce_events','aggregate_id'), ('ai_jobs','aggregate_id'), ('approval_requests','aggregate_id'), ('automation_audit_log','aggregate_id')]:
            try:
                con.execute(f'DELETE FROM {table} WHERE {col}=?', (ORDER_ID,))
            except Exception:
                pass
        con.execute('DELETE FROM orders WHERE id=?', (ORDER_ID,))
        con.commit()
        print('TEST-001 deleted')
