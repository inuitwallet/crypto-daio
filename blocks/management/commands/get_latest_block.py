import json
import logging

from asgiref.base_layer import BaseChannelLayer
from channels import Channel, Group
from django.core.management import BaseCommand
from django.db import connection
from django.db.models import Max
from django.template.loader import render_to_string
from django.utils import timezone

from blocks.models import Info, Block
from blocks.utils.rpc import send_rpc, get_block_hash

logger = logging.getLogger(__name__)

tz = timezone.get_current_timezone()


class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        Get the latest info from the coin daemon and  
        """
        chain = connection.tenant
        max_height = 0
        for coin in chain.coins.all():
            rpc = send_rpc(
                {
                    'method': 'getinfo',
                    'params': []
                },
                rpc_port=coin.rpc_port
            )
            if not rpc:
                return
            info = Info.objects.create(
                unit=rpc['walletunit'],
                max_height=rpc['blocks'],
                money_supply=rpc['moneysupply'],
                total_parked=rpc.get('totalparked'),
                connections=rpc['connections'],
                difficulty=rpc['difficulty'],
                pay_tx_fee=rpc['paytxfee'],
            )
            logger.info('saved {}'.format(info))
            max_height = info.max_height

        current_highest_block = Block.objects.all().aggregate(
            Max('height')
        ).get(
            'height__max'
        )

        while max_height > current_highest_block:
            current_highest_block += 1
            rpc_hash = send_rpc(
                {
                    'method': 'getblockhash',
                    'params': [current_highest_block]
                }
            )
            block, _ = Block.objects.get_or_create(hash=rpc_hash)

            Group('latest_blocks_list').send(
                {
                    'text': json.dumps(
                        {
                            'block_html': render_to_string(
                                'explorer/fragments/block.html',
                                {
                                    'block': block
                                }
                            )
                        }
                    )
                }
            )




