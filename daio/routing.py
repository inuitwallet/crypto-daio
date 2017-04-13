from channels import route
from blocks.consumers.parse_block import parse_block
from blocks.consumers.parse_transaction import parse_transaction

channel_routing = [
    route('parse_block', parse_block),
    route('parse_transaction', parse_transaction),
]
