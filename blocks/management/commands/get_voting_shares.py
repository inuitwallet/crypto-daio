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

        profile_links = {}
        linked_profiles = []

        new_profiles = {}

        profile_index = 1

        for profile in voting_profiles:
            # format profiles to the preferred format
            new_profiles[profile_index] = {
                'votes': [profile],
                'number_of_blocks': voting_profiles[profile]['number_of_blocks'],
                'addresses': voting_profiles[profile]['addresses']
            }

            links = {}
            # get the linked profiles by examining the addresses
            for address in new_profiles[profile_index]['addresses']:
                links = self.check_match(voting_profiles, profile, profile_index, address, links)

            # generate the links
            for link in links:
                if links[link] > 0:
                    parent_profile = min(profile_index, link)
                    linked_profile = max(profile_index, link)

                    if parent_profile in linked_profiles:
                        continue

                    if parent_profile not in profile_links:
                        profile_links[parent_profile] = []

                    if linked_profile not in profile_links[parent_profile]:
                        print('{} links to {}'.format(parent_profile, linked_profile))
                        profile_links[parent_profile].append(linked_profile)

                        linked_profiles.append(linked_profile)

            profile_index += 1

        # these are all the profiles that appear in the linked lists
        linked_profiles += profile_links.keys()

        # merge the profiles
        merged_profiles = {}

        processed_profiles = []

        for id in new_profiles:
            if id in processed_profiles:
                continue

            if id not in linked_profiles:
                merged_profiles[list(new_profiles[id]['addresses'][0].keys())[0]] = new_profiles[id]
                continue

            parent_profile = next(new_profiles[p] for p in new_profiles if int(p) == int(id))

            for link in profile_links[id]:
                linked_profile = next(new_profiles[p] for p in new_profiles if int(p) == int(link))

                merged_addresses = []

                for address in parent_profile['addresses'] + linked_profile['addresses']:
                    if address not in merged_addresses:
                        merged_addresses.append(address)

                parent_profile['addresses'] = merged_addresses
                parent_profile['votes'] += linked_profile['votes']
                parent_profile['number_of_blocks'] += linked_profile['number_of_blocks']

                voting_shares = 0

                for address in merged_addresses:
                    for addr in address:
                        voting_shares += address[addr]

                parent_profile['voting_shares'] = voting_shares

                processed_profiles.append(link)

            merged_profiles[list(parent_profile['addresses'][0].keys())[0]] = parent_profile

            processed_profiles.append(id)

        json.dump(merged_profiles, open('merged_profiles.json', 'w+'), indent=2)

        # generate a chart
        x_labels = []
        num_addresses = []
        num_shares = []
        num_blocks = []

        for profile in merged_profiles:
            x_labels.append(profile)
            num_addresses.append(len(merged_profiles[profile]['addresses']))
            num_shares.append(merged_profiles[profile]['voting_shares'] / 10000)
            num_blocks.append(merged_profiles[profile]['number_of_blocks'])

        line_chart = pygal.Bar(legend_at_bottom=True, x_title='Voting Profile')
        line_chart.title = 'Voting share distribution over {} blocks as of Block {}'.format(
            options['number'],
            options['start_height']
        )
        line_chart.x_labels = x_labels
        line_chart.add('Number of Addresses', num_addresses)
        line_chart.add('Total Number of Shares', num_shares, secondary=True)
        line_chart.add('Number of Solved Blocks', num_blocks)
        line_chart.render_to_file('chart.svg')

        # dump the output
        json.dump(voting_profiles, open('voting_profiles.json', 'w+'), indent=2)

    @staticmethod
    def check_match(profiles, own_profile, profile_id, search_address, links=None):
        if links is None:
            links = {}

        for profile in profiles:
            if profile == own_profile:
                continue

            if profile_id not in links:
                links[profile_id] = 0

            for address in profiles[profile]['addresses']:
                if address == search_address:
                    links[profile_id] += 1

        return links
