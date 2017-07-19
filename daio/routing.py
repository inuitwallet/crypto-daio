from channels import route
from blocks.consumers.block import parse_block, repair_block, check_block_hash
from blocks.consumers.transaction import repair_transaction
from blocks.consumers.address import parse_address
from blocks.consumers.info import display_info
from blocks.consumers.websockets import ws_connect, ws_disconnect, ws_receive

channel_routing = [
    # Blocks
    route('parse_block', parse_block),
    route('repair_block', repair_block),
    route('check_block_hash', check_block_hash),

    # Transactions
    route('repair_transaction', repair_transaction),

    # Addresses
    route('parse_address', parse_address),

    # Info
    route('display_info', display_info),

    # Websockets
    route('websocket.connect', ws_connect),
    route('websocket.disconnect', ws_disconnect),
    route('websocket.receive', ws_receive),
]
