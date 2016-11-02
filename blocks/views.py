from threading import Thread

from django.views.generic import DetailView

from blocks.utils.block_parser import start_parse, save_block
from blocks.utils.rpc import send_rpc
from django.http import HttpResponse
from django.http.response import HttpResponseNotFound
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from django.conf import settings
from .models import *


def notify(request, block_hash):
    """
    Used by the coin daemon to notify of a new block
    :param request:
    :param block_hash:
    :return:
    """
    if request.META['REMOTE_ADDR'] != settings.NUD_HOST:
        return HttpResponseNotFound()
    if len(block_hash) < 60:
        return HttpResponse('Nope')
    block, created = Block.objects.get_or_create(hash=block_hash)
    if created:
        rpc = send_rpc(
            {
                'method': 'getblock',
                'params': [block_hash, True, True]
            }
        )
        got_block = rpc['result'] if not rpc['error'] else None
        if got_block:
            save = Thread(
                target=save_block,
                kwargs={
                    'block': got_block,
                },
            )
            save.daemon = True
            save.start()
    return HttpResponse('daio received block {}'.format(block_hash))


def parse(request):
    parse_thread = Thread(target=start_parse)
    parse_thread.daemon = True
    parse_thread.start()
    return render(request, 'admin/blocks/app_index.html')


class BlockList(ListView):
    model = Block
    paginate_by = 50

    def get_queryset(self):
        return Block.objects.all().order_by('-height')


class BlockDetail(DetailView):
    model = Block

    def get_object(self):
        return get_object_or_404(Block, hash=self.kwargs['block_hash'])


class TransactionDetail(DetailView):
    model = Transaction

    def get_object(self):
        return get_object_or_404(Transaction, tx_id=self.kwargs['tx_id'])

