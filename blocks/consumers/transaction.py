import json
import logging

from channels import Group
from tenant_schemas.utils import schema_context

from blocks.models import Transaction, Block, Address, TxOutput
from blocks.utils.numbers import convert_to_satoshis
from blocks.utils.rpc import send_rpc, get_block_hash

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
            },
            schema_name=message.get('chain')
        )
        if not rpc_tx:
            return

        block_hash = rpc_tx.get('blockhash')
        if not block_hash:
            logger.error('no block hash found in rpc for tx {}'.format(tx_id[:8]))
            # indicates that block is orphaned?
            # get the transaction to get the block it is attached to
            try:
                tx = Transaction.objects.get(tx_id=tx_id)
            except Transaction.DoesNotExist:
                logger.warning('no existing tx with id {}'.format(tx_id[:8]))
                return

            if not tx.block:
                logger.warning('tx {} has no block'.format(tx_id[:8]))

            # get the current height of this block
            block_height = tx.block.height

            # then delete the block
            tx.block.delete()

            # get the block hash of the actual block at this height
            block_hash = get_block_hash(block_height, message.get('chain'))

        block, block_created = Block.objects.get_or_create(hash=block_hash)
        if block_created:
            # save has triggered validation which will parse the full block with tx
            logger.warning('block {} is new when parsing tx {}'.format(block, tx_id))
            return

        # get the block too for the index
        rpc_block = send_rpc(
            {
                'method': 'getblock',
                'params': [block_hash]
            },
            schema_name=message.get('chain')
        )

        if not rpc_block:
            return

        tx_list = rpc_block.get('tx', [])
        if not tx_list:
            logger.error('problem getting tx_list from block {}'.format(block))
            return

        tx_index = tx_list.index(tx_id)

        try:
            tx = Transaction.objects.get(tx_id=tx_id)
        except Transaction.DoesNotExist:
            logger.warning('tx {} is new.'.format(tx_id[:8]))
            tx = Transaction(tx_id=tx_id, block=block, index=tx_index)
            tx.save(validate=False)

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

                if script.get('type') == 'park':
                    logger.info('park output')
                    park_data = script.get('park', {})
                    tx_out.park_duration = park_data.get('duration')
                    address = park_data.get('unparkaddress')
                else:
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
                # update the value too
                tx_out.value = convert_to_satoshis(tout.get('value', 0.0))
                tx_out.save()
                logger.info('added {} to {}'.format(address, tx_out))
            return

        if error_message == 'address missing from previous output' \
                or error_message == 'previous output value is 0':
            scanned_transactions = []
            for tx_in in tx.inputs.all():
                if tx_in.previous_output:
                    if not tx_in.previous_output.address:
                        previous_tx_id = tx_in.previous_output.transaction.tx_id

                        if previous_tx_id in scanned_transactions:
                            continue

                        rpc_prev_tx = send_rpc(
                            {
                                'method': 'getrawtransaction',
                                'params': [previous_tx_id, 1]
                            },
                            schema_name=message.get('chain')
                        )

                        for tout in rpc_prev_tx.get('vout', []):
                            if tout.get('n') != tx_in.previous_output.index:
                                continue
                            script = tout.get('scriptPubKey')

                            if not script:
                                logger.warning(
                                    'no script found in rpc for output {}'.format(
                                        tx_in.previous_output
                                    )
                                )
                                continue

                            if script.get('type') == 'park':
                                logger.info('park output')
                                park_data = script.get('park', {})
                                tx_in.previous_output.park_duration = park_data.get('duration')  # noqa
                                address = park_data.get('unparkaddress')
                            else:
                                addresses = script.get('addresses', [])
                                if not addresses:
                                    logger.warning(
                                        'no addresses found in rpc for output {}'.format(
                                            tx_in.previous_output
                                        )
                                    )
                                    continue
                                address = addresses[0]

                            address_object, _ = Address.objects.get_or_create(
                                address=address
                            )

                            if tx_in.previous_output.address == address_object:
                                logger.info(
                                    'output {} already has address {}'.format(
                                        tx_in.previous_output,
                                        address
                                    )
                                )
                                continue
                            tx_in.previous_output.address = address_object
                            # update the value too
                            tx_in.previous_output.value = convert_to_satoshis(
                                tout.get('value', 0.0)
                            )
                            tx_in.previous_output.save()
                            logger.info(
                                'added {} to {}'.format(address, tx_in.previous_output)
                            )
                            # re-validate transaction too
                            tx_in.previous_output.transaction.save()

                        scanned_transactions.append(previous_tx_id)
            return

        if error_message == 'park output has no duration':
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

                if script.get('type') != 'park':
                    continue

                park_data = script.get('park', {})
                tx_out.park_duration = park_data.get('duration')
                address = park_data.get('unparkaddress')
                address_object, _ = Address.objects.get_or_create(address=address)
                tx_out.address = address_object
                tx_out.save()
                logger.info('added park data to {}'.format(tx_out))

        tx.parse_rpc_tx(rpc_tx)
