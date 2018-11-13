import json
import logging
from time import sleep

import datetime
from channels import Group, Channel
from django.core.management import BaseCommand
from django.db import connection
from django.db.models import Max
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.timezone import make_aware

from blocks.models import Info, Block, Peer
from blocks.utils.rpc import send_rpc

logger = logging.getLogger(__name__)

tz = timezone.get_current_timezone()


class Command(BaseCommand):

    @staticmethod
    def get_info(chain):
        max_height = 0
        for coin in chain.coins.all():
            rpc, message = send_rpc(
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

            max_height = info.max_height

        return max_height

    @staticmethod
    def get_peer_info(chain):
        rpc, msg = send_rpc(
            {
                'method': 'getpeerinfo',
                'params': []
            },
            schema_name=chain.schema_name,
        )

        if not rpc:
            return

        for peer_info in rpc:
            address = peer_info.get('addr')

            if not address:
                continue

            address_part = address.split(':')
            last_send = make_aware(
                datetime.datetime.fromtimestamp(peer_info.get('lastsend', 0))
            )
            last_receive = make_aware(
                datetime.datetime.fromtimestamp(peer_info.get('lastrecv', 0))
            )
            connection_time = make_aware(
                datetime.datetime.fromtimestamp(peer_info.get('conntime', 0))
            )

            peer, _ = Peer.objects.update_or_create(
                address=address_part[0],
                defaults={
                    'port': address_part[1],
                    'services': peer_info.get('services'),
                    'last_send': last_send,
                    'last_receive': last_receive,
                    'connection_time': connection_time,
                    'version': peer_info.get('version'),
                    'sub_version': peer_info.get('subver'),
                    'inbound': peer_info.get('inbound'),
                    'release_time': peer_info.get('releasetime'),
                    'height': peer_info.get('height'),
                    'ban_score': peer_info.get('banscore'),
                }
            )

            logger.info('saved peer {}'.format(peer))

    @staticmethod
    def get_highest_blocks(chain, max_height):
        current_highest_block = Block.objects.all().aggregate(
            Max('height')
        ).get(
            'height__max'
        )

        if not current_highest_block:
            current_highest_block = -1

        while max_height > current_highest_block:
            current_highest_block += 1
            rpc_hash, message = send_rpc(
                {
                    'method': 'getblockhash',
                    'params': [current_highest_block]
                },
                schema_name=chain.schema_name
            )
            if rpc_hash:
                block, _ = Block.objects.get_or_create(hash=rpc_hash)
                logger.info('saved block {}'.format(block))

        # give a short amount of time for the block(s) to be saved
        sleep(5)

        top_blocks = Block.objects.exclude(height=None).order_by('-height')[:50]
        index = 0

        for block in top_blocks:
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

    def handle(self, *args, **options):
        """
        Get the latest info from the coin daemon and send the messages to update the UI
        """
        chain = connection.tenant

        max_height = self.get_info(chain)

        self.get_peer_info(chain)

        Channel('display_info').send({'chain': connection.schema_name})

        self.get_highest_blocks(chain, max_height)






