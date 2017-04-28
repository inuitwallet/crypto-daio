import time
from asgiref.base_layer import BaseChannelLayer

from channels import Channel
from django.core.management import BaseCommand
from django.core.paginator import Paginator

from blocks.models import Block
from django.utils import timezone

import logging

from blocks.utils.rpc import send_rpc

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
        parser.add_argument(
            '-r',
            '--repair',
            help='repair any invalidity found',
            dest='repair',
            action='store_true',
            default=False
        )

    @staticmethod
    def validate_transactions(block, repair):
        tx_all_valid = True

        for tx in block.transactions.all():
            tx_valid, tx_message = tx.validate()

            if not tx_valid:
                tx_all_valid = False
                logger.error('tx {} is invalid: {}'.format(tx.tx_id, tx_message))

                if repair:
                    Channel('parse_transaction').send(
                        {'tx_hash': tx.tx_id, 'block_hash': block.hash}
                    )

        return tx_all_valid

    def validate_block(self, block, repair):
        if block.height == 0:
            # genesis block should be assumed to be valid
            return True

        valid, message = block.validate()

        if valid:
            # check the transactions for validity
            return self.validate_transactions(block, repair)
        else:
            logger.error('block {} is invalid: {}'.format(block.height, message))

            if not repair:
                return False
            else:
                # repair the block
                if message == 'merkle root incorrect':
                    rpc = send_rpc(
                        {
                            'method': 'getblock',
                            'params': [block.hash]
                        }
                    )

                    if rpc['error']:
                        logger.error('rpc error: {}'.format(rpc['error']))
                        return False

                    transactions = rpc['result'].get('tx', [])
                    block_tx = block.transactions.all().values_list('tx_id', flat=True)

                    # add missing transactions
                    for tx in list(set(transactions) - set(block_tx)):
                        logger.info('adding missing tx {}'.format(tx))
                        Channel('parse_transaction').send(
                            {
                                'tx_hash': tx,
                                'tx_index': transactions.index(tx),
                                'block_hash': block.hash
                            }
                        )
                        return self.validate_transactions(block, repair)

                    # remove additional transactions
                    for tx in block.transactions.all():
                        if tx.tx_id not in transactions:
                            logger.error(
                                'tx {} does not belong to block {}'.format(
                                    tx.tx_id,
                                    block.height
                                )
                            )
                            tx.delete()
                            return self.validate_transactions(block, repair)

                    # check for duplicate blocks (shouldn't happen as tx_id id unique)
                    if len(list(set(block_tx))) != len(block_tx):
                        logger.error('detected duplicate transaction')
                        block.transactions.all().delete()
                        Channel('parse_block').send(
                            {'block_hash': block.hash, 'no_parse': True}
                        )
                        return False

                else:
                    # all other errors with the block can be solved by re-parsing it
                    Channel('parse_block').send(
                        {'block_hash': block.hash, 'no_parse': True}
                    )

                    return False

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
            except Block.MultipleObjectsReturned:
                logger.error('multiple blocks found at {}'.format(options['block']))
                return

            if self.validate_block(block, options['repair']):
                logger.info('block {} is valid'.format(block.height))
            else:
                logger.error('block {} is invalid'.format(block.height))
            return

        # no block specified so validate all blocks starting from start_height
        blocks = Block.objects.filter(
            height__gte=options['start_height']
        ).order_by(
            'height'
        )

        # paginate to speed the initial load up a bit
        paginator = Paginator(blocks, 1000)
        all_failed = []

        try:
            for page_num in paginator.page_range:
                page_failed = []
                for block in paginator.page(page_num):
                    try:
                        if self.validate_block(block, options['repair']):
                            logger.info('{} OK'.format(block.height))
                        else:
                            logger.error('BLOCK {} IS INVALID'.format(block.height))
                            page_failed.append(block.height)
                    except BaseChannelLayer.ChannelFull:
                        logger.warning('Channel Full. Sleeping for a bit')
                        time.sleep(600)
                        if self.validate_block(block, options['repair']):
                            logger.info('{} OK'.format(block.height))
                        else:
                            logger.error('BLOCK {} IS INVALID'.format(block.height))
                            page_failed.append(block.height)
                all_failed += page_failed
                if len(page_failed) > 0:
                    time.sleep(30)

            logger.info('failed blocks: {}'.format(all_failed))
        except KeyboardInterrupt:
            logger.info('failed blocks: {}'.format(all_failed))
