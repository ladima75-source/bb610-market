from __future__ import annotations
import json, time, urllib.request, urllib.error, re
from datetime import datetime
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

def _phone(v) -> str:
    if isinstance(v,(list,tuple)):
        v=v[0] if v else ''
    d = re.sub(r'\D+', '', str(v or ''))
    if d.startswith('0') and len(d) == 10:
        d = '38' + d
    if len(d) == 12 and d.startswith('380'):
        return d
    return d

def _split_name(v: str | None):
    p = [x for x in re.split(r'\s+', (v or '').strip()) if x]
    if not p:
        return ('Покупець', '', 'BB610')
    if len(p) == 1:
        return (p[0], '', p[0])
    if len(p) == 2:
        return (p[1], '', p[0])
    return (p[1], ' '.join(p[2:]), p[0])

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
    @property
    def shipment_weight(self):
        try: return max(0.1, float(get_value('nova_poshta.shipment_weight','1.0') or 1.0))
        except Exception: return 1.0
    @property
    def shipment_description(self): return get_value('nova_poshta.shipment_description','Товари для вирощування') or 'Товари для вирощування'
    @property
    def payer_type(self): return get_value('nova_poshta.payer_type','Recipient') or 'Recipient'
    @property
    def payment_method(self): return get_value('nova_poshta.payment_method','Cash') or 'Cash'

    def capability(self):
        live=bool(self.api_key)
        create=live and all((self.sender_ref,self.sender_contact_ref,self.sender_address_ref))
        return DeliveryCapability(self.provider,self.label,live,live,create,live,('branch','locker'))

    def _call(self,model,method,props):
        if not self.api_key: raise DeliveryNotConfigured('Nova Poshta API key is not configured')
        body=json.dumps({'apiKey':self.api_key,'modelName':model,'calledMethod':method,'methodProperties':props},ensure_ascii=False).encode('utf-8')
        req=urllib.request.Request(self.endpoint,data=body,headers={'Content-Type':'application/json','Accept':'application/json'},method='POST')
        try:
            with urllib.request.urlopen(req,timeout=15) as r: data=json.load(r)
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
            props={'CityRef':city_ref,'Limit':str(limit),'Page':'1'}
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

    def sender_counterparties(self):
        rows=self._call('Counterparty','getCounterparties',{'CounterpartyProperty':'Sender','Page':'1'})
        out=[]
        for x in rows:
            ref=x.get('Ref')
            label=x.get('Description') or ' '.join(filter(None,[x.get('LastName'),x.get('FirstName'),x.get('MiddleName')])) or x.get('OwnershipFormDescription')
            if ref: out.append({'ref':ref,'label':label or ref,'city':x.get('CityDescription'),'city_ref':x.get('City') or x.get('CityRef'),'phone':x.get('Phones')})
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

    def _sender_record(self,sender_ref):
        if not sender_ref:return None
        return next((x for x in self.sender_counterparties() if x.get('ref')==sender_ref),None)

    def sender_warehouses(self,sender_ref,limit=100):
        """Return Nova Poshta branch dispatch points for the sender city.

        A business sender may have no rows in Counterparty.getCounterpartyAddresses
        when shipments are handed over at a Nova Poshta branch. For the
        WarehouseWarehouse service SenderAddress must therefore be selected from
        Address.getWarehouses for the sender's city.
        """
        sender=self._sender_record(sender_ref)
        if not sender:return []
        city_ref=(sender.get('city_ref') or '').strip()
        if not city_ref and (sender.get('city') or '').strip():
            cities=self.search_cities(sender.get('city'),10)
            if cities: city_ref=(cities[0].get('ref') or '').strip()
        if not city_ref:return []
        rows=self.search_branches(city_ref,'',limit)
        out=[]
        for x in rows:
            # Dispatch from a branch. Parcel lockers are recipient points and are
            # intentionally not offered as sender dispatch points here.
            if x.get('service')!='branch':
                continue
            ref=x.get('ref')
            if not ref: continue
            number=x.get('number')
            label=x.get('name') or x.get('address') or ref
            if number and str(number) not in str(label):
                label=f'Відділення №{number} · {label}'
            out.append({'ref':ref,'label':label,'city_ref':city_ref,'city':sender.get('city'),'number':number,'address':x.get('address'),'source':'warehouse'})
        return out

    # Compatibility name used by older integration code. From Stage 15A.3 a
    # sender "address" means the Nova Poshta warehouse/branch dispatch point.
    def sender_addresses(self,sender_ref):
        return self.sender_warehouses(sender_ref)

    def _selected_sender(self):
        contacts=self.sender_contacts(self.sender_ref)
        warehouses=self.sender_warehouses(self.sender_ref)
        contact=next((x for x in contacts if x.get('ref')==self.sender_contact_ref),None)
        address=next((x for x in warehouses if x.get('ref')==self.sender_address_ref),None)
        sender=self._sender_record(self.sender_ref)
        if not contact or not address or not sender:
            raise DeliveryNotConfigured('Nova Poshta sender contact/dispatch branch is no longer available')
        phone=_phone(contact.get('phone'))
        city_ref=(sender.get('city_ref') or address.get('city_ref') or '').strip()
        if not phone or not city_ref:
            raise DeliveryNotConfigured('Nova Poshta sender phone/city is incomplete')
        return contact,address,phone,city_ref

    def _recipient(self, order):
        customer=order.get('customer') or {}
        delivery=order.get('delivery') or {}
        phone=_phone(customer.get('phone') or order.get('customer_phone') or delivery.get('recipient_phone'))
        name=customer.get('name') or order.get('customer_name') or delivery.get('recipient_name')
        city_ref=delivery.get('city_ref')
        if not phone or not city_ref:
            raise ValueError('RECIPIENT_PHONE_OR_CITY_REF_MISSING')
        first,middle,last=_split_name(name)
        rows=self._call('Counterparty','save',{
            'CounterpartyProperty':'Recipient','CityRef':city_ref,'CounterpartyType':'PrivatePerson',
            'FirstName':first,'MiddleName':middle,'LastName':last,'Phone':phone,
        })
        if not rows or not rows[0].get('Ref'):
            raise DeliveryUpstreamError('Nova Poshta did not return recipient Ref')
        recipient_ref=rows[0]['Ref']
        contacts=self._call('Counterparty','getCounterpartyContactPersons',{'Ref':recipient_ref,'Page':'1'})
        contact_ref=None
        for x in contacts:
            if _phone(x.get('Phones') or x.get('Phone'))==phone:
                contact_ref=x.get('Ref'); break
        if not contact_ref and contacts:
            contact_ref=contacts[0].get('Ref')
        if not contact_ref:
            raise DeliveryUpstreamError('Nova Poshta did not return recipient contact Ref')
        return recipient_ref,contact_ref,phone


    def validate_shipment(self,order):
        """Read-only readiness check. Does not create Recipient and does not call InternetDocument.save."""
        if not self.capability().shipment_creation:
            raise DeliveryNotConfigured('Nova Poshta sender configuration is incomplete')
        delivery=order.get('delivery') or {}
        if not delivery.get('city_ref') or not delivery.get('branch_ref'):
            raise ValueError('RECIPIENT_CITY_OR_BRANCH_REF_MISSING')
        if delivery.get('service') not in ('branch','locker'):
            raise ValueError('UNSUPPORTED_NOVA_POSHTA_SERVICE')
        contact,address,sender_phone,city_sender=self._selected_sender()
        customer=order.get('customer') or {}
        recipient_phone=_phone(customer.get('phone') or order.get('customer_phone') or delivery.get('recipient_phone'))
        recipient_name=customer.get('name') or order.get('customer_name') or delivery.get('recipient_name')
        if not recipient_phone or len(recipient_phone)!=12 or not recipient_phone.startswith('380'):
            raise ValueError('RECIPIENT_PHONE_INVALID')
        if not (recipient_name or '').strip():
            raise ValueError('RECIPIENT_NAME_MISSING')
        wh=self._call('Address','getWarehouses',{'Ref':delivery['branch_ref'],'Page':'1','Limit':'1'})
        if not wh:
            raise ValueError('RECIPIENT_BRANCH_REF_NOT_FOUND')
        amount=max(1.0,float(order.get('total') or 0))
        payment_method=(order.get('payment') or {}).get('method') or order.get('payment_method')
        return {
          'ok':True,'read_only':True,'creates_ttn':False,'creates_recipient':False,
          'sender':{'contact':contact.get('label'),'address':address.get('label'),'phone':sender_phone,'city_ref_present':bool(city_sender)},
          'recipient':{'name':recipient_name,'phone':recipient_phone,'city':delivery.get('city'),'branch':delivery.get('branch'),'branch_ref_valid':True,'service':delivery.get('service')},
          'shipment':{'weight':self.shipment_weight,'description':self.shipment_description,'payer_type':self.payer_type,'payment_method':self.payment_method,'declared_cost':round(amount,2),'afterpayment':round(amount,2) if payment_method=='cod' else None,'service_type':'WarehouseWarehouse'},
          'note':'Перевірка виконана без створення отримувача та без InternetDocument.save.'
        }

    def create_shipment(self,order):
        if not self.capability().shipment_creation:
            raise DeliveryNotConfigured('Nova Poshta sender configuration is incomplete')
        delivery=order.get('delivery') or {}
        if not delivery.get('city_ref') or not delivery.get('branch_ref'):
            raise ValueError('RECIPIENT_CITY_OR_BRANCH_REF_MISSING')
        if delivery.get('service') not in ('branch','locker'):
            raise ValueError('UNSUPPORTED_NOVA_POSHTA_SERVICE')
        _,_,sender_phone,city_sender=self._selected_sender()
        recipient_ref,recipient_contact_ref,recipient_phone=self._recipient(order)
        amount=max(1.0,float(order.get('total') or 0))
        payment_method=(order.get('payment') or {}).get('method') or order.get('payment_method')
        props={
            'PayerType':self.payer_type,
            'PaymentMethod':self.payment_method,
            'DateTime':datetime.now().strftime('%d.%m.%Y'),
            'CargoType':'Parcel','Weight':str(self.shipment_weight),'ServiceType':'WarehouseWarehouse',
            'SeatsAmount':'1','Description':self.shipment_description,'Cost':str(round(amount,2)),
            'CitySender':city_sender,'Sender':self.sender_ref,'SenderAddress':self.sender_address_ref,
            'ContactSender':self.sender_contact_ref,'SendersPhone':sender_phone,
            'CityRecipient':delivery['city_ref'],'Recipient':recipient_ref,'RecipientAddress':delivery['branch_ref'],
            'ContactRecipient':recipient_contact_ref,'RecipientsPhone':recipient_phone,
        }
        if payment_method=='cod':
            props['AfterpaymentOnGoodsCost']=str(round(amount,2))
        rows=self._call('InternetDocument','save',props)
        if not rows:
            raise DeliveryUpstreamError('Nova Poshta did not return shipment data')
        x=rows[0]
        number=x.get('IntDocNumber') or x.get('IntDocNumberNew') or x.get('Number')
        ref=x.get('Ref')
        if not number:
            raise DeliveryUpstreamError('Nova Poshta did not return TTN number')
        return {
            'tracking_number':number,'shipment_ref':ref,'status':'created','status_text':'ТТН створено',
            'estimated_delivery_date':x.get('EstimatedDeliveryDate'),'cost_on_site':x.get('CostOnSite'),
            'raw':x,
        }

    def track(self,tracking_number):
        rows=self._call('TrackingDocument','getStatusDocuments',{'Documents':[{'DocumentNumber':tracking_number,'Phone':''}]})
        if not rows:return {'tracking_number':tracking_number,'status':None,'status_text':'Немає даних'}
        x=rows[0]
        return {'tracking_number':tracking_number,'status':str(x.get('StatusCode') or ''),'status_text':x.get('Status') or '','date':x.get('DateCreated')}
