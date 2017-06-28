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
        addresses = [
            'SYAxC194NgWoAqtGHHZ4GKXU6LT7mgqAq1',
            'Sk2P6oj9VCC8VmCBQaRWK4iwTPbvPcGPsh',
            'SQoAn2DmRPv2ypLcLR1NT3ciqfh8X9qbDQ',
            'SWvFUTiJ2gvmUEGEszvXrdjkn6Uh9ZLbZe',
            'SigAuqtYtigWZ8uVFG7iuLDYv9au9cK49L',
            'SkNDumZBBbx5ygSRd7Nvbg32RoeUERoHrH',
            'Sif3nJuoCZmG5zeahqAYy9jetRLAKfDawC',
            'SYhzKRTPVR6PrqcHqZE1c2d7fWDQLqieba',
            'SNi3zogpVvEGNLyxh6RLNHGU3PMPJBzgEY',
            'SWxjKJ4m3U1X7h22yVDyDuHcdc5hwqxG6g',
            'SYBAJJpoxwUBwyrLMud8B6FLibvZzbTCpi',
            'Sbtxw5pC3y3QpepsWH5iAcra5a53ne6se9',
            'SYxdao1Pyn92trMniivmw3UVLJ9wXbX6kz',
            'SWVRAjpqjW4orkYmADPvQ1adUni9jVK7H8',
            'SUJH1DLG2iLKHY3vXw4V5J1iLphCYAxg6n',
            'ShQ4Rezxs3NKJHcRV6SVL1bvduT2n9P4bi',
            'SewzCfwc36oFTXH9jL1VTUHsEPrJpnB2x2',
            'SYy3bPPGqf3NipGyVRcgcu6rq7RKHoyh5Y',
            'SQ7JRP54iQeLCHR8tujDJsAndKeiuyAqbi',
            'SiyWZ1WCedKRXLg7u8fmVkUtF3JRC9QATv',
            'BJDirPFfohpTRXTiTzw8gfZjV9qy3CRqpM',
        ]

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
        for address in addresses:
            try:
                addr = Address.objects.get(address=address)
            except Address.DoesNotExist:
                logger.error('No address found for {}'.format(address))
                continue

            transactions = addr.transactions
            for transaction in transactions:
                for input in transaction.inputs.all():
                    print(input)
                for output in transaction.outputs.all():
                    print(output)






