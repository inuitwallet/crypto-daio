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

            Channel('validate_block').send({'block_hash': block.hash})
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
                    Channel('validate_block').send({'block_hash': block.hash})
                except BaseChannelLayer.ChannelFull:
                    logger.warning('Channel Full. Sleeping for a bit')
                    time.sleep(600)
                    Channel('validate_block').send({'block_hash': block.hash})
