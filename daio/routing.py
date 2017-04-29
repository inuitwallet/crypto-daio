from channels import route
from blocks.consumers.block import parse_block, repair_block
from blocks.consumers.transaction import (
    parse_transaction,
    repair_transaction,
    validate_transactions,
)

channel_routing = [
    # Blocks
    route('parse_block', parse_block),
    route('repair_block', repair_block),

    # Transactions
    route('parse_transaction', parse_transaction),
    route('repair_transaction', repair_transaction),
    route('validate_transactions', validate_transactions),
]
