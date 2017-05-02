import time
from asgiref.base_layer import BaseChannelLayer

from django.core.management import BaseCommand
from django.core.paginator import Paginator

from blocks.models import Block
from django.utils import timezone

import logging

from blocks.utils.channels import send_to_channel

logger = logging.getLogger(__name__)

tz = timezone.get_current_timezone()


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            '--start-height',
            help='The block height to start the parse from',
            dest='start_height',
            default=0
        )
        parser.add_argument(
            '-b',
            '--block',
            help='The block height to validate',
            dest='block',
        )
        parser.add_argument(
            '-l',
            '--limit',
            help='limit the number of blocks to process. useful in combination with -s',
            dest='limit',
            default=None
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
                        'parse_transaction', {
                            'tx_hash': tx.tx_id,
                            'block_hash': block.hash,
                            'tx_index': tx.index
                        }
                    )
                    invalid_txs.append('{}:{}'.format(tx.index, tx.tx_id[:8]))

            if invalid_txs:
                logger.error(
                    'block {} has invalid transactions: {}'.format(
                        block.height,
                        invalid_txs
                    )
                )
                return False

            else:
                return True

        else:
            logger.error('block {} is invalid: {}'.format(block.height, error_message))
            send_to_channel(
                'repair_block', {
                    'block_hash': block.hash,
                    'error_message': error_message,
                }
            )
            return False

    def handle(self, *args, **options):
        """
        Parse the block chain
        """
        if options['block']:
            blocks = Block.objects.filter(height=options['block']).order_by('height')
        else:
            # no block specified so validate all blocks starting from start_height
            blocks = Block.objects.filter(
                height__gte=options['start_height']
            ).order_by(
                'height'
            )

        if options['limit']:
            blocks = blocks[:int(options['limit'])]

        logger.info(
            'validating {} blocks starting from {}'.format(
                blocks.count(),
                options['start_height']
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
                        block.save()
                        continue
                    for tx in block.transactions.all():
                        if not tx.is_valid:
                            if block not in page_invalid_blocks:
                                page_invalid_blocks.append(block)
                            tx.save()

                logger.info(
                    '{} ({} blocks validated with {} '
                    'invalid blocks found this round)'.format(
                        page_invalid_blocks,
                        total_blocks,
                        len(page_invalid_blocks),
                    )
                )
                time.sleep(300)  # sleep to let the channel empty a bit

                invalid_blocks += page_invalid_blocks
        except KeyboardInterrupt:
            pass
        logger.info('{} ({} invalid blocks)'.format(invalid_blocks, len(invalid_blocks)))
