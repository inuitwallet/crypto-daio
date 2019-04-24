import json
import logging

import pygal
from django.core.management import BaseCommand
from django.core.paginator import Paginator

from blocks.models import Block

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-b',
            '--start-height',
            help='The block height to start the parse from. Parse goes downwards fromm this number',
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
            height__lte=options['start_height']
        ).exclude(
            height__isnull=True
        ).order_by(
            '-height'
        )

        paginator = Paginator(blocks, int(options['number']))

        # get the unique addresses that have solved blocks

        addresses = []
        voting_profiles = {}

        for block in paginator.page(1):
            if not block.solved_by:
                logger.warning('no solved by address for block {}'.format(block.height))
                block.save()
                continue

            if block.solved_by not in addresses:
                logger.info('Address {}'.format(block.solved_by))
                addresses.append(block.solved_by)

            # the block votes should be the same for each client or for different clients attached to the same datafeed
            voting_profile = block.vote

            # we should attach addresses to voting profiles
            voting_profile_string = json.dumps(voting_profile, sort_keys=True)

            if voting_profile_string not in voting_profiles:
                voting_profiles[voting_profile_string] = {'addresses': [], 'number_of_blocks': 0}

            # increment number of blocks
            voting_profiles[voting_profile_string]['number_of_blocks'] += 1

            if block.solved_by_address not in voting_profiles[voting_profile_string]['addresses']:
                voting_profiles[voting_profile_string]['addresses'].append(block.solved_by_address)

        # we can show how many addresses have been voting with how many voting profiles

        logger.info(
            'The last {} blocks have been solved by {} different addresses with {} different voting profiles'.format(
                paginator.per_page,
                len(addresses),
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

        # generate a chart
        profile_index = 1
        x_labels = []
        num_addresses = []
        num_shares = []
        num_blocks = []

        for voting_profile in voting_profiles:
            x_labels.append(profile_index)
            voting_profiles[voting_profile]['profile_index'] = profile_index
            profile_index += 1

            num_addresses.append(len(voting_profiles[voting_profile]['addresses']))
            num_shares.append(voting_profiles[voting_profile]['voting_shares']/10000)
            num_blocks.append(voting_profiles[voting_profile]['number_of_blocks'])

        line_chart = pygal.Bar(legend_at_bottom=True, x_title='Voting Profile', x_label_rotation=45)
        line_chart.title = 'Voting share distribution as of Block {}'.format(options['start_height'])
        line_chart.x_labels = x_labels
        line_chart.add('Number of Addresses', num_addresses)
        line_chart.add('Total Number of Shares', num_shares, secondary=True)
        line_chart.add('Number of Solved Blocks', num_blocks)
        line_chart.render_to_file('chart.svg')

        # dump the output
        json.dump(voting_profiles, open('voting_profiles.json', 'w+'), indent=2)
