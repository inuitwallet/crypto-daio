import json

from channels import Group, Channel
from tenant_schemas.utils import get_tenant_model, tenant_context

from charts.consumers.tx_browser import add_onward_nodes
from blocks.models import Address
from charts.models import UserSocket
from .ui import (
    get_address_balance,
    get_address_details,
    get_block_details,
    get_current_grants,
    get_current_motions
)
from daio.models import Chain


def get_schema_from_host(message):
    host = None
    for header in message['headers']:
        if header[0] == b'host':
            host = str(header[1])
    if not host:
        return ''
    host_parts = host.split('.')
    return host_parts[0].replace('-', '_').replace('b\'', '').lower()


def ws_connect(message):
    schema = get_schema_from_host(message)
    message.reply_channel.send({'accept': True}, immediately=True)
    Group('{}_update_info'.format(schema)).add(message.reply_channel)
    Channel('display_info').send({'chain': schema}, immediately=True)
    if message['path'] == '/latest_blocks_list/':
        Group('{}_latest_blocks_list'.format(schema)).add(message.reply_channel)


def ws_receive(message):
    message_dict = json.loads(message['text'])
    domain_url = message_dict['payload']['host']
    if domain_url == 'explorer.nubits.com':
        domain_url = 'nu.crypto-daio.co.uk'
    tenant = get_tenant_model().objects.get(domain_url=domain_url)
    with tenant_context(tenant):
        if message['path'] == '/get_block_details/':
            get_block_details(message_dict, message)

            return

        if message['path'] == '/get_address_details/':
            try:
                address_object = Address.objects.get(address=message_dict.get('stream'))
                get_address_balance(address_object, message)
                get_address_details(address_object, message)
            except Address.DoesNotExist:
                pass

            return

        if message['path'] == '/tx_browser/':
            if message_dict.get('stream') == 'add_nodes':
                add_onward_nodes(message_dict, message)

            if message_dict.get('stream') == 'stop_nodes':
                try:
                    user_socket = UserSocket.objects.get(
                        reply_channel=message.reply_channel
                    )
                    user_socket.tx_browser_running = False
                    user_socket.save()
                except UserSocket.DoesNotExist:
                    pass

            return

        if message['path'] == '/get_current_grants/':
            get_current_grants(message)
            return

        if message['path'] == '/get_current_motions/':
            get_current_motions(message)
            return


def ws_disconnect(message):
    for chain in Chain.objects.all():
        Group(
            '{}_latest_blocks_list'.format(chain.schema_name)
        ).discard(message.reply_channel)
        Group(
            '{}_update_info'.format(chain.schema_name)
        ).discard(message.reply_channel)
    message.reply_channel.send(
        {
            'close': True
        },
        immediately=True
    )
