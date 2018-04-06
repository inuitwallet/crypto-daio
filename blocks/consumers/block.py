import json
import logging

from django.db import connection
from tenant_schemas.utils import schema_context

from blocks.models import Block, Transaction
from blocks.utils.rpc import get_block_hash, send_rpc

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
            logger.error('no block found for hash {}'.format(block_hash[:7]))
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

        if error_message == 'incorrect tx indexing':
            fix_merkle_root(block, message.get('chain'))
            return

        if error_message in ['missing attribute: self.previous_block',
                             'no previous block hash',
                             'incorrect previous height',
                             'no previous block hash']:
            fix_previous_block(block, message.get('chain'))
            return

        if error_message in ['incorrect next height',
                             'next block does not lead on from this block',
                             'missing next block']:
            fix_next_block(block, message.get('chain'))
            return

        if error_message in ['custodian votes do not match',
                             'park rate votes do not match',
                             'motion votes do not match',
                             'fee votes do not match']:
            fix_block_votes(block, message.get('chain'))

        if error_message == 'active park rates do not match':
            fix_block_park_rates(block, message.get('chain'))

        # all other errors with the block can be solved by re-parsing it
        logger.info('re-parsing {}'.format(block))
        rpc = send_rpc(
            {
                'method': 'getblock',
                'params': [block_hash, True, True]
            },
            schema_name=message.get('chain')
        )
        if not rpc:
            return False
        # parse the block to save it
        block.parse_rpc_block(rpc)


def fix_previous_block(block, chain):
    logger.info('fixing previous block for {}'.format(block))
    prev_hash = get_block_hash(block.height - 1, schema_name=chain)

    if not prev_hash:
        return

    try:
        prev_block = Block.objects.get(hash=prev_hash)
    except Block.DoesNotExist:
        prev_block = Block.objects.create(hash=prev_hash)

    try:
        prev_height_block = Block.objects.get(height=block.height - 1)
    except Block.DoesNotExist:
        prev_height_block = prev_block

    if prev_block != prev_height_block:
        # the block with the previous height doesn't match the hash from this block
        # likely to be an orphan so remove it
        prev_height_block.delete()

    block.previous_block = prev_block
    block.save()

    prev_block.height = block.height - 1
    prev_block.next_block = block
    prev_block.save()


def fix_next_block(block, chain):
    logger.info('fixing next block for {}'.format(block))
    # it's likely that this block is an orphan so we should remove it and rescan
    this_height = block.height
    this_hash = get_block_hash(this_height, schema_name=chain)

    if not this_hash:
        logger.warning('could not get hash for block at height {}'.format(this_height))
        return

    if this_hash != block.hash:
        block = Block.objects.create(hash=this_hash, height=this_height)

    next_hash = get_block_hash(this_height + 1, schema_name=chain)

    if not next_hash:
        logger.warning('could not get next hash for height {}'.format(this_height + 1))
        return

    try:
        next_block = Block.objects.get(hash=next_hash)
    except Block.DoesNotExist:
        next_block = Block.objects.create(hash=next_hash)

    block.next_block = next_block
    block.save()

    next_block.height = this_height + 1
    next_block.previous_block = block
    next_block.save(validate=False)


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


def fix_block_votes(block, chain):
    logger.info('fixing votes on block {}'.format(block))
    rpc = send_rpc(
        {
            'method': 'getblock',
            'params': [block.hash],
        },
        schema_name=chain
    )

    if not rpc:
        return False

    vote = rpc.get('vote', {})
    block.parse_rpc_votes(vote)
    block.vote = vote
    block.save()


def fix_block_park_rates(block, chain):
    logger.info('fixing park rates on block {}'.format(block))
    rpc = send_rpc(
        {
            'method': 'getblock',
            'params': [block.hash],
        },
        schema_name=chain
    )

    if not rpc:
        return False

    park_rates = rpc.get('parkrates', [])
    block.parse_rpc_parkrates(park_rates)
    block.park_rates = park_rates
    block.save()


def check_block_hash(message):
    schema = message.get('chain')
    with schema_context(schema):
        block_hash = message.get('block_hash')
        block_height = message.get('block_height')

        check_hash = get_block_hash(block_height, schema)

        if check_hash != block_hash:
            logger.error('block at height {} has incorrect hash'.format(block_height))
