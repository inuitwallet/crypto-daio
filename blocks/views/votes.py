from django.db.models import Max
from django.http import JsonResponse
from django.views import View

from blocks.models import CustodianVote, Block, TxOutput


class GrantView(View):
    def get(self, request):
        grants = CustodianVote.objects.all().distinct('address', 'amount')

        # get the block height 10000 blocks ago
        max_height = Block.objects.all().aggregate(Max('height'))
        vote_window_min = max_height['height__max'] - 10000
        open_grants = []
        for grant in grants:
            try:
                TxOutput.objects.get(address=grant.address, value=grant.amount * 1000)
                # output of amount to address exists
            except TxOutput.DoesNotExist:
                open_grants.append()
        return JsonResponse({'window_min': vote_window_min})
