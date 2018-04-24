def get_host(message):
    for header in message['headers']:
        if header[0] == b'host':
            return header[1].decode('utf-8')
    return ''
