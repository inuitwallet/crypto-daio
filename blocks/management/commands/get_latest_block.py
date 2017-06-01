import json
import logging
from time import sleep

from channels import Group, Channel
from django.core.management import BaseCommand
from django.db import connection
from django.db.models import Max
from django.template.loader import render_to_string
from django.utils import timezone

from blocks.models import Info, Block
from blocks.utils.rpc import send_rpc

logger = logging.getLogger(__name__)

tz = timezone.get_current_timezone()


class Command(BaseCommand):

    @staticmethod
    def update_info(info_id, value):
        Group('{}_update_info'.format(connection.schema_name)).send(
            {
                'text': json.dumps(
                    {
                        'message_type': 'update_info',
                        'id': info_id,
                        'value': value
                    }
                )
            }
        )

    def handle(self, *args, **options):
        """
        Get the latest info from the coin daemon and send the messages to update the UI
        """
        chain = connection.tenant
        max_height = connections = 0
        for coin in chain.coins.all():
            rpc = send_rpc(
                {
                    'method': 'getinfo',
                    'params': []
                },
                schema_name=chain.schema_name,
                rpc_port=coin.rpc_port
            )

            if not rpc:
                continue

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

        Channel('display_info').send({'chain': connection.schema_name})

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
                },
                schema_name=chain.schema_name
            )
            block, _ = Block.objects.get_or_create(hash=rpc_hash)

        # give a short amount of time for the block to be saved
        sleep(5)

        top_blocks = Block.objects.exclude(height=None).order_by('-height')[:50]
        index = 0

        for block in top_blocks:
            block.save()
            Group('{}_latest_blocks_list'.format(connection.schema_name)).send(
                {
                    'text': json.dumps(
                        {
                            'message_type': 'update_block',
                            'index': index,
                            'block_html': render_to_string(
                                'explorer/fragments/block.html',
                                {
                                    'block': block
                                }
                            ),
                            'block_is_valid': block.is_valid
                        }
                    )
                }
            )
            index += 1




