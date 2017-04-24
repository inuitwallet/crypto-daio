import logging

from channels import Channel

from blocks.models import Block
from blocks.utils.rpc import send_rpc

logger = logging.getLogger('daio')


def parse_block(message):
    # get the block hash from the message and return if none found
    block_hash = message.get('block_hash')
    if not block_hash:
        logger.error('no block hash in message')
        return
    logger.info('parsing block {}'.format(block_hash))
    # get the block object for the given hash
    block, created = Block.objects.get_or_create(
        hash=block_hash
    )
    if created:
        logger.info('new block created for {}'.format(block.hash))
        # fetch the rpc data for the block
        rpc = send_rpc(
            {
                'method': 'getblock',
                'params': [block_hash]
            }
        )
        if rpc['error']:
            logger.error('rpc error: {}'.format(rpc['error']))
            return
        # parse the block to save it
        block.parse_rpc_block(rpc['result'])
        logger.info('saved block {}'.format(block.height))

    else:
        logger.info('existing block found at {}'.format(block.height))
        # validate the block
        valid, error_message = block.validate()
        if valid:
            if message.get('no_parse'):
                return

            # block is valid so restart the scan at the next block
            if not block.next_block:
                logger.warning(
                    'no next block. Is this the top block? {}'.format(block.height)
                )
                return
            logger.info(
                'block valid. checking transactions and '
                'moving to next block ({})'.format(block.next_block.height)
            )
            for tx in block.transactions.all().order_by('index'):
                if not tx.is_valid:
                    tx_hash = tx.tx_id
                    tx.delete()
                    Channel('parse_transaction').send({'tx_hash': tx_hash})
            Channel('parse_block').send({'block_hash': block.next_block.hash})
        else:
            # block is invalid so re-fetch from rpc and save again
            logger.warning('INVALID BLOCK at {}! {}'.format(block.height, error_message))
            # delete all the blocks transactions
            block.transactions.all().delete()
            # get it again to redo the inputs
            rpc = send_rpc(
                {
                    'method': 'getblock',
                    'params': [block.hash]
                }
            )
            if rpc['error']:
                logger.error('rpc error: {}'.format(rpc['error']))
                return
            # parse the block to save it
            block.parse_rpc_block(rpc['result'])
            logger.info('re scanned and save saved block {}'.format(block.height))

