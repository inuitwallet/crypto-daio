import logging

from django.core.management import BaseCommand

from blocks.models import Block, Transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        # delete blocks with no height
        deleted_blocks = Block.objects.filter(height__isnull=True).delete()
        logger.info("Removed Blocks: {}".format(deleted_blocks))

        # delete transactions with no block
        deleted_transactions = Transaction.objects.filter(block__isnull=True).delete()
        logger.info("Removed Txs: {}".format(deleted_transactions))
