from blocks.views.addresses import AddressDetailView
from blocks.views.blocks import AllBlocks, BlockDetailView, LatestBlocksList
from blocks.views.health import HealthView
from blocks.views.notify import Notify
from blocks.views.search import Search
from blocks.views.votes import GrantView, MotionView

__all__ = [
    "AddressDetailView",
    "BlockDetailView",
    "AllBlocks",
    "LatestBlocksList",
    "Notify",
    "Search",
    "HealthView",
    "GrantView",
    "MotionView",
]
