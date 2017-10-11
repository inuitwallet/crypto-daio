import logging

from django.core.management import BaseCommand

from blocks.models import Address

blocked_addresses = [
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
    'BJDirPFfohpTRXTiTzw8gfZjV9qy3CRqpM',
]

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        total_balance = 0
        for address in blocked_addresses:
            try:
                blocked_address = Address.objects.get(address=address)
            except Address.DoesNotExist:
                logger.warning('{} does not exist'.format(address))
                continue

            balance = blocked_address.balance
            logger.info('{} has a balance of {}'.format(address, balance))
            total_balance += balance

        logger.info('total balance for all addresses is {}'.format(total_balance))
