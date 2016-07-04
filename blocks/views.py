from threading import Thread
from blocks.utils.block_parser import start_parse, save_block
from blocks.utils.rpc import send_rpc
from django.http import HttpResponse
from django.http.response import HttpResponseNotFound
from django.shortcuts import render
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
    block = Block.objects.get_or_create(hash=block_hash)
    if block[1]:
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


def get_block(request, block_height):
    """
    get the block at height
    :param request:
    :param block_height:
    :return:
    """
    block = Block.objects.get(height=block_height)
    context = {'block': block, 'transactions': []}
    for tx in block.transactions.all():
        input_id = tx.inputs.all()[0].tx_id
        input = None
        if input_id:
            input = Transaction.objects.get(tx_id=input_id)
        tx_dict = {
            'input': input,
            'outputs': [],
        }
        outputs = TxOutput.objects.filter(transaction=tx)
        for output in outputs:
            tx_dict['outputs'].append(output)

    return render(request, 'blocks/block.html', context)


def parse(request):
    parse_thread = Thread(target=start_parse)
    parse_thread.daemon = True
    parse_thread.start()
    return render(request, 'admin/blocks/app_index.html')


class BlockView(ListView):
    model = Block
