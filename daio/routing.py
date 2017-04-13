from channels import route
from blocks.consumers.parse_block import parse_block

channel_routing = [
    route('parse_block', parse_block),
]
