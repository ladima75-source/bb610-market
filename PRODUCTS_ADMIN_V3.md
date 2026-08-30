BB610 MARKET — PRODUCTS ADMIN V3

Що додано:
- повне редагування картки товару;
- додавання нового товару;
- редагування комерційних полів кожного SKU прямо в картці;
- редагування назви фасування та фото для CMS SKU;
- видалення CMS SKU (статичні SKU не видаляються — їх можна вимкнути);
- генератор SKU;
- основне фото + галерея, зміна порядку, вибір головного фото;
- попередній перегляд чернетки через admin/preview.html;
- дублювання товару як чернетки без копіювання SKU;
- Python 3.9 compatibility fix у backend/app.py;
- orders.html/index redirect з V2.1 включені, щоб не було регресії навігації.

DEPLOY:
1. Завантажити PATCH у корінь GitHub.
2. VPS: cd /opt/bb610-market && git pull
3. systemctl restart bb610-market
4. systemctl status bb610-market --no-pager

Нових Python-залежностей у V3 немає. SQLite міграція не потрібна.
