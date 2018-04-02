import logging

from django.core.management import BaseCommand

from blocks.models import Block

logger = logging.getLogger(__name__)


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
            '-n',
            '--number',
            help='use the last x blocks',
            dest='number',
            default=10000
        )

    def handle(self, *args, **options):
        blocks = Block.objects.filter(
            height__gte=options['start_height']
        ).exclude(
            height__isnull=True
        ).order_by(
            'height'
        )

        blocks = blocks[blocks.count() - int(options['number']):]

        total_shares = 0
        addresses = []

        for block in blocks:
            if not block.solved_by:
                logger.warning('no solved by address for block {}'.format(block.height))
                block.save()
                continue

            if block.solved_by not in addresses:
                logger.info('New Address: {}'.format(block.solved_by.address))
                addresses.append(block.solved_by)
                total_shares += block.solved_by.balance

        logger.info(
            '{} blocks have been solved by {} different addresses'.format(
                blocks.count(),
                len(addresses)
            )
        )
        logger.info('using a total of {} Voting Shares'.format(total_shares))
