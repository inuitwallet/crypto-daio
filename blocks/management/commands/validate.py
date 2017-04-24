from threading import Thread

from channels import Channel
from django.core.management import BaseCommand

from blocks.consumers.parse_transaction import parse_transaction
from blocks.models import Block
from django.utils import timezone

import logging

from blocks.utils.rpc import send_rpc

logger = logging.getLogger('daio')

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
                block_hash = block.hash
                block.delete()
                Channel('parse_block').send({'block_hash': block_hash})
            return False
        for tx in block.transactions.all().order_by('index'):
            tx_valid, tx_message = tx.validate()
            if not tx_valid:
                logger.error('tx {} is invalid: {}'.format(tx.tx_id, tx_message))
                if repair:
                    tx_hash = tx.tx_id
                    tx.delete()
                    Channel('parse_transaction').send({'tx_hash': tx_hash})
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
                logger.info('{} OK'.format(block.height))
            else:
                logger.error('BLOCK {} IS INVALID'.format(block.height))







