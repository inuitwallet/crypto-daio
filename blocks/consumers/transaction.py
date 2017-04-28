import logging

from channels import Channel

from blocks.models import Transaction, Block
from blocks.utils.rpc import send_rpc

logger = logging.getLogger('daio')


def parse_transaction(message):
    """
    Process a transaction. 
    Create and parse if the transaction is new
    Validate if Transaction already exists
    If validation fails, re-parse Transaction
    
    :param message: asgi valid message containing:
        tx_hash (required) string - tx_id of transaction rto process
        block_hash (optional) string - hash of block that transaction belongs to.
                                       if not passed an rpc call is made to get it.
        tx_index (optional) string - index of transaction in relation to block.
                                     if not passed an rpc call is made to get it.
                                     
    :return: boolean
    """
    rpc = None
    # get the transaction hash from the message and return if none found
    tx_hash = message.get('tx_hash')

    if not tx_hash:
        logger.error('no transaction hash in message')
        return False

    # get the block from the message
    block_hash = message.get('block_hash')

    if not block_hash:
        logger.warning('no block hash in message for tx {}'.format(tx_hash))
        # we are scanning just the transaction so fetch the raw data
        rpc = send_rpc(
            {
                'method': 'getrawtransaction',
                'params': [tx_hash, 1]
            }
        )
        if rpc['error']:
            logger.error('rpc error at tx {}: {}'.format(tx_hash, rpc['error']))
            return False

        # get the block_hash from the transaction
        block_hash = rpc['result'].get('blockhash')

        if not block_hash:
            logger.error('no block hash found from tx rpc')
            return False

    # get the index from the message
    tx_index = message.get('tx_index')

    if tx_index is None:
        logger.warning('no tx index in message for tx {}'.format(tx_hash))
        block_rpc = send_rpc(
            {
                'method': 'getblock',
                'params': [block_hash]
            }
        )

        if block_rpc['error']:
            logger.error(
                'get tx_index rpc error at tx {} for {} {}'.format(
                    tx_hash,
                    block_hash,
                    block_rpc['error']
                )
            )
            return False

        try:
            tx_index = block_rpc['result'].get('tx', []).index(tx_hash)
        except ValueError:
            logger.error(
                'transaction doesn\'t belong to block: {} not in {}'.format(
                    tx_hash,
                    block_rpc['result'].get('tx', [])
                )
            )
            try:
                Transaction.objects.get(tx_id=tx_hash).delete()
                return False
            except Transaction.DoesNotExist:
                return False

    block, created = Block.objects.get_or_create(hash=block_hash)
    if created:
        logger.warning('block is newly created so parsing full block')
        Channel('parse_block').send({'block_hash': block_hash})
        return False

    logger.info('parsing tx {} for block {}'.format(tx_hash, block.height))
    tx, created = Transaction.objects.get_or_create(
        tx_id=tx_hash,
        block=block,
        index=tx_index
    )
    if created:
        logger.info('new tx {} at block {}'.format(tx_hash, block.height))
        # fetch the rpc data for the block if we haven't already
        if not rpc:
            rpc = send_rpc(
                {
                    'method': 'getrawtransaction',
                    'params': [tx_hash, 1]
                }
            )
            if rpc['error']:
                logger.error('rpc error: {} {}'.format(rpc['error'], tx_hash))
                return
        # parse the block to save it
        tx.parse_rpc_tx(rpc['result'])
    else:
        logger.info('existing tx {} found at {}'.format(tx_hash, block.height))
        # validate the transaction
        valid, error_message = tx.validate()
        if not valid:
            # transaction is invalid so re-fetch from rpc and save again
            logger.warning(
                'INVALID TX {} at {}! {}'.format(tx_hash, block.height, error_message)
            )
            # fetch the rpc data for the block if we haven't already
            if not rpc:
                rpc = send_rpc(
                    {
                        'method': 'getrawtransaction',
                        'params': [tx_hash, 1]
                    }
                )
                if rpc['error']:
                    logger.error('rpc error: {}'.format(rpc['error']))
                    return
            # re-parse the block to save it
            tx.parse_rpc_tx(rpc['result'])
        else:
            logger.info('tx {} is valid'.format(tx_hash))