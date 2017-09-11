import json

from channels import Group, Channel
from tenant_schemas.utils import get_tenant_model, tenant_context

from charts.consumers.tx_browser import recalc_browser
from .ui import (
    get_address_details,
    get_block_transactions,
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
        if message['path'] == '/get_block_transactions/':
            get_block_transactions(message_dict, message)
            return

        if message['path'] == '/get_address_details/':
            get_address_details(message_dict, message)
            return

        if message['path'] == '/tx_browser/':
            recalc_browser(message_dict, message)


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
