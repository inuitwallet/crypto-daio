from threading import Thread

from channels import Channel
from django.core.management import BaseCommand

from blocks.consumers.parse_block import parse_block
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
        if block.height == 0:
            return True

        valid, message = block.validate()
        if not valid:
            logger.error('block {} is invalid: {}'.format(block.height, message))

            if repair:
                if message == 'merkle root incorrect':
                    rpc = send_rpc(
                        {
                            'method': 'getblock',
                            'params': [block.hash]
                        }
                    )

                    if rpc['error']:
                        logger.error('rpc error: {}'.format(rpc['error']))
                        return
                    transactions = rpc['result'].get('tx', [])

                    if len(transactions) != block.transactions.all().count():
                        logger.error('missing transactions')
                        tx_index = 0

                        for tx in transactions:
                            tx_thread = Thread(
                                target=parse_transaction,
                                kwargs={
                                    'message': {
                                        'tx_hash': tx,
                                        'tx_index': tx_index,
                                        'block_hash': block.hash
                                    }
                                }
                            )
                            tx_thread.start()
                            tx_index += 1
                else:
                    block_hash = block.hash
                    block.delete()
                    parse_block({'block_hash': block_hash})

            return False

        tx_all_valid = True

        for tx in block.transactions.all().order_by('index'):
            tx_valid, tx_message = tx.validate()

            if not tx_valid:
                tx_all_valid = False
                logger.error('tx {} is invalid: {}'.format(tx.tx_id, tx_message))

                if repair:
                    tx_hash = tx.tx_id
                    tx.delete()
                    parse_transaction({'tx_hash': tx_hash. 'block_hash': block.hash})

        return tx_all_valid

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







