import time
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

                    block_tx = block.transactions.all().values_list('tx_id', flat=True)

                    # add missing transactions
                    for tx in list(set(transactions) - set(block_tx)):
                        logger.info('adding missing tx')
                        Channel('parse_transaction').send(
                            {
                                'tx_hash': tx,
                                'tx_index': transactions.index(tx),
                                'block_hash': block.hash
                            }
                        )

                    for tx in block.transactions.all():
                        # remove additional transactions
                        if tx.tx_id not in transactions:
                            logger.error(
                                'tx {} does not belong to block {}'.format(
                                    tx.tx_id,
                                    block.height
                                )
                            )
                            tx.delete()
                else:
                    block_hash = block.hash
                    block.delete()
                    Channel('parse_block').send(
                        {'block_hash': block_hash, 'no_parse': True}
                    )

            return False

        tx_all_valid = True

        for tx in block.transactions.all().order_by('index'):
            tx_valid, tx_message = tx.validate()

            if not tx_valid:
                tx_all_valid = False
                logger.error('tx {} is invalid: {}'.format(tx.tx_id, tx_message))

                if repair:
                    Channel('parse_transaction').send(
                        {'tx_hash': tx.tx_id, 'block_hash': block.hash}
                    )

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
