from django.db import connection
from django.shortcuts import render
from django.views import View

from blocks.models import Peer, Info


class HealthView(View):

    @staticmethod
    def get(request):
        # get the latest info object
        info = Info.objects.all().order_by('-time_added').first()
        # calculate the peers distance from our latest block
        peers = Peer.objects.all().order_by('-height')
        for peer in peers:
            peer.height_diff = peer.height - info.max_height
        return render(
            request,
            'explorer/health.html',
            {
                'chain': connection.tenant,
                'peers': peers
            }
        )
