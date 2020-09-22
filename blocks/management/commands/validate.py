import logging
import time

from channels import Channel
from django.core.management import BaseCommand
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Min
from django.utils import timezone

from blocks.models import Block

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
            "-b", "--block", help="The block height to validate", dest="block",
        )
        parser.add_argument(
            "-l",
            "--limit",
            help="limit the number of blocks to process. useful in combination with -s",
            dest="limit",
            default=None,
        )
        parser.add_argument(
            "-la", "--last", help="use the last x blocks", dest="last", default=None
        )

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
                        block.validate_block_height()
                        new_block = block.set_existing_block_height_if_found()

                        if new_block:
                            block = new_block

                        block.check_validity()

                    for tx in block.transactions.all():
                        if not tx.is_valid:
                            if block not in page_invalid_blocks:
                                page_invalid_blocks.append(block)
                            Channel("repair_transaction").send(
                                {
                                    "chain": connection.tenant.schema_name,
                                    "tx_id": tx.tx_id,
                                }
                            )

                logger.info(
                    f"({total_blocks} blocks validated with {len(page_invalid_blocks)} invalid blocks found this round)"
                )

                if len(page_invalid_blocks) > 0:
                    # sleep to let the channel empty a bit
                    # maximum of 600 seconds
                    sleep_time = 10 * len(page_invalid_blocks)
                    time.sleep(sleep_time if sleep_time <= 600 else 600)

                invalid_blocks += page_invalid_blocks

        except KeyboardInterrupt:
            pass

        logger.info("({} invalid blocks)".format(len(invalid_blocks)))
