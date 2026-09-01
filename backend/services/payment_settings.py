from __future__ import annotations
import re
from typing import Any
from .integration_secrets import get_value, set_values, source_for


def _bool(v: str | None, default: bool=False) -> bool:
    if v is None or str(v).strip()=="": return default
    return str(v).strip().lower() in ("1","true","yes","on")


def _clean_iban(v: str | None) -> str:
    return re.sub(r"\s+", "", str(v or "")).upper()


def payment_settings_status(online_configured: bool=False, online_provider: str|None=None) -> dict[str,Any]:
    cod=_bool(get_value('payments.cod_enabled','0'))
    bank_enabled=_bool(get_value('payments.bank_transfer_enabled','0'))
    recipient=get_value('payments.bank_recipient','')
    iban=_clean_iban(get_value('payments.bank_iban',''))
    purpose=get_value('payments.bank_purpose','Оплата замовлення {order_number}') or 'Оплата замовлення {order_number}'
    bank_ready=bank_enabled and bool(recipient and iban)
    return {
      'id':'payments','label':'Оплата',
      'cod':{'enabled':cod,'source':source_for('payments.cod_enabled')},
      'bank_transfer':{'enabled':bank_enabled,'ready':bank_ready,'recipient':recipient,'iban':iban,'purpose':purpose,
                       'blocker':None if bank_ready else ('disabled' if not bank_enabled else 'recipient_or_iban_missing')},
      'online_card':{'enabled':bool(online_configured),'provider':online_provider if online_configured else None,'stage':'14B'},
    }


def save_payment_settings(*,cod_enabled=None,bank_transfer_enabled=None,bank_recipient=None,bank_iban=None,bank_purpose=None):
    values={}
    if cod_enabled is not None: values['payments.cod_enabled']='1' if bool(cod_enabled) else '0'
    if bank_transfer_enabled is not None: values['payments.bank_transfer_enabled']='1' if bool(bank_transfer_enabled) else '0'
    if bank_recipient is not None: values['payments.bank_recipient']=str(bank_recipient).strip()
    if bank_iban is not None:
        iban=_clean_iban(bank_iban)
        if iban and (len(iban)<15 or len(iban)>34): raise ValueError('IBAN_FORMAT_INVALID')
        values['payments.bank_iban']=iban
    if bank_purpose is not None: values['payments.bank_purpose']=str(bank_purpose).strip() or 'Оплата замовлення {order_number}'
    if values: set_values(values)
    return payment_settings_status()


def bank_transfer_instructions(order_number: str) -> dict[str,str]:
    recipient=get_value('payments.bank_recipient','')
    iban=_clean_iban(get_value('payments.bank_iban',''))
    purpose=(get_value('payments.bank_purpose','Оплата замовлення {order_number}') or 'Оплата замовлення {order_number}').replace('{order_number}',order_number)
    return {'recipient':recipient,'iban':iban,'purpose':purpose}
