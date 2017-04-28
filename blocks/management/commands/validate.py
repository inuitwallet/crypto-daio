import time
from asgiref.base_layer import BaseChannelLayer

from channels import Channel
from django.core.management import BaseCommand
from django.core.paginator import Paginator

from blocks.models import Block
from django.utils import timezone

import logging

logger = logging.getLogger('daio')

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

    @staticmethod
    def validate_block(block):
        valid, error_message = block.validate()

        if valid:
            logger.info('block {} is valid'.format(block.height))
            for tx in block.transactions.all():
                if not tx.is_valid:
                    Channel('parse_transaction').send(
                        {
                            'tx_hash': tx.tx_id,
                            'block_hash': block.hash,
                            'tx_index': tx.index
                        }
                    )
                else:
                    logger.info(
                        'tx {} at block {} is valid'.format(tx.tx_id, block.height)
                    )
        else:
            Channel('repair_block').send(
                {
                    'block_hash': block.hash,
                    'error_message': error_message
                }
            )

    def handle(self, *args, **options):
        """
        Parse the block chain
        """
        if options['block']:
            # just validate the single block specified
            try:
                block = Block.objects.get(height=options['block'])
            except Block.DoesNotExist:
                logger.error('no block found at {}'.format(options['block']))
                return

            self.validate_block(block)
            return

        # no block specified so validate all blocks starting from start_height
        blocks = Block.objects.filter(
            height__gte=options['start_height']
        ).order_by(
            'height'
        )

        # paginate to speed the initial load up a bit
        paginator = Paginator(blocks, 1000)

        for page_num in paginator.page_range:

            for block in paginator.page(page_num):
                try:
                    self.validate_block(block)
                except BaseChannelLayer.ChannelFull:
                    logger.warning('Channel Full. Sleeping for a bit')
                    time.sleep(600)
                    self.validate_block(block)
