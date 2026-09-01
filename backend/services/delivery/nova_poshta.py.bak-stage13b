from __future__ import annotations
import json, time, urllib.request, urllib.error
from .base import DeliveryAdapter, DeliveryCapability, DeliveryNotConfigured, DeliveryUpstreamError
from ..integration_secrets import get_value

_CACHE: dict[tuple, tuple[float, list[dict]]] = {}

def _cached(key: tuple, ttl: int, loader):
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit and hit[0] > now:
        return hit[1]
    value = loader()
    _CACHE[key] = (now + ttl, value)
    return value

class NovaPoshtaAdapter(DeliveryAdapter):
    provider='nova_poshta'; label='Нова пошта'

    @property
    def api_key(self): return get_value('nova_poshta.api_key','')
    @property
    def endpoint(self): return get_value('nova_poshta.api_url','https://api.novaposhta.ua/v2.0/json/') or 'https://api.novaposhta.ua/v2.0/json/'
    @property
    def sender_ref(self): return get_value('nova_poshta.sender_ref','')
    @property
    def sender_contact_ref(self): return get_value('nova_poshta.sender_contact_ref','')
    @property
    def sender_address_ref(self): return get_value('nova_poshta.sender_address_ref','')

    def capability(self):
        live=bool(self.api_key)
        create=live and all((self.sender_ref,self.sender_contact_ref,self.sender_address_ref))
        return DeliveryCapability(self.provider,self.label,live,live,create,live,('branch','locker'))

    def _call(self,model,method,props):
        if not self.api_key: raise DeliveryNotConfigured('Nova Poshta API key is not configured')
        body=json.dumps({'apiKey':self.api_key,'modelName':model,'calledMethod':method,'methodProperties':props},ensure_ascii=False).encode('utf-8')
        req=urllib.request.Request(self.endpoint,data=body,headers={'Content-Type':'application/json','Accept':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=12) as r: data=json.load(r)
        except (urllib.error.URLError,TimeoutError,json.JSONDecodeError) as e:
            raise DeliveryUpstreamError(str(e)) from e
        if not data.get('success'):
            errors=data.get('errors') or data.get('warnings') or ['Nova Poshta API error']
            raise DeliveryUpstreamError('; '.join(str(x) for x in errors))
        return data.get('data') or []

    def search_cities(self,q,limit=20):
        q=(q or '').strip()
        if len(q)<2:return []
        key=('cities',q.lower(),int(limit))
        def load():
            rows=self._call('Address','searchSettlements',{'CityName':q,'Limit':str(limit),'Page':'1'})
            out=[]
            for block in rows:
                for x in block.get('Addresses') or []:
                    ref=x.get('DeliveryCity') or x.get('Ref')
                    name=x.get('Present') or x.get('MainDescription')
                    if ref and name:
                        out.append({'ref':ref,'name':name,'region':x.get('Area') or x.get('Region'),'postal_code':None})
            return out[:limit]
        return _cached(key,300,load)

    def search_branches(self,city_ref,q='',limit=100):
        city_ref=(city_ref or '').strip(); q=(q or '').strip()
        if not city_ref:return []
        limit=max(1,min(int(limit),100))
        key=('branches',city_ref,q.lower(),limit)
        def load():
            props={'SettlementRef':city_ref,'Limit':str(limit),'Page':'1'}
            if q: props['FindByString']=q
            rows=self._call('Address','getWarehouses',props)
            out=[]
            for x in rows:
                desc=x.get('Description') or x.get('ShortAddress')
                ref=x.get('Ref')
                if ref and desc:
                    wt=(' '.join(str(x.get(k) or '') for k in ('CategoryOfWarehouse','TypeOfWarehouse','Description'))).lower()
                    service='locker' if ('поштомат' in wt or 'postomat' in wt) else 'branch'
                    out.append({'ref':ref,'name':desc,'number':x.get('Number'),'service':service,'address':x.get('ShortAddress') or desc})
            return out[:limit]
        return _cached(key,300,load)

    # Admin-only sender dictionaries. Refs are stored server-side, while the UI shows human labels.
    def sender_counterparties(self):
        rows=self._call('Counterparty','getCounterparties',{'CounterpartyProperty':'Sender','Page':'1'})
        out=[]
        for x in rows:
            ref=x.get('Ref')
            label=x.get('Description') or ' '.join(filter(None,[x.get('LastName'),x.get('FirstName'),x.get('MiddleName')])) or x.get('OwnershipFormDescription')
            if ref: out.append({'ref':ref,'label':label or ref,'city':x.get('CityDescription'),'phone':x.get('Phones')})
        return out

    def sender_contacts(self,sender_ref):
        if not sender_ref:return []
        rows=self._call('Counterparty','getCounterpartyContactPersons',{'Ref':sender_ref,'Page':'1'})
        out=[]
        for x in rows:
            ref=x.get('Ref')
            label=' '.join(filter(None,[x.get('LastName'),x.get('FirstName'),x.get('MiddleName')])) or x.get('Description') or ref
            if ref: out.append({'ref':ref,'label':label,'phone':x.get('Phones') or x.get('Phone')})
        return out

    def sender_addresses(self,sender_ref):
        if not sender_ref:return []
        rows=self._call('Counterparty','getCounterpartyAddresses',{'Ref':sender_ref,'CounterpartyProperty':'Sender'})
        out=[]
        for x in rows:
            ref=x.get('Ref')
            label=x.get('Description') or x.get('Address') or x.get('StreetDescription') or ref
            if ref: out.append({'ref':ref,'label':label,'city_ref':x.get('CityRef'),'city':x.get('CityDescription')})
        return out

    def create_shipment(self,order):
        # Stage 13B makes checkout + sender configuration production-ready.
        # InternetDocument.save stays gated until recipient counterparty creation/mapping is signed off.
        if not self.capability().shipment_creation:
            raise DeliveryNotConfigured('Nova Poshta sender configuration is incomplete')
        raise DeliveryNotConfigured('Nova Poshta TTN creation requires recipient counterparty mapping; scheduled for Stage 13B.2')

    def track(self,tracking_number):
        rows=self._call('TrackingDocument','getStatusDocuments',{'Documents':[{'DocumentNumber':tracking_number,'Phone':''}]})
        if not rows:return {'tracking_number':tracking_number,'status':None,'status_text':'Немає даних'}
        x=rows[0]
        return {'tracking_number':tracking_number,'status':str(x.get('StatusCode') or ''),'status_text':x.get('Status') or '','date':x.get('DateCreated')}
