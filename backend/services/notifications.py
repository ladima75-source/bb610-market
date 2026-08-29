from __future__ import annotations
import html, os, smtplib, urllib.parse, urllib.request
from email.message import EmailMessage
from ..db import connect
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def _log(order_id, channel, status, error=None):
    with connect() as con:
        con.execute(
            'INSERT INTO notification_log(order_id,channel,status,attempted_at,error) VALUES(?,?,?,?,?)',
            (order_id, channel, status, now(), error),
        )
        con.commit()


def _money(value, currency='UAH'):
    try:
        amount = f"{float(value):,.2f}".replace(',', ' ').replace('.00', '')
    except (TypeError, ValueError):
        amount = str(value or '—')
    return f"{amount} {currency or 'UAH'}"


def _payment_label(payment):
    payment = payment or {}
    method = payment.get('method') or payment.get('payment_method') or '—'
    status = payment.get('status') or payment.get('payment_status') or '—'
    labels = {
        'cod': 'Післяплата',
        'online_card': 'Онлайн карткою',
        'bank_transfer': 'Переказ на рахунок',
        'pickup_payment': 'Оплата при самовивозі',
    }
    return f"{labels.get(method, method)} · {status}"


def _delivery_label(delivery):
    delivery = delivery or {}
    provider = delivery.get('provider') or delivery.get('method') or '—'
    service = delivery.get('service') or ''
    city = delivery.get('city') or ''
    branch = delivery.get('branch') or delivery.get('address_line') or delivery.get('destination') or ''
    provider_labels = {
        'nova_poshta': 'Нова пошта',
        'ukrposhta': 'Укрпошта',
        'pickup': 'Самовивіз',
        'local_delivery': 'Доставка по Дніпру',
    }
    service_labels = {
        'branch': 'відділення',
        'parcel_locker': 'поштомат',
        'courier': 'кур’єр',
    }
    bits = [provider_labels.get(provider, provider)]
    if service:
        bits.append(service_labels.get(service, service))
    location = ', '.join(x for x in (city, branch) if x)
    if location:
        bits.append(location)
    return ' · '.join(bits)


def _items_lines(order):
    items = order.get('items') or []
    if not items:
        return ['—']
    lines = []
    for item in items:
        name = item.get('name') or item.get('sku') or 'Товар'
        variant = item.get('variant') or ''
        qty = item.get('quantity') or 1
        suffix = f" ({variant})" if variant else ''
        lines.append(f"• {name}{suffix} × {qty}")
    return lines


def _text(order):
    customer = order.get('customer') or {}
    currency = order.get('currency') or 'UAH'
    payment = order.get('payment') or {'method': order.get('payment_method'), 'status': order.get('payment_status')}
    delivery = order.get('delivery') or {'method': order.get('fulfillment_method'), 'destination': order.get('fulfillment_destination')}
    admin_url = os.getenv('BB610_ADMIN_URL') or (os.getenv('BB610_PUBLIC_SITE_URL', 'https://market.bb610.com.ua').rstrip('/') + '/admin/')
    lines = [
        f"Нове замовлення {order.get('order_number','—')}",
        '',
        f"Клієнт: {customer.get('name') or '—'}",
        f"Телефон: {customer.get('phone') or '—'}",
        f"Сума: {_money(order.get('total'), currency)}",
        f"Оплата: {_payment_label(payment)}",
        f"Доставка: {_delivery_label(delivery)}",
        '',
        'Товари:',
        *_items_lines(order),
        '',
        f"Admin: {admin_url}",
    ]
    return '\n'.join(lines)


def _html(order):
    text = _text(order)
    lines = text.splitlines()
    title = html.escape(lines[0] if lines else 'Нове замовлення BB610 MARKET')
    body = '<br>'.join(html.escape(x) for x in lines[1:])
    return (
        '<!doctype html><html><body style="font-family:Arial,sans-serif;color:#1f2328;line-height:1.45">'
        f'<h2 style="margin:0 0 16px">{title}</h2><div>{body}</div>'
        '</body></html>'
    )


def notify_new_order(order):
    order_id = order['order_id']
    text = _text(order)

    # Telegram — enabled only when both backend-only values are configured.
    token = os.getenv('BB610_TELEGRAM_BOT_TOKEN')
    chat = os.getenv('BB610_TELEGRAM_CHAT_ID')
    if token and chat:
        try:
            body = urllib.parse.urlencode({'chat_id': chat, 'text': text, 'disable_web_page_preview': 'true'}).encode()
            req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=body)
            urllib.request.urlopen(req, timeout=8).read()
            _log(order_id, 'telegram', 'sent')
        except Exception as e:
            _log(order_id, 'telegram', 'failed', str(e)[:500])
    else:
        _log(order_id, 'telegram', 'disabled')

    # SMTP email — enabled only when required backend-only values are configured.
    host = os.getenv('BB610_SMTP_HOST')
    to = os.getenv('BB610_ORDER_NOTIFY_EMAIL')
    sender = os.getenv('BB610_SMTP_FROM')
    if host and to and sender:
        try:
            msg = EmailMessage()
            msg['Subject'] = f"BB610 Market — нове замовлення {order.get('order_number','')}"
            msg['From'] = sender
            msg['To'] = to
            msg.set_content(text)
            msg.add_alternative(_html(order), subtype='html')
            port = int(os.getenv('BB610_SMTP_PORT', '587'))
            user = os.getenv('BB610_SMTP_USER')
            pwd = os.getenv('BB610_SMTP_PASSWORD')
            with smtplib.SMTP(host, port, timeout=10) as s:
                if os.getenv('BB610_SMTP_STARTTLS', '1') == '1':
                    s.starttls()
                if user:
                    s.login(user, pwd or '')
                s.send_message(msg)
            _log(order_id, 'email', 'sent')
        except Exception as e:
            _log(order_id, 'email', 'failed', str(e)[:500])
    else:
        _log(order_id, 'email', 'disabled')
