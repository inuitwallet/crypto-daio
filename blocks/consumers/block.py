import logging

from asgiref.base_layer import BaseChannelLayer
from channels import Channel
from tenant_schemas.utils import schema_context

from blocks.models import Block, Transaction
from blocks.utils.rpc import send_rpc, get_block_hash

logger = logging.getLogger(__name__)


def parse_block(message):
    """
    Process a block. 
    Create and parse if block didn't previously exist.
    Fetch and validate if block did previously exist.
    
    :param message: asgi valid message containing
        block_hash (required) string - hash of the block to process
        parse_next (optional) boolean - set True to move to the next 
                                        block after passing validation
    """
    with schema_context(message.get('chain')):
        block_hash = message.get('block_hash')

        if not block_hash:
            logger.error('no block hash in message')
            return

        block, created = Block.objects.get_or_create(
            hash=block_hash
        )

        if not created:
            logger.info('existing block {} found'.format(block))
            # save prompts for block validation
        block.save()


def repair_block(message):
    """
    Repair an existing block
    
    :param message: asgi valid message containing:
        block_hash (required) string - hash of block to repair
    """
    with schema_context(message.get('chain')):
        block_hash = message.get('block_hash')

        if not block_hash:
            logger.error('no block hash in message')
            return

        try:
            block = Block.objects.get(hash=block_hash)
        except Block.DoesNotExist:
            logger.error('no block found with hash {}'.format(block_hash))
            try:
                Channel('parse_block').send(
                    {
                        'chain': message.get('chain'),
                        'block_hash': block_hash
                    }
                )
            except BaseChannelLayer.ChannelFull:
                logger.error('CHANNEL FULL!')
            return

        valid, error_message = block.validate()
        if valid:
            logger.info('block {} is valid'.format(block))
            return

        logger.info('repairing block {}: {}'.format(block, error_message))

        # merkle root error means missing, extra or duplicate transactions
        if error_message == 'merkle root incorrect':
            fix_merkle_root(block, message.get('chain'))
            return

        if 'previous' in message:
            fix_previous_block(block, message.get('chain'))
            return

        if 'next' in message:
            fix_next_block(block, message.get('chain'))
            return

        # all other errors with the block can be solved by re-parsing it
        logger.info('re-parsing {}'.format(block))
        rpc = send_rpc(
            {
                'method': 'getblock',
                'params': [block_hash]
            },
            schema_name=message.get('chain')
        )
        if not rpc:
            return False
        # parse the block to save it
        block.parse_rpc_block(rpc)


def fix_previous_block(block, chain):
    logger.info('fixing previous block')
    prev_hash = get_block_hash(block.height - 1, schema_name=chain)
    if not prev_hash:
        return
    prev_block, created = Block.objects.get_or_create(hash=prev_hash)
    prev_block.next_block = block
    prev_block.save()
    block.previous_block = prev_block
    block.save()


def fix_next_block(block, chain):
    logger.info('fixing next block')
    next_hash = get_block_hash(block.height + 1, schema_name=chain)
    if not next_hash:
        return
    next_block, created = Block.objects.get_or_create(hash=next_hash)
    next_block.previous_block = block
    next_block.save()
    block.next_block = next_block
    block.save()


def fix_merkle_root(block, chain):
    logger.info('fixing merkle root on block {}'.format(block))
    rpc = send_rpc(
        {
            'method': 'getblock',
            'params': [block.hash],
        },
        schema_name=chain
    )

    if not rpc:
        return False

    transactions = rpc.get('tx', [])
    block_tx = block.transactions.all().values_list('tx_id', flat=True)

    # add missing transactions
    for tx_id in list(set(transactions) - set(block_tx)):
        logger.info('adding missing tx {} to {}'.format(tx_id[:8], block))
        tx, _ = Transaction.objects.get_or_create(
            tx_id=tx_id
        )
        logger.info('block = {}'.format(block))
        tx.block = block
        tx.save()

    # remove additional transactions
    for tx in block.transactions.all():
        if tx.tx_id not in transactions:
            logger.error('tx {} does not belong to block {}'.format(tx, block))
            tx.delete()
            continue

        # fix index
        rpc_index = transactions.index(tx.tx_id)
        if tx.index != rpc_index:
            logger.error(
                'incorrect index for tx {}: ({})'.format(tx, rpc_index)
            )
            tx.index = rpc_index
            tx.save()

    # reinitialise validation
    block.save()
