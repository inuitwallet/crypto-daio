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
        # parse the block to save it
        block.parse_rpc_block(rpc['result'])
        logger.info('saved block {}'.format(block.height))

    else:
        logger.info('existing block')
        # validate the block
        valid, message = block.validate()
        if valid:
            # block is valid so restart the scan at the next block
            logger.info('block valid. moving to next block')
            Channel('parse_block').send({'block_hash': block.next_block.hash})
        else:
            # block is invalid so re-fetch from rpc and save again
            logger.warning('INVALID BLOCK! {}'.format(message))
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

