import logging

from django.core.management import BaseCommand
from django.core.paginator import Paginator
from django.db import connection

from blocks.models import Block
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
        chain = connection.tenant

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
            'getting vote data for {} blocks starting from {}'.format(
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
                    rpc_block = send_rpc(
                        {
                            'method': 'getblock',
                            'params': [block.hash, True, True]
                        },
                        schema_name=chain.schema_name
                    )

                    if not rpc_block:
                        logger.warning('No data for {}'.format(block))

                    # save the votes
                    block.parse_rpc_votes(rpc_block.get('vote', {}))

                    # save active park rates
                    block.parse_rpc_parkrates(rpc_block.get('parkrates', []))

                logger.info('Got vote data for {} blocks'.format(total_blocks))

        except KeyboardInterrupt:
            pass

        logger.info('Finished')
