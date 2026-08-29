from .nova_poshta import NovaPoshtaAdapter
from .ukrposhta import UkrposhtaAdapter
from .base import DeliveryError,DeliveryNotConfigured,DeliveryUpstreamError

_ADAPTERS={'nova_poshta':NovaPoshtaAdapter(),'ukrposhta':UkrposhtaAdapter()}
def adapter(provider): return _ADAPTERS.get(provider)
def capabilities(): return [a.capability().__dict__ for a in _ADAPTERS.values()]
