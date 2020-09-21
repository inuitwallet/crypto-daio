import json
import logging

from django.db.models import Max, Min, Sum
from django.template.loader import render_to_string

from blocks.models import Block, CustodianVote, MotionVote, TxOutput

logger = logging.getLogger(__name__)


def get_current_grants(message):
    message.reply_channel.send(
        {"text": json.dumps({"message_type": "loading"})}, immediately=True
    )
    # get the block height 10000 blocks ago
    max_height = Block.objects.all().aggregate(Max("height"))["height__max"]
    vote_window_min = max_height - 10000

    # get the distinct grants that have been voted for in the last 10000 blocks
    grants = (
        CustodianVote.objects.filter(
            block__height__gte=vote_window_min, block__height__lte=max_height
        )
        .exclude(block__isnull=True)
        .distinct("address", "amount")
    )

    # get the total number of sharedays destroyed in the current period
    sharedays_destroyed = Block.objects.filter(
        height__gte=vote_window_min, height__lte=max_height
    ).aggregate(Sum("coinage_destroyed"))["coinage_destroyed__sum"]

    for grant in grants:
        granted = None
        for grant_output in TxOutput.objects.filter(
            address=grant.address,
            value=grant.amount * 10000,
        ):
            if not grant_output.transaction.block:
                continue

            for tx_input in grant_output.transaction.inputs.all():
                if not tx_input.previous_output:
                    granted = tx_input.transaction.block

        # lets see how many blocks in the last 10000 this grant exists in
        votes = CustodianVote.objects.filter(
            block__height__gte=vote_window_min,
            block__height__lte=max_height,
            address=grant.address,
            amount=grant.amount,
        )
        votes_count = votes.count()
        grant_sharedays = votes.aggregate(Sum("block__coinage_destroyed"))[
            "block__coinage_destroyed__sum"
        ]

        message.reply_channel.send(
            {
                "text": json.dumps(
                    {
                        "message_type": "new_current_grant",
                        "html": render_to_string(
                            "explorer/fragments/grant.html",
                            {
                                "grant": {
                                    "address": grant.address.address,
                                    "amount": grant.amount,
                                    "number_of_votes": votes_count,
                                    "vote_percentage": round(
                                        (votes_count / 10000) * 100, 2
                                    ),
                                    "first_seen": CustodianVote.objects.filter(
                                        address=grant.address, amount=grant.amount
                                    ).aggregate(Min("block__height"))[
                                        "block__height__min"
                                    ],
                                    "sharedays_destroyed": grant_sharedays,
                                    "sharedays_percentage": round(
                                        (grant_sharedays / sharedays_destroyed) * 100, 2
                                    ),
                                    "granted": granted,
                                }
                            },
                        ),
                    }
                )
            },
            immediately=True,
        )

    message.reply_channel.send(
        {"text": json.dumps({"message_type": "done"})}, immediately=True
    )


def get_current_motions(message):
    message.reply_channel.send(
        {"text": json.dumps({"message_type": "loading"})}, immediately=True
    )
    # get the block height 10000 blocks ago
    max_height = Block.objects.all().aggregate(Max("height"))["height__max"]
    vote_window_min = max_height - 10000

    # get the distinct grants that have been voted for in the last 10000 blocks
    motions = (
        MotionVote.objects.filter(
            block__height__gte=vote_window_min, block__height__lte=max_height
        )
        .exclude(block__isnull=True)
        .distinct("hash")
    )

    # get the total number of sharedays destroyed in the current period
    sharedays_destroyed = Block.objects.filter(
        height__gte=vote_window_min, height__lte=max_height
    ).aggregate(Sum("coinage_destroyed"))["coinage_destroyed__sum"]

    for motion in motions:
        # lets see if this has passed
        try:
            granted = MotionVote.objects.get(
                hash=motion.hash, block_percentage__gte=50, sdd_percentage__gte=50
            )
        except MotionVote.DoesNotExist:
            granted = False

        # lets see how many blocks in the last 10000 this grant exists in
        votes = MotionVote.objects.filter(
            block__height__gte=vote_window_min,
            block__height__lte=max_height,
            hash=motion.hash,
        )
        votes_count = votes.count()
        motion_sharedays = votes.aggregate(Sum("block__coinage_destroyed"))[
            "block__coinage_destroyed__sum"
        ]

        message.reply_channel.send(
            {
                "text": json.dumps(
                    {
                        "message_type": "new_current_motion",
                        "html": render_to_string(
                            "explorer/fragments/motion.html",
                            {
                                "motion": {
                                    "hash": motion.hash,
                                    "number_of_votes": votes_count,
                                    "vote_percentage": round(
                                        (votes_count / 10000) * 100, 2
                                    ),
                                    "first_seen": MotionVote.objects.filter(
                                        hash=motion.hash
                                    ).aggregate(Min("block__height"))[
                                        "block__height__min"
                                    ],
                                    "sharedays_destroyed": motion_sharedays,
                                    "sharedays_percentage": round(
                                        (motion_sharedays / sharedays_destroyed) * 100,
                                        2,
                                    ),
                                    "granted": granted,
                                }
                            },
                        ),
                    }
                )
            },
            immediately=True,
        )

    message.reply_channel.send(
        {"text": json.dumps({"message_type": "done"})}, immediately=True
    )
