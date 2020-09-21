import json
import logging
import time

import requests
from django.conf import settings
from requests import ReadTimeout
from requests.exceptions import ConnectionError

from daio.models import Chain

logger = logging.getLogger(__name__)


def send_rpc(data, schema_name, rpc_port=None, retry=0):
    """
    Return a connection to the nud  rpc  interface
    """
    if retry == 3:
        logger.error("3 retries have failed")
        return False, "3 retries have failed"

    chain = Chain.objects.get(schema_name=schema_name)

    # check that the rpc connection is active
    if not chain.rpc_active:
        if data.get("method") in settings.RPC_ALWAYS_LIST:
            # if the method should be allowed, allow it
            pass
        else:
            # otherwise quit early
            return False, "Daemon not active"

    data["jsonrpc"] = "2.0"
    data["id"] = int(time.time())
    rpc_url = "http://{}:{}@{}:{}".format(
        chain.rpc_user,
        chain.rpc_password,
        chain.rpc_host,
        chain.rpc_port if not rpc_port else rpc_port,
    )
    headers = {"Content-Type": "applications/json"}
    try:
        response = requests.post(
            url=rpc_url, headers=headers, data=json.dumps(data), timeout=60,
        )

        try:
            result = response.json()
            error = result.get("error", None)
            if error:
                logger.error("rpc error sending {}: {}".format(data, error))
                return False, error
            return result.get("result"), "success"

        except ValueError:
            logger.error("rpc error sending {}: {}".format(data, response.text))
            return False, response.text

    except ConnectionError:
        logger.error(
            "rpc error sending {}: {}".format(data, "no connection with daemon")
        )
        return False, "no connection with daemon"

    except ReadTimeout:
        logger.warning("rpc error sending {}: {}".format(data, "daemon timeout"))
        send_rpc(data, schema_name=schema_name, retry=retry + 1)
        return False, "daemon timeout"


def get_block_hash(height, schema_name):
    rpc, msg = send_rpc(
        {"method": "getblockhash", "params": [int(height)]}, schema_name=schema_name
    )
    return rpc
