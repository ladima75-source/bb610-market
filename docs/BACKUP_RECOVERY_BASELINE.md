# Orders DB — backup/recovery baseline

До live запуска резервное копирование является обязательным operational blocker.

Минимальная схема для текущего SQLite Orders Core:

1. DB хранится на backend storage, не в GitHub Pages.
2. Делается автоматическая копия минимум ежедневно; при значимом объёме — чаще.
3. Backup хранится отдельно от основного backend instance.
4. Retention: несколько последних daily + weekly copies.
5. Перед копированием использовать SQLite-safe backup mechanism / DB snapshot, а не случайное копирование активного файла без проверки.
6. Backup считается рабочим только после restore test на отдельной DB.
7. После восстановления проверяются минимум:
   - order count;
   - order_items;
   - order_status_history;
   - order_delivery;
   - order_payments;
   - payment_events;
   - notification log.

Конкретный storage/provider определяется после выбора production backend hosting.
