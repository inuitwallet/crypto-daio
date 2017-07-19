import logging
import time

from django.core.management import BaseCommand
from django.core.paginator import Paginator
from django.db import connection
from django.utils import timezone

from blocks.models import Block
from blocks.utils.rpc import get_block_hash
from channels import Channel

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
    def check_hash(block_height, block_hash, schema_name):
        check_hash = get_block_hash(block_height, schema_name)
        if check_hash != block_hash:
            logger.error('block at height {} has incorrect hash'.format(block_height))

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

        try:
            for page_num in paginator.page_range:
                for block in paginator.page(page_num):

                    Channel('check_block_hash').send({
                        'block_height': block.height,
                        'block_hash': block.hash,
                        'chain': connection.schema_name
                    })

                time.sleep(10)
                logger.info('checked {} blocks'.format(page_num * 1000))

        except KeyboardInterrupt:
            pass
