import logging

from channels import Channel

from blocks.models import Block
from blocks.utils.rpc import send_rpc

logger = logging.getLogger('block_parser')


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
        logger.info('new block')
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

        block.parse_rpc_block(rpc['result'])

    else:
        logger.info('existing block')
        if not block.next_block:
            logger.warning('no next block')
            block.parse_rpc_block(block.serialize())
        else:
            Channel('parse_block').send({'block_hash': block.next_block.hash})

    logger.info('saved block {}'.format(block.height))

