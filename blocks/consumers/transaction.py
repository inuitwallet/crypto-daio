import logging

from tenant_schemas.utils import schema_context

from blocks.models import Transaction, Block, Address, TxOutput
from blocks.utils.rpc import send_rpc

logger = logging.getLogger(__name__)


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
            logger.error('no block hash found in rpc_tx: {}'.format(rpc_tx))
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

        if 'has no address' in error_message:
            for tout in rpc_tx.get('vout', []):
                try:
                    tx_out = tx.outputs.get(index=tout.get('n'))
                except TxOutput.DoesNotExist:
                    logger.warning('output not found: {}'.format(tout.get('n')))
                    rpc_tx.save()
                    return
                script = tout.get('scriptPubKey')
                if not script:
                    return
                addresses = script.get('addresses')
                if not addresses:
                    return
                address = addresses[0]
                address_object, _ = Address.objects.get_or_create(address=address)
                if tx_out.address == address_object:
                    return
                tx_out.address = address_object
                tx_out.save()
                logger.info('added {} to {}'.format(address, tx_out))

        tx.parse_rpc_tx(rpc_tx)
