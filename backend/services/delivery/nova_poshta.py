from __future__ import annotations
import json, os, urllib.request, urllib.error
from .base import DeliveryAdapter,DeliveryCapability,DeliveryNotConfigured,DeliveryUpstreamError

class NovaPoshtaAdapter(DeliveryAdapter):
    provider='nova_poshta'; label='Нова пошта'
    def __init__(self):
        self.api_key=os.getenv('BB610_NOVA_POSHTA_API_KEY','').strip()
        self.endpoint=os.getenv('BB610_NOVA_POSHTA_API_URL','https://api.novaposhta.ua/v2.0/json/').strip()
        # Shipment creation is deliberately gated separately because it additionally needs
        # sender/contact refs, cargo defaults and a signed-off commercial shipping policy.
        self.sender_ref=os.getenv('BB610_NOVA_POSHTA_SENDER_REF','').strip()
        self.sender_contact_ref=os.getenv('BB610_NOVA_POSHTA_SENDER_CONTACT_REF','').strip()
        self.sender_address_ref=os.getenv('BB610_NOVA_POSHTA_SENDER_ADDRESS_REF','').strip()
    def capability(self):
        live=bool(self.api_key)
        create=live and all((self.sender_ref,self.sender_contact_ref,self.sender_address_ref))
        return DeliveryCapability(self.provider,self.label,live,live,create,live,('branch','locker'))
    def _call(self,model,method,props):
        if not self.api_key: raise DeliveryNotConfigured('Nova Poshta API key is not configured')
        body=json.dumps({'apiKey':self.api_key,'modelName':model,'calledMethod':method,'methodProperties':props},ensure_ascii=False).encode()
        req=urllib.request.Request(self.endpoint,data=body,headers={'Content-Type':'application/json','Accept':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=10) as r: data=json.load(r)
        except (urllib.error.URLError,TimeoutError,json.JSONDecodeError) as e: raise DeliveryUpstreamError(str(e)) from e
        if not data.get('success'):
            raise DeliveryUpstreamError('; '.join(data.get('errors') or ['Nova Poshta API error']))
        return data.get('data') or []
    def search_cities(self,q,limit=20):
        rows=self._call('Address','searchSettlements',{'CityName':q,'Limit':str(limit),'Page':'1'})
        out=[]
        for block in rows:
            for x in block.get('Addresses') or []:
                ref=x.get('DeliveryCity') or x.get('Ref')
                name=x.get('Present') or x.get('MainDescription')
                if ref and name: out.append({'ref':ref,'name':name,'region':x.get('Area') or x.get('Region'),'postal_code':None})
        return out[:limit]
    def search_branches(self,city_ref,q='',limit=30):
        if not city_ref:return []
        props={'SettlementRef':city_ref,'Limit':str(limit),'Page':'1'}
        if q:props['FindByString']=q
        rows=self._call('Address','getWarehouses',props)
        out=[]
        for x in rows:
            desc=x.get('Description') or x.get('ShortAddress')
            ref=x.get('Ref')
            if ref and desc:
                wt=(x.get('CategoryOfWarehouse') or x.get('TypeOfWarehouse') or '').lower()
                service='locker' if ('поштомат' in desc.lower() or 'postomat' in wt) else 'branch'
                out.append({'ref':ref,'name':desc,'number':x.get('Number'),'service':service,'address':x.get('ShortAddress') or desc})
        return out[:limit]
    def create_shipment(self,order):
        # Intentionally not guessed: production InternetDocument.save requires sender refs,
        # cargo/weight/payment/service policy and recipient mapping. Stage 8 exposes the hook
        # but keeps it locked until those commercial parameters are configured and tested.
        if not self.capability().shipment_creation: raise DeliveryNotConfigured('Nova Poshta shipment creation is not fully configured')
        raise DeliveryNotConfigured('Nova Poshta shipment creation awaits Stage 8 production sender/cargo mapping')
    def track(self,tracking_number):
        rows=self._call('TrackingDocument','getStatusDocuments',{'Documents':[{'DocumentNumber':tracking_number,'Phone':''}]})
        if not rows:return {'tracking_number':tracking_number,'status':None,'status_text':'Немає даних'}
        x=rows[0]
        return {'tracking_number':tracking_number,'status':str(x.get('StatusCode') or ''),'status_text':x.get('Status') or '','date':x.get('DateCreated')}
