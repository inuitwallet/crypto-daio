import logging

from blocks.models import Transaction, Block
from blocks.utils.channels import send_to_channel
from blocks.utils.rpc import send_rpc

logger = logging.getLogger(__name__)


def parse_transaction(message):
    """
    Process a transaction. 
    Create and parse if the transaction is new
    Validate if Transaction already exists
    If validation fails, re-parse Transaction
    
    :param message: asgi valid message containing:
        tx_id (required) string - tx_id of transaction rto process
        block_hash (optional) string - hash of block that transaction belongs to.
                                       if not passed an rpc call is made to get it.
        tx_index (optional) string - index of transaction in relation to block.
                                     if not passed an rpc call is made to get it.
                                     
    :return: boolean
    """
    # get the transaction hash from the message and return if none found
    tx_id = message.get('tx_id')

    if not tx_id:
        logger.error('no transaction id in message')
        return

    # get the block hash from the message
    block_hash = message.get('block_hash')

    if not block_hash:
        logger.error('no block hash in message')
        return

    # get the index from the message
    tx_index = message.get('tx_index')

    if tx_index is None:
        logger.warning('no tx index in message')
        return

    block, created = Block.objects.get_or_create(hash=block_hash)
    if created:
        # save has triggered validation which will parse the full block with tx
        logger.warning('block {} is new when parsing tx {}'.format(block, tx_id))
        return False

    tx, created = Transaction.objects.get_or_create(
        tx_id=tx_id,
        block=block,
        index=tx_index
    )
    if not created:
        logger.info('existing tx {} found at {}'.format(tx, block))
        tx.save()


def repair_transaction(message):
    """
    repair the given transaction
    :param message: 
    :return: 
    """
    tx_id = message.get('tx_id')
    if not tx_id:
        logger.error('no tx_id passed')

    # get the raw transaction
    rpc_tx = send_rpc(
        {
            'method': 'getrawtransaction',
            'params': [tx_id, 1]
        }
    )
    if not rpc_tx:
        return

    block_hash = rpc_tx.get('blockhash')
    if not block_hash:
        logger.error('no block hash found in rpc_tx')
        return

    block, created = Block.objects.get_or_create(hash=block_hash)
    if created:
        # save has triggered validation which will parse the full block with tx
        logger.warning('block {} is new when parsing tx {}'.format(block, tx_id))
        return False

    # get the block too for the index
    rpc_block = send_rpc(
        {
            'method': 'getblock',
            'params': [block_hash]
        }
    )

    if not rpc_block:
        return

    tx_list = rpc_block.get('tx', [])
    if not tx_list:
        logger.error('problem getting tx list from block {}'.format(block))
        return

    tx_index = tx_list.index(tx_id)

    # we now have tx_id, tx_index and block
    try:
        tx = Transaction.objects.get(
            block=block,
            tx_id=tx_id,
            index=tx_index,
        )
    except Transaction.DoesNotExist:
        tx = Transaction(
            block=block,
            tx_id=tx_id,
            index=tx_index,
        )

    tx.parse_rpc_tx(rpc_tx)


def validate_transactions(message):
    """
    given a block, validate all transactions
    :param message: asgi valid message containing:
        block_hash (required) string - hash of block to use for validations
    :return: 
    """
    block_hash = message.get('block_hash')

    if not block_hash:
        logger.error('no block hash in message passed to validate transactions')
        return False

    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        logger.error('no block found with hash {}'.format(block_hash))
        return False

    for tx in block.transactions.all():
        if not tx.is_valid:
            send_to_channel(
                'parse_transaction',
                {'tx_hash': tx.tx_id, 'block_hash': block.hash}
            )
        else:
            logger.info(
                'transaction {} at block {} is valid'.format(tx.tx_id, block.hash)
            )
