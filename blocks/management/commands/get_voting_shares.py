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
            "-b",
            "--start-height",
            help="The block height to start the parse from. Parse goes downwards fromm this number",
            dest="start_height",
            default=0,
        )
        parser.add_argument(
            "-n", "--number", help="use the last x blocks", dest="number", default=10000
        )

    def handle(self, *args, **options):
        blocks = (
            Block.objects.filter(height__lte=options["start_height"])
            .exclude(height__isnull=True)
            .order_by("-height")
        )

        paginator = Paginator(blocks, int(options["number"]))

        # 1) Attach addresses to voting profiles with number of blocks solved

        addresses = []
        voting_profiles = {}

        for block in paginator.page(1):
            solved_by = block.solved_by_address

            if not solved_by:
                logger.warning("no solved by address for block {}".format(block.height))
                block.save()
                continue

            if solved_by not in addresses:
                logger.info("Address {}".format(solved_by))
                addresses.append(solved_by)

            # the block votes should be the same for each client or for different clients attached to the same data feed
            voting_profile = block.vote

            # we should attach addresses to voting profiles
            voting_profile_string = json.dumps(voting_profile, sort_keys=True)

            if voting_profile_string not in voting_profiles:
                voting_profiles[voting_profile_string] = {
                    "addresses": [],
                    "number_of_blocks": 0,
                }

            # increment number of blocks
            voting_profiles[voting_profile_string]["number_of_blocks"] += 1

            if solved_by not in voting_profiles[voting_profile_string]["addresses"]:
                voting_profiles[voting_profile_string]["addresses"].append(solved_by)

        # we can show how many addresses have been voting with how many voting profiles
        logger.info(
            "The last {} blocks have been solved by {} different addresses with {} different voting profiles".format(
                paginator.per_page, len(addresses), len(voting_profiles.keys())
            )
        )

        # we can now go through and calculate how many shares are voting for each profile
        # first we give each profile an index number
        profile_index = 1

        for profile in voting_profiles:
            voting_profiles[profile]["id"] = profile_index
            profile_index += 1

        # calculate the links between voting profiles based on shared addresses
        # now we can se which shared addresses there are
        profile_links = {}
        linked_profiles = []
        new_profiles = {}

        for profile in voting_profiles:
            profile_id = voting_profiles[profile]["id"]
            # format profiles to the preferred format
            new_profiles[profile_id] = {
                "votes": [profile],
                "number_of_blocks": voting_profiles[profile]["number_of_blocks"],
                "addresses": voting_profiles[profile]["addresses"],
            }

            links = {}
            # get the linked profiles by examining the addresses
            for address in new_profiles[profile_id]["addresses"]:
                links = self.check_match(voting_profiles, profile, address, links)

            # generate the links
            for link in links:
                if links[link] > 0:
                    parent_profile = min(profile_id, link)
                    linked_profile = max(profile_id, link)

                    if parent_profile in linked_profiles:
                        continue

                    if parent_profile not in profile_links:
                        profile_links[parent_profile] = []

                    if linked_profile not in profile_links[parent_profile]:
                        logger.info(
                            "{} has {} links to {} of {} addresses".format(
                                parent_profile,
                                links[link],
                                linked_profile,
                                len(new_profiles[parent_profile]["addresses"]),
                            )
                        )
                        profile_links[parent_profile].append(linked_profile)

                        linked_profiles.append(linked_profile)

        # these are all the profiles that appear in the linked lists
        linked_profiles += profile_links.keys()

        # merge the profiles
        merged_profiles = {}

        processed_profiles = []

        for profile_id in new_profiles:
            if profile_id in processed_profiles:
                continue

            if profile_id not in linked_profiles:
                # no merging needed as profile isn't linked to anything
                primary_address = self.get_primary_address(
                    new_profiles[profile_id]["addresses"]
                )
                merged_profiles[primary_address] = new_profiles[profile_id]
                continue

            parent_profile = next(
                new_profiles[p] for p in new_profiles if int(p) == int(profile_id)
            )

            for link in profile_links[profile_id]:
                linked_profile = next(
                    new_profiles[p] for p in new_profiles if int(p) == int(link)
                )

                merged_addresses = []

                for address in (
                    parent_profile["addresses"] + linked_profile["addresses"]
                ):
                    if address not in merged_addresses:
                        merged_addresses.append(address)

                parent_profile["addresses"] = merged_addresses
                parent_profile["votes"] += linked_profile["votes"]
                parent_profile["number_of_blocks"] += linked_profile["number_of_blocks"]
                processed_profiles.append(link)

            primary_address = self.get_primary_address(parent_profile["addresses"])
            merged_profiles[primary_address] = parent_profile

            processed_profiles.append(profile_id)

        for profile in merged_profiles:
            logger.info("Calculating share total for profile {}".format(profile))
            total_shares = 0
            addresses = []

            for address in merged_profiles[profile]["addresses"]:
                logger.info("Getting balance for {}".format(address))
                balance = address.balance
                total_shares += balance
                addresses.append({address.address: balance})

            merged_profiles[profile]["voting_shares"] = total_shares
            merged_profiles[profile]["addresses"] = addresses

        json.dump(merged_profiles, open("merged_profiles.json", "w+"), indent=2)

        # generate a chart
        x_labels = []
        num_addresses = []
        num_shares = []
        num_blocks = []

        for profile in sorted(merged_profiles, key=str.lower):
            x_labels.append(profile)
            num_addresses.append(len(merged_profiles[profile]["addresses"]))
            num_shares.append(merged_profiles[profile]["voting_shares"] / 10000)
            num_blocks.append(merged_profiles[profile]["number_of_blocks"])

        line_chart = pygal.Bar(
            legend_at_bottom=True, x_title="Voting Profile", x_label_rotation=30
        )
        line_chart.title = (
            "Voting share distribution over {} blocks as of Block {}".format(
                options["number"], options["start_height"]
            )
        )
        line_chart.x_labels = x_labels
        line_chart.add("Number of Addresses", num_addresses)
        line_chart.add("Total Number of Shares", num_shares, secondary=True)
        line_chart.add("Number of Solved Blocks", num_blocks)
        line_chart.render_to_file("chart.svg")

    @staticmethod
    def check_match(profiles, own_profile, search_address, links=None):
        if links is None:
            links = {}

        for profile in profiles:
            if profile == own_profile:
                continue

            profile_id = profiles[profile]["id"]

            if profile_id not in links:
                links[profile_id] = 0

            for address in profiles[profile]["addresses"]:
                if address == search_address:
                    links[profile_id] += 1

        return links

    @staticmethod
    def get_primary_address(addresses):
        """
        addresses is a list of dicts. each dict is {address: number_of_shares}
        we get the addresses and return the first alphabetically
        """
        addr_list = []

        for address in addresses:
            addr_list.append(address.address)

        return sorted(addr_list, key=str.lower)[0]
