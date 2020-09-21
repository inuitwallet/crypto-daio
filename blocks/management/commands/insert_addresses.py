import logging
import time

from asgiref.base_layer import BaseChannelLayer
from django.core.management import BaseCommand
from django.core.paginator import Paginator
from django.db import connection
from django.utils import timezone

from blocks.models import Address, Block, Transaction, TxOutput
from blocks.utils.channels import send_to_channel
from blocks.utils.rpc import send_rpc

logger = logging.getLogger(__name__)

tz = timezone.get_current_timezone()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-s",
            "--start-height",
            help="The block height to start the parse from",
            dest="start_height",
            default=0,
        )
        parser.add_argument(
            "-b",
            "--block",
            help="The block height to validate",
            dest="block",
        )
        parser.add_argument(
            "-l",
            "--limit",
            help="limit the number of blocks to process. useful in combination with -s",
            dest="limit",
            default=None,
        )

    @staticmethod
    def validate_block(block):
        if block.height == 0:
            # genesis block is ok
            return True

        valid, error_message = block.validate()

        if valid:
            invalid_txs = []

            for tx in block.transactions.all():
                if not tx.is_valid:
                    send_to_channel(
                        "parse_transaction",
                        {
                            "chain": connection.tenant.schema_name,
                            "tx_hash": tx.tx_id,
                            "block_hash": block.hash,
                            "tx_index": tx.index,
                        },
                    )
                    invalid_txs.append("{}:{}".format(tx.index, tx.tx_id[:8]))

            if invalid_txs:
                logger.error(
                    "block {} has invalid transactions: {}".format(
                        block.height, invalid_txs
                    )
                )
                return False

            else:
                return True

        else:
            logger.error("block {} is invalid: {}".format(block.height, error_message))
            send_to_channel(
                "repair_block",
                {
                    "chain": connection.tenant.schema_name,
                    "block_hash": block.hash,
                    "error_message": error_message,
                },
            )
            return False

    def save_block(self, block, retry=1):
        try:
            block.save()
        except BaseChannelLayer.ChannelFull:
            logger.warning("channel full. sleeping")
            time.sleep(60 * retry)
            self.save_block(block, retry + 1)

    def save_tx(self, tx, retry=1):
        try:
            tx.save()
        except BaseChannelLayer.ChannelFull:
            logger.warning("channel full. sleeping")
            time.sleep(60 * retry)
            self.save_tx(tx, retry + 1)

    def handle(self, *args, **options):
        """
        get the raw block
        """
        if options["block"]:
            blocks = Block.objects.filter(height=options["block"]).order_by("height")
        else:
            # no block specified so validate all blocks starting from start_height
            blocks = Block.objects.filter(height__gte=options["start_height"]).order_by(
                "height"
            )

        if options["limit"]:
            blocks = blocks[: int(options["limit"])]

        logger.info("fetching raw blocks")

        # paginate to speed the initial load up a bit
        paginator = Paginator(blocks, 1000)

        for page_num in paginator.page_range:
            logger.info("parsing page {}".format(page_num))
            for block in paginator.page(page_num):
                if block.height == 0:
                    continue

                # get the raw rpc block
                rpc_block, msg = send_rpc(
                    {"method": "getblock", "params": [block.hash, True, True]},
                    schema_name=connection.schema_name,
                )

                for tx in rpc_block.get("tx", []):
                    try:
                        block_tx = block.transactions.get(tx_id=tx.get("txid"))
                    except Transaction.DoesNotExist:
                        logger.warning(
                            "transaction not found {}".format(tx.get("txid")[:8])
                        )
                        block.save()
                        continue
                    for tout in tx.get("vout", []):
                        try:
                            block_tx_out = block_tx.outputs.get(index=tout.get("n"))
                        except TxOutput.DoesNotExist:
                            logger.warning("output not found: {}".format(tout.get("n")))
                            block_tx.save()
                            continue
                        script = tout.get("scriptPubKey")
                        if not script:
                            continue
                        addresses = script.get("addresses")
                        if not addresses:
                            continue
                        address = addresses[0]
                        address_object, _ = Address.objects.get_or_create(
                            address=address
                        )
                        if block_tx_out.address == address_object:
                            continue
                        block_tx_out.address = address_object
                        block_tx_out.save()
                        logger.info("added {} to {}".format(address, block_tx_out))

                    # check the tx is valid
                    valid, message = block_tx.validate()
                    if not valid:
                        logger.warning(
                            "{} is still invalid: {}".format(block_tx, message)
                        )
                        block_tx.save()

                # check the block is valid
                valid, message = block.validate()
                if not valid:
                    logger.warning("{} is still invalid: {}".format(block, message))
                    block.save()
