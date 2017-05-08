from channels import route
from blocks.consumers.block import parse_block, repair_block
from blocks.consumers.transaction import repair_transaction
from blocks.consumers.address import parse_address
from blocks.consumers.websockets import ws_connect

channel_routing = [
    # Blocks
    route('parse_block', parse_block),
    route('repair_block', repair_block),

    # Transactions
    route('repair_transaction', repair_transaction),

    # Addresses
    route('parse_address', parse_address),

    # Websockets
    route('websocket.connect', ws_connect)
]
