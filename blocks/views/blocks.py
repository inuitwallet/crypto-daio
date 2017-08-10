from django.db import connection
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from blocks.models import Block, Transaction


class LatestBlocksList(ListView):
    model = Block
    paginate_by = 50
    template_name = 'explorer/latest_blocks_list.html'

    def get_queryset(self):
        return Block.objects.exclude(height=None).order_by('-height')

    def get_context_data(self, **kwargs):
        context = super(LatestBlocksList, self).get_context_data(**kwargs)
        context['chain'] = connection.tenant
        return context


class BlockDetailView(View):
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(BlockDetailView, self).dispatch(request, *args, **kwargs)

    @staticmethod
    def get(request, block_height):
        block = get_object_or_404(Block, height=block_height)
        block.save()
        return render(
            request,
            'explorer/block_detail.html',
            {
                'object': block,
                'chain': connection.tenant,
            }
        )

    @staticmethod
    def post(request, block_height):
        # validate the given transaction and return the same page
        if 'tx_pk' in request.POST:
            # attempt to get the transaction if it exists
            try:
                tx = Transaction.objects.get(pk=request.POST['tx_pk'])
                # save the tx to start validation
                tx.save()
            except Transaction.DoesNotExist:
                pass
        return render(
            request,
            'explorer/block_detail.html',
            {
                'object': get_object_or_404(Block, height=block_height),
                'chain': connection.tenant,
            }
        )


class All_Blocks(LatestBlocksList):
    model = Block
    paginate_by = 50
    template_name = 'explorer/all_blocks_list.html'

    def get_queryset(self):
        return Block.objects.exclude(height=None).order_by('-height')

    def get_context_data(self, **kwargs):
        context = super(LatestBlocksList, self).get_context_data(**kwargs)
        context['chain'] = connection.tenant
        return context
