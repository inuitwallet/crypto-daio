import logging

from tenant_schemas.utils import schema_context

from blocks.models import Address, TxOutput

logger = logging.getLogger(__name__)


def parse_address(message):
    with schema_context(message.get("chain")):
        addr = message.get("address")

        if not addr:
            logger.error("no address passed in message")
            return

        try:
            tx_output = TxOutput.objects.get(pk=message.get("tx_output"))
        except TxOutput.DoesNotExist:
            logger.error("tx_output not found: {}".format(message.get("tx_output")))
            return

        address, created = Address.objects.get_or_create(
            address=addr,
        )

        if created:
            address.save()

        tx_output.address = address
        tx_output.save()

        # TODO check the address against the list of addresses to watch


def get_address_balance(message):
    with schema_context(message.get("chain")):
        addr = message.get("address")
