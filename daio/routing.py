from channels import route
from blocks.consumers.block import parse_block, validate_block, repair_block
from blocks.consumers.transaction import parse_transaction, validate_transactions

channel_routing = [
    # Blocks
    route('parse_block', parse_block),
    route('validate_block', validate_block),
    route('repair_block', repair_block),

    # Transactions
    route('parse_transaction', parse_transaction),
    route('validate_transactions', validate_transactions),
]
