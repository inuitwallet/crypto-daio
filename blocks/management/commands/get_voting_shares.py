import json
import logging

from django.core.management import BaseCommand
from django.core.paginator import Paginator

from blocks.models import Block

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            '--start-height',
            help='The block height to start the parse from',
            dest='start_height',
            default=0
        )
        parser.add_argument(
            '-n',
            '--number',
            help='use the last x blocks',
            dest='number',
            default=10000
        )

    def handle(self, *args, **options):
        blocks = Block.objects.filter(
            height__gte=options['start_height']
        ).exclude(
            height__isnull=True
        ).order_by(
            '-height'
        )

        paginator = Paginator(blocks, int(options['number']))

        # get the unique addresses that have solved blocks

        addresses = {}
        voting_profiles = {}

        for block in paginator.page(1):
            if not block.solved_by:
                logger.warning('no solved by address for block {}'.format(block.height))
                block.save()
                continue

            if block.solved_by not in addresses:
                logger.info('New Address: {}'.format(block.solved_by))
                addresses[block.solved_by] = {'voting_profiles': []}

            # the block votes should be the same for each client
            voting_profile = block.vote

            # we want to be able to attach voting profiles to addresses
            if voting_profile not in addresses[block.solved_by]['voting_profiles']:
                addresses[block.solved_by]['voting_profiles'].append(voting_profile)

            # we should also attach addresses to voting profiles
            voting_profile_string = json.dumps(voting_profile, sort_keys=True)

            if voting_profile_string not in voting_profiles:
                voting_profiles[voting_profile_string] = {'addresses': []}

            if block.solved_by_address not in voting_profiles[voting_profile_string]['addresses']:
                voting_profiles[voting_profile_string]['addresses'].append(block.solved_by_address)

        # we can show how many addresses have been voting with how many voting profiles

        logger.info(
            '{} blocks have been solved by {} different addresses with {} different voting profiles'.format(
                paginator.per_page,
                len(addresses.keys()),
                len(voting_profiles.keys())
            )
        )

        # we can now go through and calculate how many shares are voting for each profile
        for voting_profile in voting_profiles:
            logger.info('Calculating share total for {}'.format(voting_profile))
            total_shares = 0
            addresses = []

            for address in voting_profiles[voting_profile]['addresses']:
                balance = address.balance
                total_shares += balance
                addresses.append({address.address : balance})

            voting_profiles[voting_profile]['voting_shares'] = total_shares
            voting_profiles[voting_profile]['addresses'] = addresses

        json.dump(addresses, open('voting_addresses.json', 'w+'), sort_keys=True, indent=2)
        json.dump(voting_profiles, open('voting_profiles.json', 'w+'), sort_keys=True, indent=2)
        # logger.info('using a total of {} Voting Shares'.format(total_shares))
