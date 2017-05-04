import logging

from django.core.management import BaseCommand
from django.db import connection
from django.utils import timezone

from blocks.utils.rpc import send_rpc

logger = logging.getLogger(__name__)

tz = timezone.get_current_timezone()


class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        Get the latest info from the coin daemon and  
        """
        chain = connection.tenant
        for coin in chain.coins.all():
            rpc = send_rpc(
                {
                    'method': 'getinfo',
                    'params': []
                },
                rpc_port=coin.rpc_port
            )
            logger.info('{} = {}'.format(coin.unit_code, rpc['walletunit']))
