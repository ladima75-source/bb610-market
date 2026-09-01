from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Any
from .integration_secrets import configured, get_value, set_values, source_for

NP_DEFAULT_URL='https://api.novaposhta.ua/v2.0/json/'
def now(): return datetime.now(timezone.utc).isoformat()
def _bool_env(name,default=False): return os.getenv(name,'1' if default else '0').strip().lower() in ('1','true','yes','on')

def nova_poshta_status()->dict[str,Any]:
    api_key_ok=configured('nova_poshta.api_key')
    sender_values={
      'sender_ref':get_value('nova_poshta.sender_ref'),
      'sender_contact_ref':get_value('nova_poshta.sender_contact_ref'),
      'sender_address_ref':get_value('nova_poshta.sender_address_ref'),
    }
    sender={**sender_values,'configured':{k:bool(v) for k,v in sender_values.items()}}
    sender_ready=all(sender['configured'].values())
    cod_ready=api_key_ok and _bool_env('BB610_PAYMENT_COD_ENABLED',False)
    return {
      'id':'nova_poshta','label':'Нова пошта','configured':api_key_ok,
      'api_key':{'configured':api_key_ok,'masked':'••••••••••••' if api_key_ok else '','source':source_for('nova_poshta.api_key')},
      'api_url':get_value('nova_poshta.api_url',NP_DEFAULT_URL) or NP_DEFAULT_URL,
      'sender':sender,
      'api_ready':api_key_ok,
      'checkout_ready':api_key_ok,
      'cod_ready':cod_ready,
      'sender_ready':sender_ready,
      # TTN deliberately stays false until recipient counterparty mapping is implemented.
      'shipment_ready':False,
      'shipment_blocker':None if not sender_ready else 'recipient_mapping',
    }

def save_nova_poshta_settings(*,api_key=None,api_url=None,sender_ref=None,sender_contact_ref=None,sender_address_ref=None):
    values={}
    if api_key is not None: values['nova_poshta.api_key']=api_key
    if api_url is not None: values['nova_poshta.api_url']=api_url or NP_DEFAULT_URL
    if sender_ref is not None: values['nova_poshta.sender_ref']=sender_ref
    if sender_contact_ref is not None: values['nova_poshta.sender_contact_ref']=sender_contact_ref
    if sender_address_ref is not None: values['nova_poshta.sender_address_ref']=sender_address_ref
    if values:set_values(values)
    return nova_poshta_status()

def test_nova_poshta():
    from .delivery.nova_poshta import NovaPoshtaAdapter
    rows=NovaPoshtaAdapter().search_cities('Дніпро',5)
    return {'ok':True,'provider':'nova_poshta','checked_at':now(),'results':len(rows),'sample':[{'name':x.get('name'),'ref_present':bool(x.get('ref'))} for x in rows[:3]]}

def nova_poshta_sender_options(sender_ref: str|None=None):
    from .delivery.nova_poshta import NovaPoshtaAdapter
    a=NovaPoshtaAdapter()
    if not sender_ref:
        return {'senders':a.sender_counterparties()}
    return {'contacts':a.sender_contacts(sender_ref),'addresses':a.sender_addresses(sender_ref)}
