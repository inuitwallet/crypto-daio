from channels import Channel
from django.views import View

from django.http import HttpResponse
from django.http.response import HttpResponseNotFound
from django.views.generic import ListView
from django.conf import settings
from .models import *


class Notify(View):
    """
    Used by the coin daemon to notify of a new block
    :param request:
    :param block_hash:
    :return:
    """
    @staticmethod
    def get(request, block_hash, secret_hash):
        if secret_hash not in settings.NOTIFY_SECRET_HASHES:
            return HttpResponseNotFound()
        if len(block_hash) < 60:
            return HttpResponseNotFound()
        block, created = Block.objects.get_or_create(hash=block_hash)
        if created:
            Channel('parse_block').send({'block_hash': block_hash})
        return HttpResponse('daio received block {}'.format(block_hash))


class LatestBlocksList(ListView):
    model = Block
    template_name = 'explorer/latest_blocks_list.html'

    def get_queryset(self):
        return Block.objects.exclude(height=None).order_by('-height')[:15]
