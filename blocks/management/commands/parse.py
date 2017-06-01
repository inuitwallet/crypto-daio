from django.core.management import BaseCommand
from django.db import connection

from django.utils import timezone

from blocks.utils.channels import send_to_channel
from blocks.utils.rpc import get_block_hash, send_rpc
import logging

from models import Block

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

    def handle(self, *args, **options):
        """
        Parse the block chain
        """
        chain = connection.tenant
        rpc = send_rpc(
            {
                'method': 'getinfo',
                'params': []
            },
            schema_name=chain.schema_name
        )

        if not rpc:
            logger.error('no RPC connection')
            return

        max_height = rpc['blocks']

        for height in range(max_height):
            rpc = send_rpc(
                {
                    'method': 'getblockhash',
                    'params': [height]
                },
                schema_name=chain
            )
            if not rpc:
                continue
            try:
                block = Block.objects.get(hash=rpc)
            except Block.DoesNotExist:
                block = Block(hash=rpc, height=height)

            block.save(validate=False)

        for block in Block.objects.all():
            block.save()
