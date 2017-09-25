import json
import logging

from blocks.models import Transaction, TxInput, Block, Address
from charts.models import UserSocket

logger = logging.getLogger(__name__)


def check_continue(message):
    # get the user_socket object and check if we should continue
    try:
        user_socket = UserSocket.objects.get(reply_channel=message.reply_channel)
        if not user_socket.tx_browser_running:
            send_console(message, 'Stopping!')
            return False
    except UserSocket.DoesNotExist:
        send_console(message, 'Stopping!')
        return False

    return True


def check_block_already_scanned(message, block):
    try:
        user_socket = UserSocket.objects.get(reply_channel=message.reply_channel)
    except UserSocket.DoesNotExist:
        user_socket = UserSocket.objects.create(reply_channel=message.reply_channel)
        user_socket.tx_browser_running = True
        user_socket.save()

    if block in user_socket.blocks.all():
        return False
    user_socket.blocks.add(block)
    return True


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


def send_console(message, text):
    if not check_continue(message):
        return
    message.reply_channel.send(
        {
            'text': json.dumps(
                {
                    'message_type': 'console',
                    'text': text
                }
            )
        },
        immediately=True
    )


def send_block(message, block):
    if not check_continue(message):
        return
    message.reply_channel.send(
        {
            'text': json.dumps(
                {
                    'message_type': 'node',
                    'node': {
                        'id': 'Block_{}'.format(block.height),
                        'shape': 'square',
                        'title': 'Block_{}'.format(block.height),
                        'size': 5
                    }
                }
            )
        },
        immediately=True
    )


def send_address(message, address):
    if not check_continue(message):
        return
    message.reply_channel.send(
        {
            'text': json.dumps(
                {
                    'message_type': 'node',
                    'node': {
                        'id': 'Address_{}'.format(address),
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
    if not check_continue(message):
        return
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
    if not check_continue(message):
        return

    if not check_block_already_scanned(message, block):
        return

    send_console(message, 'Scanning outputs for Block {}'.format(block.height))
    outputs = block.outputs
    unspent = outputs.get('unspent', [])
    spent = outputs.get('spent', [])
    for unspent_address in unspent:
        if not check_continue(message):
            return
        send_console(message, 'Unspent Output {} from {} to {}'.format(
            unspent[unspent_address],
            block.height,
            unspent_address.address
        ))
        send_address(message, unspent_address.address)
        send_edge(
            message,
            'Block_{}'.format(block.height),
            'Address_{}'.format(unspent_address.address),
            unspent[unspent_address],
            '#2cf948'
        )
    for spent_block in spent:
        if not check_continue(message):
            return
        send_console(message, 'Spent output {} from {} to {}'.format(
            spent[spent_block],
            block.height,
            spent_block.height
        ))
        send_block(message, spent_block)
        send_edge(
            message,
            'Block_{}'.format(block.height),
            'Block_{}'.format(spent_block.height),
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

    # get the user_socket object and set us going
    try:
        user_socket = UserSocket.objects.get(reply_channel=message.reply_channel)
    except UserSocket.DoesNotExist:
        user_socket = UserSocket.objects.create(reply_channel=message.reply_channel)

    user_socket.tx_browser_running = True
    user_socket.save()

    node_details = node.get('title').split('_')
    node_type = node_details[0]
    node_value = node_details[1]

    if node_type == 'Address':
        send_console(message, 'Getting onward blocks from {}'.format(node_value))
        for block in yield_address_blocks(node_value):
            if not check_continue(message):
                return
            # we need to see the value of funds that was input from this address
            input_value = 0
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
            send_console(message, 'Direct output from {} of {} to {}'.format(
                node_value,
                input_value,
                block.height
            ))
            send_block(message, block)
            send_edge(
                message=message,
                edge_from='Address_{}'.format(node_value),
                edge_to='Block_{}'.format(block.height),
                edge_value=input_value,
                colour='#00000'
            )
            handle_block(
                message=message,
                block=block,
            )

    send_console(message, 'Finished')
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

