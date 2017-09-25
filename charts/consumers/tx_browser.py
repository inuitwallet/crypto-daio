import json
import logging

from blocks.models import Transaction, TxInput, Block, Address

logger = logging.getLogger(__name__)


def yield_address_blocks(address, from_block=0):
    """
    yield blocks that have the given address as an input in at least one transaction
    :param address:
    :param from_block:
    :return:
    """
    blocks = Block.objects.filter(
        transaction__input__previous_output__address__address=address
    ).distinct(
        'height'
    ).order_by('height')

    for block in blocks:
        if block.height < from_block:
            continue
        yield block


def send_block(message, block):
    message.reply_channel.send(
        {
            'text': json.dumps(
                {
                    'message_type': 'node',
                    'node': {
                        'id': block.height,
                        'shape': 'square',
                        'title': 'Block_{}'.format(block),
                        'size': 5
                    }
                }
            )
        },
        immediately=True
    )


def send_address(message, address):
    message.reply_channel.send(
        {
            'text': json.dumps(
                {
                    'message_type': 'node',
                    'node': {
                        'id': address,
                        'label': address,
                        'color': '#92d9e5',
                        'title': 'Address_{}'.format(address),
                    }
                }
            )
        },
        immediately=True
    )


def send_edge(message, edge_from, edge_to, edge_value, colour):
    message.reply_channel.send(
        {
            'text': json.dumps(
                {
                    'message_type': 'edge',
                    'edge': {
                        'id': '{}:{}:{}:{}'.format(edge_from, edge_to, edge_value, colour),
                        'from': edge_from,
                        'to': edge_to,
                        'value': edge_value,
                        'title': edge_value,
                        'color': colour,
                        'arrows': 'to'
                    }
                }
            )
        },
        immediately=True
    )


def handle_block(message, block):
    print('handling block {}'.format(block.height))
    outputs = block.outputs
    unspent = outputs.get('unspent', [])
    spent = outputs.get('spent', [])
    for unspent_address in unspent:
        print('unspent output {} from {} to {}'.format(
            unspent[unspent_address],
            block.height,
            unspent_address.address
        ))
        send_address(message, unspent_address.address)
        send_edge(
            message,
            block.height,
            unspent_address.address,
            unspent[unspent_address],
            '#2cf948'
        )
    for spent_block in spent:
        print('spent output {} from {} to {}'.format(
            spent[spent_block],
            block.height,
            spent_block.height
        ))
        send_block(message, spent_block)
        send_edge(
            message,
            block.height,
            spent_block.height,
            spent[spent_block],
            '#f4a84b'
        )
        handle_block(
            message=message,
            block=spent_block
        )


def add_onward_nodes(message_dict, message):
    node = message_dict['payload'].get('node')

    if not node:
        return

    node_details = node.get('title').split('_')
    node_type = node_details[0]
    node_value = node_details[1]

    if node_type == 'Address':
        for block in yield_address_blocks(node_value):
            # we need to see the value of funds that was input from this address
            input_value = 0
            print('New Block')
            for tx in block.transactions.all():
                # only deal with fund movement transactions. ignore POW and POS tx
                if tx.index < 2:
                    continue

                for tx_input in tx.inputs.all():
                    if not tx_input.previous_output:
                        continue
                    if not tx_input.previous_output.address:
                        continue
                    if tx_input.previous_output.address.address == node_value:
                        input_value += tx_input.previous_output.display_value

            if input_value == 0:
                continue

            # we have the value so create the block and edge the recurse on the block
            send_block(message, block)
            send_edge(
                message=message,
                edge_from=node_value,
                edge_to=block.height,
                edge_value=input_value,
                colour='#00000'
            )
            handle_block(
                message=message,
                block=block,
            )

    # if is_address:
    #     # node is an address so get the onward transactions
    #     txs = get_address_transactions(is_address)
    #     blocks = {}
    #     for tx in txs:
    #         if tx.block.height not in blocks:
    #             blocks[tx.block.height] = 0
    #             send_block(message, tx.block)
    #
    #         address_inputs = tx.address_inputs
    #
    #         for address in address_inputs:
    #             blocks[tx.block.height] += address_inputs.get(address, 0)
    #
    #     for block in blocks:
    #         send_edge(
    #             message,
    #             is_address,
    #             block,
    #             blocks.get(block, 0),
    #             '#2cf948'
    #         )
    #
    #         #address_inputs = tx.address_inputs
    #         #for address in address_inputs:
    #         #    send_address(message, address)
    #         #    send_edge(
    #         #        message,
    #         #        address,
    #         #        tx.tx_id,
    #         #        address_inputs.get(address, 0),
    #         #        '#2cf948'
    #         #    )
    # else:
    #     if 'Block' in node.get('title'):
    #         # we have a Block
    #         block = Block.objects.filter(height=node.get('id')).first()
    #         output_totals = {'spent': {}, 'unspent': {}}
    #
    #         for tx in block.transactions.all():
    #
    #             for tx_output in tx.outputs.all():
    #                 try:
    #                     if tx_output.input.transaction.block not in output_totals['spent']:
    #                         output_totals['spent'][tx_output.input.transaction.block] = 0
    #                     output_totals['spent'][tx_output.input.transaction.block] += tx_output.display_value  # noqa
    #                 except TxInput.DoesNotExist:
    #                     if not tx_output.address:
    #                         continue
    #                     if tx_output.address.address not in output_totals['unspent']:
    #                         output_totals['unspent'][tx_output.address.address] = 0
    #                     output_totals['unspent'][
    #                         tx_output.address.address] += tx_output.display_value  # noqa
    #
    #         for address in output_totals['unspent']:
    #             send_address(message, address)
    #             send_edge(
    #                 message,
    #                 tx.block.height,
    #                 address,
    #                 output_totals['unspent'].get(address, 0),
    #                 '#d86868'
    #             )
    #
    #         for block in output_totals['spent']:
    #             send_block(message, block)
    #             send_edge(
    #                 message,
    #                 tx.block.height,
    #                 block.height,
    #                 output_totals['spent'].get(block, 0),
    #                 '#f4a84b'
    #         )
    #
    #     else:
    #         # we have a transaction
    #         output_totals = {'spent': {}, 'unspent': {}}
    #         tx = Transaction.objects.filter(tx_id=node.get('id')).first()
    #
    #         for tx_output in tx.outputs.all():
    #             try:
    #                 if tx_output.input:
    #                     if tx_output.input.transaction not in output_totals['spent']:
    #                         output_totals['spent'][tx_output.input.transaction] = 0
    #                     output_totals['spent'][tx_output.input.transaction] += tx_output.display_value  # noqa
    #             except TxInput.DoesNotExist:
    #                 if not tx_output.address:
    #                     continue
    #                 if tx_output.address.address not in output_totals['unspent']:
    #                     output_totals['unspent'][tx_output.address.address] = 0
    #                 output_totals['unspent'][tx_output.address.address] += tx_output.display_value  # noqa
    #
    #         for address in output_totals['unspent']:
    #             send_address(message, address)
    #             send_edge(
    #                 message,
    #                 tx.tx_id,
    #                 address,
    #                 output_totals['unspent'].get(address, 0),
    #                 '#d86868'
    #             )
    #
    #         for transaction in output_totals['spent']:
    #             send_tx(message, transaction)
    #             send_edge(
    #                 message,
    #                 tx.tx_id,
    #                 transaction.tx_id,
    #                 output_totals['spent'].get(transaction, 0),
    #                 '#f4a84b'
    #             )

    print('#####\nDone\n#####')
    message.reply_channel.send(
        {
            'text': json.dumps(
                {
                    'message_type': 'stabilize',
                }
            )
        },
        immediately=True
    )

