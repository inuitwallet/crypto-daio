from blocks.views.addresses import AddressDetailView
from blocks.views.blocks import BlockDetailView, LatestBlocksList, All_Blocks
from blocks.views.charts import ChartsView
from blocks.views.notify import Notify
from blocks.views.search import Search
from blocks.views.health import HealthView

__all__ = [
    'AddressDetailView',
    'BlockDetailView',
    'All_Blocks',
    'LatestBlocksList',
    'ChartsView',
    'Notify',
    'Search',
    'HealthView',
]
