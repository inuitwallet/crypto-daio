import logging

from blocks.models import Block
from blocks.utils.channels import send_to_channel
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
    block_hash = message.get('block_hash')

    if not block_hash:
        logger.error('no block hash in message')
        return

    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        logger.error('no block found with hash {}'.format(block_hash))
        send_to_channel('parse_block', {'block_hash', block_hash})
        return

    valid, error_message = block.validate()
    if valid:
        logger.info('block {} is valid'.format(block))
        return

    logger.info('repairing block {}: {}'.format(block, error_message))

    # Possible error messages are:
    # missing attribute: <attribute_name>
    # no previous block hash
    # incorrect hash
    # incorrect previous height
    # previous block does not point to this block
    # incorrect next height
    # next block does not lead on from this block
    # merkle root incorrect

    # merkle root error means missing, extra or duplicate transactions
    if error_message == 'merkle root incorrect':
        fix_merkle_root(block)
        return

    if 'previous' in message:
        fix_previous_block(block)
        return

    if 'next' in message:
        fix_next_block(block)
        return

    # all other errors with the block can be solved by re-parsing it
    logger.info('re-parsing {}'.format(block))
    rpc = send_rpc(
        {
            'method': 'getblock',
            'params': [block_hash]
        }
    )
    if not rpc:
        return False
    # parse the block to save it
    block.parse_rpc_block(rpc)


def fix_previous_block(block):
    logger.info('fixing previous block')
    prev_hash = get_block_hash(block.height - 1)
    if not prev_hash:
        return
    prev_block, created = Block.objects.get_or_create(hash=prev_hash)
    if created:
        # save will trigger validation on new previous block
        logger.warning('previous block of {} is new. validating'.format(block))
        return
    prev_block.next_block = block
    prev_block.save()
    block.previous_block = prev_block
    block.save()


def fix_next_block(block):
    logger.info('fixing next block')
    next_hash = get_block_hash(block.height + 1)
    if not next_hash:
        return
    next_block, created = Block.objects.get_or_create(hash=next_hash)
    if created:
        # save will trigger validation on new previous block
        logger.warning('next block of {} is new. validating'.format(block))
        return
    next_block.previous_block = block
    next_block.save()
    block.next_block = next_block
    block.save()


def fix_merkle_root(block):
    logger.info('fixing merkle root on block {}'.format(block))
    rpc = send_rpc(
        {
            'method': 'getblock',
            'params': [block.hash]
        }
    )

    if not rpc:
        return False

    transactions = rpc.get('tx', [])
    block_tx = block.transactions.all().values_list('tx_id', flat=True)

    # add missing transactions
    for tx in list(set(transactions) - set(block_tx)):
        logger.info('adding missing tx {} to {}'.format(tx[:8], block))
        send_to_channel(
            'parse_transaction', {
                'tx_id': tx,
                'tx_index': transactions.index(tx),
                'block_hash': block.hash
            }
        )

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
            tx.save(validate=False)

    # reinitialise validation
    block.save()
