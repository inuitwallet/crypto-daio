import logging

from channels import Channel
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

        if error_message == 'output has no address':
            for tout in rpc_tx.get('vout', []):
                try:
                    tx_out = tx.outputs.get(index=tout.get('n'))
                except TxOutput.DoesNotExist:
                    logger.warning('output not found: {}'.format(tout.get('n')))
                    tx.save()
                    continue
                script = tout.get('scriptPubKey')
                if not script:
                    logger.warning(
                        'no script found in rpc for output {}'.format(tx_out)
                    )
                    continue
                addresses = script.get('addresses', [])
                if not addresses:
                    logger.warning(
                        'no addresses found in rpc for output {}'.format(tx_out)
                    )
                    continue
                address = addresses[0]
                address_object, _ = Address.objects.get_or_create(address=address)
                if tx_out.address == address_object:
                    logger.info(
                        'output {} already has address {}'.format(tx_out, address)
                    )
                    continue
                tx_out.address = address_object
                tx_out.save()
                logger.info('added {} to {}'.format(address, tx_out))
            return

        if error_message == 'address missing from previous output':
            scanned_transactions = []
            for tx_in in tx.inputs.all():
                if tx_in.previous_output:
                    if not tx_in.previous_output.address:
                        previous_tx_id = tx_in.previous_output.transaction.tx_id
                        if previous_tx_id in scanned_transactions:
                            continue

                        logger.info(
                            're-validating {}'.format(previous_tx_id)
                        )
                        Channel('repair_transaction').send({
                            'chain': message.get('chain'),
                            'tx_id': tx_in.previous_output.transaction.tx_id
                        })
                        scanned_transactions.append(previous_tx_id)

        tx.parse_rpc_tx(rpc_tx)
