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
from .forms import SearchForm


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
                'params': [block_hash]
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
        return Block.objects.all().exclude(height=None).order_by('-height')


class BlockDetail(DetailView):
    model = Block
    context_object_name = u'block_data'

    def get_object(self, **kwargs):
        return get_object_or_404(Block, hash=self.kwargs['block_hash'])

    def get_context_data(self, **kwargs):
        context = super(BlockDetail, self).get_context_data(**kwargs)
        context['balance'] = {}
        block = get_object_or_404(Block, hash=self.kwargs['block_hash'])

        for transaction in block.transactions.all():
            input_total = 0

            for tx_input in TxInput.objects.filter(transaction=transaction):
                try:
                    output = TxOutput.objects.get(
                        transaction=tx_input.output_transaction,
                        n=tx_input.v_out
                    )
                    input_total += output.value
                except TxOutput.DoesNotExist:
                    continue

            output_total = 0

            for tx_output in transaction.outputs.all():
                output_total += tx_output.value

            context['balance'][str(transaction.tx_id)] = output_total - input_total

        return context


class TransactionDetail(DetailView):
    model = Transaction

    def get_object(self):
        return get_object_or_404(Transaction, tx_id=self.kwargs['tx_id'])


def search(request):
    """
    Search term can be a full or partial:
    block height,
    block hash,
    tx hash,
    address
    :param request:
    :return:
    """
    results = []
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            # we have a search term.
            # lets search
            # block height first
            results += Block.objects.filter(
                height__icontains=form.cleaned_data['search']
            )
            # then block hash
            results += Block.objects.filter(
                hash__icontains=form.cleaned_data['search']
            )
            # then Tx hash
            results += Transaction.objects.filter(
                tx_id__icontains=form.cleaned_data['search']
            )
            # the addresses
            results += Address.objects.filter(
                address__icontains=form.cleaned_data['search']
            )
    else:
        form = SearchForm()

    return render(request, 'blocks/search.html', {'form': form, 'results': results})
