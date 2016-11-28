import time
from threading import Thread

import requests
import json
from django.conf import settings
from requests import ReadTimeout
from requests.exceptions import ConnectionError

from blocks.utils.block_parser import save_block


def send_rpc(data):
    """
    Return a connection to the nud  rpc  interface
    """
    data['jsonrpc'] = "2.0"
    data['id'] = int(time.time())
    rpc_url = 'http://{}:{}@{}:{}'.format(
        settings.RPC_USER,
        settings.RPC_PASSWORD,
        settings.RPC_HOST,
        settings.RPC_PORT,
    )
    headers = {'Content-Type': 'applications/json'}
    try:
        result = requests.post(
            url=rpc_url,
            headers=headers,
            data=json.dumps(data),
            timeout=600,
        )

        try:
            return result.json()
        except ValueError:
            return {'error': True, 'message': result.text}

    except ConnectionError:
        return {'error': True, 'message': 'no connection with daemon'}

    except ReadTimeout:
        return {'error': True, 'message': 'daemon timeout'}


def trigger_block_parse(block_hash):
    rpc = send_rpc(
        {
            'method': 'getblock',
            'params': [block_hash]
        }
    )
    got_block = rpc['result'] if not rpc['error'] else None
    if got_block:
        save = Thread(
            target=save_block,
            kwargs={
                'block': got_block,
            },
            name=block_hash
        )
        save.daemon = True
        save.start()
