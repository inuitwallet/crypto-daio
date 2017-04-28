import logging

from channels import Channel

from blocks.models import Block
from blocks.utils.rpc import send_rpc, get_block_hash

logger = logging.getLogger('daio')


def parse_block(message):
    """
    Process a block. 
    Create and parse if block didn't previously exist.
    Fetch and validate if block did previously exist.
    
    :param message: asgi valid message containing
        block_hash (required) string - hash of the block to process
        parse_next (optional) boolean - set True to move to the next 
                                        block after passing validation
    
    :return boolean
    """
    parse_next = message.get('parse_next', False)
    block_hash = message.get('block_hash')
    if not block_hash:
        logger.error('no block hash in message passed to validate')
        return False

    logger.info('parsing block {}'.format(block_hash))
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
            return False
        # parse the block to save it
        block.parse_rpc_block(rpc['result'])
        logger.info('saved block {}'.format(block.height))

    else:
        logger.info('existing block found at {}. validating'.format(block.height))
        Channel('validate_block').send(
            {'block_hash': block.hash, 'parse_next': parse_next}
        )


def validate_block(message):
    """
    Validate an existing block.
    If validation passes, validate the blocks transactions and optionally 
    process the next block.
    If validation fails, act on the block accordingly
    
    Block will have repairs made in it fails validation. 
    This does not guarantee that the block will pass validation afterwards
    
    :param message: asgi valid message containing:
        block_hash (required) string - hash of block to validate
        parse_next (optional) boolean - set True to move to the next block 
                                        after passing validation
    
    :return: boolean 
    """
    parse_next = message.get('parse_next', False)
    block_hash = message.get('block_hash')

    if not block_hash:
        logger.error('no block hash in message')
        return False

    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        logger.error('no block found with hash {}'.format(block_hash))
        return False

    if block.height == 0:
        # genesis block is ok
        return True

    valid, error_message = block.validate()

    if valid:
        logger.info(
            'block {} at {} is valid. checking transactions'.format(
                block.hash,
                block.height
            )
        )
        Channel('validate_transactions').send({'block_hash': block.hash})
        if parse_next:
            if not block.next_block:
                logger.warning('no next block {} found to parse'.format(block.height + 1))
                return
            if not block.next_block.hash:
                logger.error('next block {} has no hash'.format(block.height + 1))
                return
            Channel('parse_block').send({'block_hash': block.next_block.hash})
    else:
        logger.warning(
            'INVALID BLOCK {} at {}! {}'.format(block.hash, block.height, error_message)
        )
        Channel('repair_block').send(
            {
                'block_hash': block.hash,
                'error_message': error_message,
                'parse_next': parse_next
            }
        )


def repair_block(message):
    """
    Repair an existing block
    
    :param message: asgi valid message containing:
        block_hash (required) string - hash of block to repair
        error_message (required) string - validation error message
        parse_next (optional) boolean - set True to move to the next block 
                                        after passing validation
        
    :return: boolean 
    """
    parse_next = message.get('parse_next', False)
    error_message = message.get('error_message')

    if not error_message:
        logger.error('no error message passed to repair')
        return False

    block_hash = message.get('block_hash')

    if not block_hash:
        logger.error('no block hash in message passed to repair')
        return False

    try:
        block = Block.objects.get(hash=block_hash)
    except Block.DoesNotExist:
        logger.error('no block found with hash {}'.format(block_hash))
        return False

    logger.info('repairing block {}'.format(block.height))
    # merkle root error means missing, extra or duplicate transactions
    if error_message == 'merkle root incorrect':
        rpc = send_rpc(
            {
                'method': 'getblock',
                'params': [block.hash]
            }
        )

        if rpc['error']:
            logger.error('rpc error: {}'.format(rpc['error']))
            return False

        transactions = rpc['result'].get('tx', [])
        block_tx = block.transactions.all().values_list('tx_id', flat=True)

        # add missing transactions
        for tx in list(set(transactions) - set(block_tx)):
            logger.info('adding missing tx {}'.format(tx))
            Channel('parse_transaction').send(
                {
                    'tx_hash': tx,
                    'tx_index': transactions.index(tx),
                    'block_hash': block.hash
                }
            )

        # remove additional transactions
        for tx in block.transactions.all():
            if tx.tx_id not in transactions:
                logger.error(
                    'tx {} does not belong to block {}'.format(
                        tx.tx_id,
                        block.height
                    )
                )
                tx.delete()

        # check for duplicate blocks (shouldn't happen as tx_id id unique)
        if len(list(set(block_tx))) != len(block_tx):
            logger.error('detected duplicate transaction')
            block.transactions.all().delete()

        # validate the transactions
        Channel('validate_transactions').send({'block': block})

    elif error_message == 'missing attribute: self.previous_block':
        try:
            prev_block = Block.objects.get(height=block.height - 1)
        except Block.DoesNotExist:
            logger.error('previous block not found')
            Channel('parse_block').send({'block_hash': get_block_hash(block.height - 1)})
            return

        logger.info('fixing next block')
        block.previous_block = prev_block
        block.save()

        prev_block.next_block = block
        prev_block.save()

    else:
        # all other errors with the block can be solved by deleting and re-parsing it
        Channel('parse_block').send(
            {'block_hash': block.hash, 'parse_next': parse_next}
        )
