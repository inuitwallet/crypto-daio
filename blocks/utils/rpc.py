import time

import logging
import requests
import json
from django.conf import settings
from requests import ReadTimeout
from requests.exceptions import ConnectionError


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
            return {'error': True, 'message': result.text, 'data': data}

    except ConnectionError:
        return {'error': True, 'message': 'no connection with daemon'}

    except ReadTimeout:
        return {'error': True, 'message': 'daemon timeout'}


def get_block_hash(height):
    rpc = send_rpc(
        {
            'method': 'getblockhash',
            'params': [int(height)]
        }
    )
    if rpc['error']:
        logger = logging.getLogger('daio')
        logger.error(rpc['error'])
    return rpc['result'] if not rpc['error'] else None
