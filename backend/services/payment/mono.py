from __future__ import annotations
import base64, hashlib, json, os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature
from .base import PaymentAdapter, PaymentSession, PaymentWebhookEvent, PaymentNotConfigured, PaymentSignatureError
from ..integration_secrets import get_value

API='https://api.monobank.ua'
_STATUS={'success':'paid','failure':'failed','reversed':'refunded','processing':'requires_action','created':'requires_action','hold':'requires_action'}

class MonoPaymentAdapter(PaymentAdapter):
    provider='mono'
    def __init__(self):
        self.token=get_value('payments.mono_token','')
        self._pubkey=None
    def configured(self)->bool:
        return bool(self.token)
    def _json(self,method,path,payload=None):
        if not self.token: raise PaymentNotConfigured('mono acquiring token is not configured')
        data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
        req=Request(API+path,data=data,method=method,headers={'X-Token':self.token,'Content-Type':'application/json','Accept':'application/json','X-Cms':'BB610 Market'})
        try:
            with urlopen(req,timeout=15) as r: return json.loads(r.read().decode() or '{}')
        except HTTPError as e:
            try: detail=e.read().decode()
            except Exception: detail=''
            raise PaymentNotConfigured('mono API error '+str(e.code)+((': '+detail[:240]) if detail else '')) from e
        except URLError as e: raise PaymentNotConfigured('mono API unavailable') from e
    def test(self):
        d=self._json('GET','/api/merchant/pubkey')
        return {'ok':bool(d.get('key'))}
    def create_session(self,*,order_id,order_number,amount,currency,return_url,customer):
        if currency!='UAH': raise ValueError('MONO_UNSUPPORTED_CURRENCY')
        webhook=os.getenv('BB610_PUBLIC_API_URL','https://api.market.bb610.com.ua').rstrip('/')+'/api/v1/payments/webhooks/mono'
        payload={'amount':int(round(float(amount)*100)),'ccy':980,'redirectUrl':return_url,'webHookUrl':webhook,
                 'merchantPaymInfo':{'reference':order_number,'destination':'Оплата замовлення '+order_number}}
        d=self._json('POST','/api/merchant/invoice/create',payload)
        invoice=d.get('invoiceId'); page=d.get('pageUrl')
        if not invoice or not page: raise PaymentNotConfigured('mono did not return invoiceId/pageUrl')
        return PaymentSession(provider='mono',provider_payment_id=invoice,redirect_url=page,status='requires_action',raw={'invoiceId':invoice})
    def _public_key(self,refresh=False):
        if self._pubkey is None or refresh:
            d=self._json('GET','/api/merchant/pubkey'); raw=base64.b64decode(d.get('key',''))
            self._pubkey=serialization.load_pem_public_key(raw)
        return self._pubkey
    def _verify(self,signature,body):
        try: sig=base64.b64decode(signature,validate=True)
        except Exception: return False
        for refresh in (False,True):
            try:
                self._public_key(refresh).verify(sig,body,ec.ECDSA(hashes.SHA256())); return True
            except InvalidSignature: continue
            except Exception: continue
        return False
    def parse_webhook(self,headers,body):
        sign=headers.get('x-sign','')
        if not sign or not self._verify(sign,body): raise PaymentSignatureError('Invalid mono webhook signature')
        try: d=json.loads(body.decode())
        except Exception as e: raise ValueError('INVALID_MONO_WEBHOOK_JSON') from e
        invoice=str(d.get('invoiceId') or '')
        status=str(d.get('status') or '')
        mapped=_STATUS.get(status)
        if not invoice or not mapped: raise ValueError('UNSUPPORTED_MONO_WEBHOOK_STATUS')
        event_id='mono:'+invoice+':'+status+':'+str(d.get('modifiedDate') or d.get('createdDate') or '')
        return PaymentWebhookEvent(provider_event_id=event_id,provider_payment_id=invoice,order_id=None,status=mapped,event_type='mono.invoice.'+status,raw=d)
