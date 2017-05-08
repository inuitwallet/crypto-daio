from channels import Group


def ws_connect(message):
    if message['path'] == '/latest_blocks_list':
        Group('latest_blocks_list').add(message.reply_channel)


def ws_disconnect(message):
    Group('latest_blocks_list').discard(message.reply_channel)
