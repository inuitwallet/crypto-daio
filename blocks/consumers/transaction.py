import logging

from channels import Channel
from django.db import IntegrityError, connection
from tenant_schemas.utils import schema_context

from blocks.models import Transaction, Block
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
        block_hash (required) string - hash of block that transaction belongs to.
                                       if not passed an rpc call is made to get it.
        tx_index (required) string - index of transaction in relation to block.
                                     if not passed an rpc call is made to get it.
                                     
    :return: boolean
    """
    with schema_context(message.get('chain')):
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
        )

        if not created:
            logger.warning('existing tx {} found at {}'.format(tx, block))
            if tx.index != tx_index or tx.block != block:
                logger.error('index or block not a match. repairing {}'.format(tx))
                Channel('repair_transaction').send(
                    {
                        'chain': connection.schema_name,
                        'tx_id': tx_id
                    }
                )
                return
            logger.info('index and block match. leaving {}'.format(tx))
            return

        # tx is new
        logger.info('new tx created {}. repairing'.format(tx))
        Channel('repair_transaction').send(
            {
                'chain': connection.schema_name,
                'tx_id': tx_id
            }
        )
        return


def repair_transaction(message):
    """
    repair the given transaction
    :param message: 
    :return: 
    """
    with schema_context(message.get('chain')):
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
            logger.error('problem getting tx_list from block {}'.format(block))
            return

        tx_index = tx_list.index(tx_id)

        # we now have tx_id, tx_index and block
        tx, created = Transaction.objects.get_or_create(tx_id=tx_id)

        if created:
            logger.warning('tx {} is new. saving and validating')
            tx.block = block
            tx.index = tx_index
            tx.save()
            return

        logger.info('repairing tx {}'.format(tx))

        valid, error_message = tx.validate()

        if valid:
            logger.info('tx {} is valid'.format(tx))
            return

        logger.error('tx {} invalid: {}'.format(tx, error_message))

        if error_message == 'incorrect index':
            tx.index = tx_index
            tx.save()
            logger.info('updated index of {}'.format(tx))
            return

        if error_message == 'no block':
            tx.block = block
            tx.save()
            logger.info('update block on {}'.format(tx))
            return

        tx.parse_rpc_tx(rpc_tx)


def validate_transactions(message):
    """
    given a block, validate all transactions
    :param message: asgi valid message containing:
        block_hash (required) string - hash of block to use for validations
    :return: 
    """
    with schema_context(message.get('chain')):
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
                Channel('parse_transaction').send(
                    {
                        'chain': connection.tenant.schema_name,
                        'tx_hash': tx.tx_id,
                        'block_hash': block.hash
                    }
                )
            else:
                logger.info(
                    'transaction {} at block {} is valid'.format(tx.tx_id, block.hash)
                )
