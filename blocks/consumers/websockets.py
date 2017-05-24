from channels import Group, Channel


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
    if message['path'] == '/latest_blocks_list/':
        Group('latest_blocks_list').add(message.reply_channel)
        Group('update_info').add(message.reply_channel)
        message.reply_channel.send({
            'accept': True
        })
        Channel('display_info').send({'chain': get_schema_from_host(message)})

    if '/block/' in message['path']:
        Group('update_info').add(message.reply_channel)
        message.reply_channel.send({
            'accept': True
        })
        Channel('display_info').send({'chain': get_schema_from_host(message)})


def ws_disconnect(message):
    Group('latest_blocks_list').discard(message.reply_channel)
    Group('update_info').discard(message.reply_channel)
    message.reply_channel.send({
        'close': True
    })
