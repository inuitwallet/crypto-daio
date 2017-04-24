from channels import Channel
from django.core.management import BaseCommand

from django.utils import timezone

from blocks.utils.rpc import get_block_hash
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

    def handle(self, *args, **options):
        """
        Parse the block chain
        """
        start_hash = get_block_hash(options['start_height'])
        if not start_hash:
            logger.error('could not get start hash. check rpc connection')
            return
        logger.info(
            'starting block chain parse at height {} with block {}'.format(
                options['start_height'],
                start_hash
            )
        )
        # send the hash to the channel for parsing a block
        Channel('parse_block').send({'block_hash': start_hash})




