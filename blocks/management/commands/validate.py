import logging
import time

from asgiref.base_layer import BaseChannelLayer
from django.core.management import BaseCommand
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Min
from django.utils import timezone

from blocks.models import Block
from blocks.utils.channels import send_to_channel

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
        parser.add_argument(
            "-t", "--last", help="use the last x blocks", dest="last", default=None
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
        Parse the block chain
        """
        if options["block"]:
            blocks = Block.objects.filter(height=options["block"]).order_by("height")
        else:
            # no block specified so validate all blocks starting from start_height
            blocks = (
                Block.objects.filter(height__gte=options["start_height"])
                .exclude(height__isnull=True)
                .order_by("height")
            )

        if options["last"]:
            blocks = blocks[blocks.count() - int(options["last"]) :]

        if options["limit"]:
            blocks = blocks[: int(options["limit"])]

        logger.info(
            "validating {} blocks starting from {}".format(
                blocks.count(), blocks.aggregate(Min("height"))["height__min"]
            )
        )

        # paginate to speed the initial load up a bit
        paginator = Paginator(blocks, 1000)

        invalid_blocks = []
        total_blocks = 0
        try:
            for page_num in paginator.page_range:
                page_invalid_blocks = []

                for block in paginator.page(page_num):
                    total_blocks += 1

                    if block.height == 0:
                        continue

                    if not block.is_valid:
                        page_invalid_blocks.append(block)
                        self.save_block(block)

                    for tx in block.transactions.all():
                        if not tx.is_valid:
                            if block not in page_invalid_blocks:
                                page_invalid_blocks.append(block)
                            self.save_tx(tx)

                logger.info(
                    "({} blocks validated with {} "
                    "invalid blocks found this round)".format(
                        total_blocks,
                        len(page_invalid_blocks),
                    )
                )
                if len(page_invalid_blocks) > 0:
                    # sleep to let the channel empty a bit
                    # maximum of 600 seconds
                    sleep_time = 10 * len(page_invalid_blocks)
                    time.sleep(sleep_time if sleep_time <= 120 else 120)

                invalid_blocks += page_invalid_blocks
        except KeyboardInterrupt:
            pass
        logger.info("({} invalid blocks)".format(len(invalid_blocks)))
