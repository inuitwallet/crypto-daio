import json
import logging

from channels import Channel, Group
from tenant_schemas.utils import get_tenant_model, tenant_context

from blocks.models import Address
from daio.models import Chain

from .ui import (
    get_address_balance,
    get_address_details,
    get_block_details,
    get_current_grants,
    get_current_motions,
    get_latest_blocks,
    get_next_blocks,
)

logger = logging.getLogger(__name__)


def get_schema_from_host(message):
    host = None
    for header in message["headers"]:
        if header[0] == b"host":
            host = str(header[1])
    if not host:
        return ""
    host_parts = host.split(".")
    return host_parts[0].replace("-", "_").replace("b'", "").lower()


def ws_connect(message):
    schema = get_schema_from_host(message)
    message.reply_channel.send({"accept": True}, immediately=True)
    Group("{}_update_info".format(schema)).add(message.reply_channel)
    Channel("display_info").send({"chain": schema}, immediately=True)

    if message["path"] == "/latest_blocks_list/":
        Group("{}_latest_blocks_list".format(schema)).add(message.reply_channel)

    if message["path"] == "/latest_blocks/":
        Group("{}_latest_blocks".format(schema)).add(message.reply_channel)


def ws_receive(message):
    message_dict = json.loads(message["text"])
    domain_url = message_dict["payload"]["host"]

    if domain_url == "explorer.nubits.com":
        domain_url = "nu.crypto-daio.co.uk"

    try:
        tenant = get_tenant_model().objects.get(domain_url=domain_url)
    except get_tenant_model().DoesNotExist:
        tenant = get_tenant_model().objects.get(domain_url="nu.crypto-test.co.uk")

    with tenant_context(tenant):
        if message["path"] == "/get_block_details/":
            get_block_details(message_dict, message)

            return

        if message["path"] == "/get_address_details/":
            try:
                address_object = Address.objects.get(address=message_dict.get("stream"))
                get_address_balance(address_object, message)
                get_address_details(address_object, message)
            except Address.DoesNotExist:
                pass

            return

        if message["path"] == "/get_current_grants/":
            get_current_grants(message)
            return

        if message["path"] == "/get_current_motions/":
            get_current_motions(message)
            return

        if message["path"] == "/all_blocks_list/":
            try:
                last_height = int(message_dict["payload"]["last_height"])
            except ValueError:
                return

            get_next_blocks(message, last_height)
            return

        if message["path"] == "/latest_blocks/":
            get_latest_blocks(message)


def ws_disconnect(message):
    for chain in Chain.objects.all():
        Group("{}_latest_blocks_list".format(chain.schema_name)).discard(
            message.reply_channel
        )
        Group("{}_update_info".format(chain.schema_name)).discard(message.reply_channel)
    message.reply_channel.send({"close": True}, immediately=True)
