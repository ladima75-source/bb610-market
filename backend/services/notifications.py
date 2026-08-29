from __future__ import annotations
import json, os, smtplib, urllib.parse, urllib.request
from email.message import EmailMessage
from ..db import connect
from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat()

def _log(order_id, channel, status, error=None):
    with connect() as con:
        con.execute('INSERT INTO notification_log(order_id,channel,status,attempted_at,error) VALUES(?,?,?,?,?)',(order_id,channel,status,now(),error))
        con.commit()

def _text(order):
    return f"Нове замовлення {order['order_number']}\nСтатус: {order['status']}\nКлієнт: {order['customer']['name']}\nТелефон: {order['customer']['phone']}\nСума: {order['total']:.2f} UAH"

def notify_new_order(order):
    order_id=order['order_id']; text=_text(order)
    # Telegram (disabled until both env values are present)
    token=os.getenv('BB610_TELEGRAM_BOT_TOKEN'); chat=os.getenv('BB610_TELEGRAM_CHAT_ID')
    if token and chat:
        try:
            body=urllib.parse.urlencode({'chat_id':chat,'text':text}).encode()
            urllib.request.urlopen(urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',data=body),timeout=8).read()
            _log(order_id,'telegram','sent')
        except Exception as e: _log(order_id,'telegram','failed',str(e)[:500])
    else: _log(order_id,'telegram','disabled')
    # SMTP email (disabled until required env values are present)
    host=os.getenv('BB610_SMTP_HOST'); to=os.getenv('BB610_ORDER_NOTIFY_EMAIL'); sender=os.getenv('BB610_SMTP_FROM')
    if host and to and sender:
        try:
            msg=EmailMessage(); msg['Subject']=f"BB610 Market — {order['order_number']}"; msg['From']=sender; msg['To']=to; msg.set_content(text)
            port=int(os.getenv('BB610_SMTP_PORT','587')); user=os.getenv('BB610_SMTP_USER'); pwd=os.getenv('BB610_SMTP_PASSWORD')
            with smtplib.SMTP(host,port,timeout=10) as s:
                if os.getenv('BB610_SMTP_STARTTLS','1')=='1': s.starttls()
                if user: s.login(user,pwd or '')
                s.send_message(msg)
            _log(order_id,'email','sent')
        except Exception as e: _log(order_id,'email','failed',str(e)[:500])
    else: _log(order_id,'email','disabled')
