from django.core.management import BaseCommand
from django.db import connection

from django.utils import timezone

from blocks.utils.rpc import get_block_hash, send_rpc
import logging

from blocks.models import Block

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
            hash = get_block_hash(height=height, schema_name=chain)
            if not hash:
                continue
            try:
                block = Block.objects.get(hash=hash)
            except Block.DoesNotExist:
                block = Block(hash=hash, height=height)

            block.save(validate=False)

        for block in Block.objects.all():
            block.save()
