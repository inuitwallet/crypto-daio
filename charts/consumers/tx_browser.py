import json
import logging

from blocks.models import Transaction
from models import TxInput

logger = logging.getLogger(__name__)


def get_address_transactions(address, from_block):
    txs = Transaction.objects.distinct(
        'tx_id'
    ).filter(
        input__previous_output__address=address
    ).exclude(
        index=1
    ).exclude(
        block=None
    ).exclude(
        block__height__gte=from_block
    ).order_by(
        'tx_id'
    )

    return sorted(txs, key=lambda tx: tx.total_input, reverse=True)


def handle_tx(tx, base_address, nodes, edges, scanned_transactions):
    if tx in scanned_transactions:
        return

    if tx.index == 1:
        return

    if not tx.block:
        return

    scanned_transactions.append(tx)

    logger.info(tx.tx_id)

    # add the Tx to the nodes
    if not any(node['id'] == tx.tx_id for node in nodes):
        nodes.append({
            'id': tx.tx_id,
            'shape': 'dot',
            'title': '{}'.format(tx),
            'size': 3
        })

    if base_address:
        edges.append({
            'from': base_address,
            'to': tx.tx_id,
            'color': 'grey',
            'arrows': 'middle'
        })

    address_inputs = tx.address_inputs
    for input_address in address_inputs:
        # for each input add an edge from the address to the tx.
        # Add the address if it doesn't exist
        if not any(node['id'] == input_address for node in nodes):  # noqa
            nodes.append({
                'id': input_address,
                'label': input_address,
                'color': '#92d9e5',
                'title': 'Address'
            })
        edges.append({
            'from': input_address,
            'to': tx.tx_id,
            'value': address_inputs.get(input_address, 0) / 100000000,
            'title': address_inputs.get(input_address, 0) / 100000000,
            'color': '#2cf948',
            'arrows': 'middle'
        })

    output_totals = {'spent': {}, 'unspent': {}}
    for tx_output in tx.outputs.all():
        try:
            if tx_output.input:
                if tx_output.input.transaction not in output_totals['spent']:
                    output_totals['spent'][tx_output.input.transaction] = 0
                output_totals['spent'][tx_output.input.transaction] += tx_output.value
        except TxInput.DoesNotExist:
            if not tx_output.address:
                continue
            if tx_output.address.address not in output_totals['unspent']:
                output_totals['unspent'][tx_output.address.address] = 0
            output_totals['unspent'][tx_output.address.address] += tx_output.value

    for address in output_totals['unspent']:
        if not any(node['id'] == address for node in nodes):
            nodes.append({
                'id': address,
                'label': address,
                'color': '#92d9e5',
                'title': 'Address'
            })
        edges.append({
            'from': tx.tx_id,
            'to': address,
            'value': output_totals['unspent'].get(address, 0) / 100000000,
            'title': output_totals['unspent'].get(address, 0) / 100000000,
            'color': '#d86868',
            'arrows': 'middle'
        })

    for transaction in output_totals['spent']:
        # add the Tx to the nodes
        if not any(node['id'] == transaction.tx_id for node in nodes):
            nodes.append({
                'id': transaction.tx_id,
                'shape': 'dot',
                'title': '{}'.format(transaction),
                'size': 3
            })
        edges.append({
            'from': tx.tx_id,
            'to': transaction.tx_id,
            'value': output_totals['spent'].get(transaction, 0) / 100000000,
            'title': output_totals['spent'].get(transaction, 0) / 100000000,
            'color': '#f4a84b',
            'arrows': 'middle'
        })

    return nodes, edges, scanned_transactions


def recalc_browser(message_dict, message):
    nodes = []
    edges = []
    scanned_transactions = []

    main_node = message_dict['payload'].get('main_node', '')
    seed_nodes = message_dict['payload'].get('seed_nodes', [])

    # an address has a label
    is_address = main_node.get('label')

    # if the main node is an address we look at the previous transactions to see the
    # earliest block we need to gather onward transactions from
    minimum_block = None
    if is_address:
        nodes.append({
            'id': is_address,
            'label': is_address,
            'color': '#89ff91',
            'title': 'Address'
        })
        for node in seed_nodes:
            # an address has a label
            parent_is_address = node.get('label')

            if parent_is_address:
                continue

            # 2:bcb91b1c@1089790:cf716f6f
            block_number = node.get('title').split('@')[1].split(':')[0]

            if not minimum_block:
                minimum_block = block_number

            if block_number < minimum_block:
                minimum_block = block_number

        txs = get_address_transactions(is_address, minimum_block)
        for tx in txs:
            nodes, edges, scanned_transactions = handle_tx(
                tx,
                is_address,
                nodes,
                edges,
                scanned_transactions
            )

    # otherwise we use the main_node transaction to calculate onward

    message.reply_channel.send(
        {
            'text': json.dumps(
                {
                    'message_type': 'new_browser',
                    'nodes': nodes,
                    'edges': edges
                }
            )
        },
        immediately=True
    )





