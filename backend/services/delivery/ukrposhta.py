from __future__ import annotations
import os
from .base import DeliveryAdapter,DeliveryCapability,DeliveryNotConfigured

class UkrposhtaAdapter(DeliveryAdapter):
    provider='ukrposhta'; label='Укрпошта'
    def __init__(self):
        self.token=os.getenv('BB610_UKRPOSHTA_BEARER_TOKEN','').strip()
        self.base=os.getenv('BB610_UKRPOSHTA_API_URL','https://www.ukrposhta.ua/ecom/0.0.1').strip().rstrip('/')
    def capability(self):
        # Official e-commerce API access is token/contract based. Stage 8 keeps the website
        # contract stable and does not guess private account-specific shipment parameters.
        configured=bool(self.token)
        return DeliveryCapability(self.provider,self.label,configured,False,False,configured,('branch',))
    def search_cities(self,q,limit=20):
        return []
    def search_branches(self,city_ref,q='',limit=30):
        return []
    def create_shipment(self,order):
        raise DeliveryNotConfigured('Ukrposhta shipment creation requires production token/client configuration')
    def track(self,tracking_number):
        raise DeliveryNotConfigured('Ukrposhta tracking adapter is reserved until production token is configured')
