from channels.generic.websockets import WebsocketDemultiplexer
from blocks.consumers.angular_consumers.block import (
    LatestBlocksConsumer,
    MoreBlocksConsumer,
    BlockConsumer,
    TransactionConsumer
)


class LatestBlocksDemultiplexer(WebsocketDemultiplexer):
    consumers = {
        'latest_blocks': LatestBlocksConsumer,
        'more_blocks': MoreBlocksConsumer
    }


class BlockDemultiplexer(WebsocketDemultiplexer):
    consumers = {
        'block': BlockConsumer,
        'transactions': TransactionConsumer,
    }

