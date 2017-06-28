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
from blocks.models import Address

logger = logging.getLogger(__name__)

tz = timezone.get_current_timezone()


class Command(BaseCommand):

    def handle(self, *args, **options):
        """
        investigate the losses by tracking activity through the blockchain
        :param args:
        :param options:
        :return:
        """
        compromised_addresses = [
            'SSajkovCPXwdw46nyJ7vpTDkwtRZJzyY2z',
            'SNf4uyshit1fj8dWKVxHsKTgTrNR61RskY',
            'SQTHenWRCF7tZQb5RQAbf3pVYN3Jq5RET4',
            'ShGVUEJpyZBTgK6V5ZzBorv899R1LP7pqm',
            'SNdbH9sUJ8z33iE8oNBCwCLfwP9tafyZh3',
            'Sb84GHDPxy1dzE4VttDTrLwYLzLw4hEDUV',
            'SUgGG6PYXeoXtrUU85rViuWbxsVczwQX7i',
            'SRcyHX5JE1tprmtUNswHFsgWqwciwkqigk',
            'SMv2C8x41mtkZvv5wNejdqSsBQPPTfPEDj',
            'SQGuknAk53MpBMy9fuX632Kqi8FWoNMQ2v',
            'SYrndApJNq5JrXGu83NQuzb3PHQoaeEwx8',
            'SXQcdc5THvdUAdfmK4NEYQpvqANwz4iBHg',
            'SeTPb7fj6PLn2E4aMa5TbR83Pw6MSs37fM',
        ]

        target_addresses = [
            'SfhbL4Hmkvh8t79wkFEotnGqf64GvvB7HV',
            'Sh5okqoxnFoiCVAJEdzfxzHqSyunriVPmp',
            'SUGfxGPyCgaNg3FjXjcpMwtco1CTNbRSwG',
            'SeSuCVYzdPT1Biw9cfuK4mHYGTeihqY7Cq',
            'SY3mR9hhtN6V4JVG8nf466SMr6Vx2asDSp',
            'SVZ9C4D78Xmca7S4edFoghJB6znVcjBf9s',
            'ST2FF2LybChMcpj5dywaLTG2P4pezvspiJ',
            'SV3ZNwQ9CCDaHFb3BjwviUZzq1sDDycDtH',
            'SMgrPVqXaVfcrFgMFesJZT37b4VBohWxqr',
            'Se3FvyRoshq6zjGbiWLYYAKAJnP3kH4Xvj',
            'SUGCjFktPEdXBquPJdSemuxZFy4AxvbXH4',
            'Sg6aYkT7MP2R6FttKoKAPXqtTw1CHEzkZN',
            'SNQ4BWMpiumVtTEmrW4xAYfbJFhxdHZBxz',
            'STWUi4iSgpAwJrycwrurn1j7DTS18w7ZDN',
            'SickUboc7GTJK7TxF7vfYnunFLk81NLr9p',
            'SeDCHvv8VQx1dsZFBJRJEmcjTTEvKU1QxH',
            'Sf8xcBTzjxHV7518BE3xuQqHTzTr9BKTfr',
            'SNbMQJnVDymEvE2vpyHfqdKzedjekXsGQi',
            'ScDYXcJc4TShVLcKBmgRq9rz6ZvqfLrAkv',
        ]
        for address in compromised_addresses:
            try:
                addr = Address.objects.get(address=address)
            except Address.DoesNotExist:
                logger.error('{} does not exist'.format(address))
                continue
            
            for tx in addr.transactions:
                tx.block.save()
                for out_addr in tx.address_outputs:
                    if out_addr in target_addresses:
                        logger.info(
                            '{} sent {} to {} on {}'.format(
                                address,
                                tx.address_outputs['out_addr'],
                                out_addr,
                                tx.time
                            )
                        )
