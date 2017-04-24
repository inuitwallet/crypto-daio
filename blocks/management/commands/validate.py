from channels import Channel
from django.core.management import BaseCommand

from blocks.models import Block
from django.utils import timezone

import logging

logger = logging.getLogger(__name__)

tz = timezone.get_current_timezone()


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '-b',
            '--block',
            help='The block height to validate',
            dest='block',
        )
        parser.add_argument(
            '-r',
            '--repair',
            help='repair any invalidity found',
            dest='repair',
            action='store_true',
            default=False
        )

    @staticmethod
    def validate(block, repair):
        valid, message = block.validate()
        if not valid:
            logger.error('block {} is invalid: {}'.format(block.height, message))
            if repair:
                Channel('parse_block').send({'block_hash': block.hash})
            return False
        for tx in block.transactions.all().order_by('index'):
            tx_valid, tx_message = tx.validate()
            if not tx_valid:
                logger.error('tx {} is invalid: {}'.format(tx.tx_id, tx_message))
                if repair:
                    Channel('parse_transaction').send({'tx_hash': tx.tx_id})
                return False
        return True

    def handle(self, *args, **options):
        """
        Parse the block chain
        """
        if options['block']:
            try:
                block = Block.objects.get(height=options['block'])
            except Block.DoesNotExist:
                logger.error('no block found at {}'.format(options['block']))
                return
            except Block.MultipleObjectsReturned:
                logger.error('multiple blocks found at {}'.format(options['block']))
                return

            if self.validate(block, options['repair']):
                logger.info('block {} is valid'.format(block.height))
            else:
                logger.error('block {} is invalid'.format(block.height))
            return

        for block in Block.objects.all().order_by('height'):
            if self.validate(block, options['repair']):
                logger.info('block {} is valid'.format(block.height))
            else:
                logger.error('BLOCK {} IS INVALID'.format(block.height))







