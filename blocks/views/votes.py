from django.db import connection
from django.db.models import Max, Min, Sum
from django.shortcuts import render
from django.views import View

from blocks.models import CustodianVote, Block, TxOutput, MotionVote


class GrantView(View):
    def get(self, request):
        # get the block height 10000 blocks ago
        max_height = Block.objects.all().aggregate(Max('height'))
        vote_window_min = max_height['height__max'] - 10000

        grants = CustodianVote.objects.filter(
            block__height__gte=vote_window_min
        ).distinct(
            'address',
            'amount'
        )
        sharedays_destroyed = Block.objects.filter(
            height__gte=vote_window_min,
            height__lte=max_height['height__max']
        ).aggregate(Sum('coinage_destroyed'))['coinage_destroyed__sum']

        open_grants = []

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
                    address=grant.address,
                    amount=grant.amount
                )
                votes_count = votes.count()
                grant_sharedays = votes.aggregate(
                    Sum('block__coinage_destroyed')
                )['block__coinage_destroyed__sum']
                open_grants.append(
                    {
                        'address': grant.address.address,
                        'amount': grant.amount,
                        'number_of_votes': votes_count,
                        'vote_percentage': round((votes_count / 10000) * 100, 2),
                        'first_seen': CustodianVote.objects.filter(
                            address=grant.address,
                            amount=grant.amount
                        ).aggregate(Min('block__height'))['block__height__min'],
                        'sharedays_destroyed': grant_sharedays,
                        'sharedays_percentage': round(
                            (grant_sharedays / sharedays_destroyed) * 100,
                            2
                        ),
                        'granted': granted
                    }
                )
        return render(
            request,
            'explorer/grants.html',
            {
                'chain': connection.tenant,
                'grants': sorted(
                    open_grants,
                    key=lambda x: x['vote_percentage'],
                    reverse=True
                ),
                'block_min_height': vote_window_min,
                'block_max_height': max_height['height__max']
            }
        )


class MotionView(View):
    def get(self, request):
        # get the block height 10000 blocks ago
        max_height = Block.objects.all().aggregate(Max('height'))
        vote_window_min = max_height['height__max'] - 10000

        motions = MotionVote.objects.all().distinct(
            'hash'
        )

        for motion in motions:
            pass

        return render(
            request,
            'explorer/grants.html',
            {
                'chain': connection.tenant,
            }
        )
