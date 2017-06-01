from channels import Group, Channel

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
    if message['path'] == '/latest_blocks_list/':
        Group('{}_latest_blocks_list'.format(schema)).add(message.reply_channel)
        Group('{}_update_info'.format(schema)).add(message.reply_channel)
        message.reply_channel.send({
            'accept': True
        })
        Channel('display_info').send({'chain': schema})

    if '/block/' in message['path']:
        Group('{}_update_info'.format(schema)).add(message.reply_channel)
        message.reply_channel.send({
            'accept': True
        })
        Channel('display_info').send({'chain': schema})


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
