from django.views import View

from django.http import HttpResponse
from django.http.response import HttpResponseNotFound
from django.views.generic import ListView
from django.conf import settings
from .models import *

from .utils.parser import trigger_block_parse


class Notify(View):
    """
    Used by the coin daemon to notify of a new block
    :param request:
    :param block_hash:
    :return:
    """
    @staticmethod
    def get(request, block_hash):
        if request.META['REMOTE_ADDR'] != settings.NUD_HOST:
            return HttpResponse('not a recognised IP address')
        if len(block_hash) < 60:
            return HttpResponse('Nope')
        block, created = Block.objects.get_or_create(hash=block_hash)
        if created:
            trigger_block_parse(block_hash)
        return HttpResponse('daio received block {}'.format(block_hash))


class LatestBlocksList(ListView):
    model = Block
    template_name = 'explorer/latest_blocks_list.html'

    def get_queryset(self):
        return Block.objects.exclude(height=None).order_by('-height')[:15]
