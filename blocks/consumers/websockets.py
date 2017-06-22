import json

from channels import Group, Channel
from django.template.loader import render_to_string
from tenant_schemas.utils import get_tenant_model, tenant_context

from daio.models import Chain
from blocks.models import Block, Address


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
    message.reply_channel.send({
        'accept': True
    })
    Group('{}_update_info'.format(schema)).add(message.reply_channel)
    Channel('display_info').send({'chain': schema})

    if message['path'] == '/latest_blocks_list/':
        Group('{}_latest_blocks_list'.format(schema)).add(message.reply_channel)


def ws_receive(message):
    message_dict = json.loads(message['text'])
    tenant = get_tenant_model().objects.get(domain_url=message_dict['payload']['host'])
    with tenant_context(tenant):
        if message['path'] == '/get_block_transactions/':
            block_hash = message_dict['stream']
            block = Block.objects.get(hash=block_hash)
            for tx in block.transactions.all():
                message.reply_channel.send({
                    'text': json.dumps(
                        {
                            'html': render_to_string(
                                'explorer/fragments/transaction.html',
                                {
                                    'tx': tx
                                }
                            )
                        }
                    )
                })
            return

        if message['path'] == '/get_address_transactions/':
            address = message_dict['stream']
            address_object = Address.objects.get(address=address)
            for tx in address_object.transactions:
                message.reply_channel.send({
                    'text': json.dumps(
                        {
                            'html': render_to_string(
                                'explorer/fragments/transaction.html',
                                {
                                    'tx': tx
                                }
                            )
                        }
                    )
                })
            return


def ws_disconnect(message):
    for chain in Chain.objects.all():
        Group(
            '{}_latest_blocks_list'.format(chain.schema_name)
        ).discard(message.reply_channel)
        Group(
            '{}_update_info'.format(chain.schema_name)
        ).discard(message.reply_channel)
    message.reply_channel.send({
        'close': True
    })
