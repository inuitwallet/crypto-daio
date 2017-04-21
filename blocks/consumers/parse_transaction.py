import logging

from blocks.models import Transaction, Block
from blocks.utils.rpc import send_rpc

logger = logging.getLogger('block_parser')


def parse_transaction(message):
    # get the transaction hash from the message and return if none found
    tx_hash = message.get('tx_hash')

    if not tx_hash:
        logger.error('no transaction hash in message')
        return
    # get the block from the message
    block_hash = message.get('block_hash')

    if not block_hash:
        logger.error('no block id in message')
        return
    # get the block from the message
    tx_index = message.get('tx_index')

    if not tx_index:
        logger.error('no tx index in message')
        return

    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        logger.error('block {} does not exist'.format(block_hash))
        return

    logger.info('parsing tx {} for block {}'.format(tx_hash, block.height))
    tx, created = Transaction.objects.get_or_create(
        tx_id=tx_hash,
        block=block,
        index=tx_index
    )
    if created:
        logger.info('new tx')
        # fetch the rpc data for the block
        rpc = send_rpc(
            {
                'method': 'getrawtransaction',
                'params': [tx_hash, 1]
            }
        )
        if rpc['error']:
            logger.error('rpc error: {}'.format(rpc['error']))
            return
        # parse the block to save it
        tx.parse_rpc_tx(rpc['result'])
        logger.info('saved tx {} at block {}'.format(tx_hash, block.height))
    else:
        pass
