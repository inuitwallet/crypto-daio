from .addresses import AddressDetailView
from .blocks import BlockDetailView, LatestBlocksList, All_Blocks
from .charts import ChartsView
from .notify import Notify
from .search import Search

__all__ = [
    'AddressDetailView',
    'BlockDetailView',
    'All_Blocks',
    'LatestBlocksList',
    'ChartsView',
    'Notify',
    'Search'
]
