from blocks.views.addresses import AddressDetailView
from blocks.views.blocks import BlockDetailView, LatestBlocksList, AllBlocks
from blocks.views.charts import ChartsView
from blocks.views.notify import Notify
from blocks.views.search import Search
from blocks.views.health import HealthView
from blocks.views.votes import GrantView, MotionView

from blocks.views.explorer_angular import AngularExplorer

__all__ = [
    'AddressDetailView',
    'BlockDetailView',
    'AllBlocks',
    'LatestBlocksList',
    'ChartsView',
    'Notify',
    'Search',
    'HealthView',
    'GrantView',
    'MotionView',

    'AngularExplorer'
]
