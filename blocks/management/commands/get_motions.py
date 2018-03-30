import logging

from django.core.management import BaseCommand
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Sum

from blocks.models import Block, MotionVote
from blocks.utils.rpc import send_rpc

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

    def handle(self, *args, **options):
        if options['block']:
            blocks = Block.objects.filter(height=options['block']).order_by('-height')
        else:
            # no block specified so validate all blocks starting from start_height
            blocks = Block.objects.filter(
                height__gte=options['start_height']
            ).order_by(
                '-height'
            )

        if options['limit']:
            blocks = blocks[:int(options['limit'])]

        logger.info(
            'getting motion votes for {} blocks starting from {}'.format(
                blocks.count(),
                blocks.first().height
            )
        )

        # paginate to speed the initial load up a bit
        paginator = Paginator(blocks, 1000)
        total_blocks = 0

        try:
            for page_num in paginator.page_range:
                for block in paginator.page(page_num):
                    total_blocks += 1
                    # get votes this block
                    block_votes = MotionVote.objects.filter(block=block)

                    for vote in block_votes:

                        votes = MotionVote.objects.filter(
                            hash=vote.hash,
                            block__height__gte=max(block.height - 10000, 0),
                            block__height__lte=block.height
                        )

                        vote.blocks_percentage = (votes.count() / 10000) * 100

                        # calculate the ShareDays Destroyed percentage
                        total_sdd = Block.objects.filter(
                            height__gte=max(block.height - 10000, 0),
                            height__lte=block.height
                        ).aggregate(
                            Sum('coinage_destroyed')
                        )['coinage_destroyed__sum']

                        voted_sdd = votes.aggregate(
                            Sum('block__coinage_destroyed')
                        )['block__coinage_destroyed__sum']

                        vote.sdd_percentage = (voted_sdd / total_sdd) * 100
                        vote.save()
                        logger.info('saved {}'.format(vote))

                logger.info('Got motion vote data for {} blocks'.format(total_blocks))

        except KeyboardInterrupt:
            pass

        logger.info('Finished')
