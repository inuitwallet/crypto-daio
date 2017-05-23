from channels import Group, Channel
from django.db import connection


def ws_connect(message):
    if message['path'] == '/latest_blocks_list/':
        Group('latest_blocks_list').add(message.reply_channel)
        Group('update_info').add(message.reply_channel)
        message.reply_channel.send({
            'accept': True
        })
        Channel('display_info').send({'chain': connection.tenant.schema_name})

    if '/block/' in message['path']:
        Group('update_info').add(message.reply_channel)
        message.reply_channel.send({
            'accept': True
        })
        Channel('display_info').send({'chain': connection.tenant.schema_name})


def ws_disconnect(message):
    Group('latest_blocks_list').discard(message.reply_channel)
    Group('update_info').discard(message.reply_channel)
    message.reply_channel.send({
        'close': True
    })
