from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from blocks.models import Block, Transaction, Address


class Search(View):
    @staticmethod
    def get(reqquest):
        return redirect(reverse('index'))

    @staticmethod
    def post(request):
        search_term = request.POST.get('search', '').strip()
        if search_term == '':
            messages.add_message(request, messages.ERROR, 'You submitted a blank search')
            return redirect(request.META.get('HTTP_REFERER'))

        # we have a search term.
        # we need to match it to a block height, a block has, a transaction id or
        # an address

        # find block by height
        try:
            block = Block.objects.get(height=search_term)
            messages.add_message(
                request,
                messages.SUCCESS,
                'Found Block {} for {}'.format(block.hash, search_term)
            )
            return redirect(reverse('block', kwargs={'block_height': block.height}))
        except (Block.DoesNotExist, ValueError):
            pass

        # find block by hash
        try:
            block = Block.objects.get(hash=search_term)
            messages.add_message(
                request,
                messages.SUCCESS,
                'Found Block {} for {}'.format(block.height, search_term)
            )
            return redirect(reverse('block', kwargs={'block_height': block.height}))
        except Block.DoesNotExist:
            pass

        # find transaction by id
        try:
            tx = Transaction.objects.get(tx_id=search_term)
            messages.add_message(
                request,
                messages.SUCCESS,
                'Transaction {} can be found in Block {}'.format(
                    search_term[:10],
                    tx.block.height
                )
            )
            return redirect(reverse('block', kwargs={'block_height': tx.block.height}))
        except Transaction.DoesNotExist:
            pass

        # find address
        try:
            address = Address.objects.get(address=search_term)
            messages.add_message(
                request,
                messages.SUCCESS,
                'Found Address {}'.format(search_term)
            )
            return redirect(reverse('address', kwargs={'address': address}))
        except Address.DoesNotExist:
            pass

        # didn't find anything
        messages.add_message(
            request,
            messages.ERROR,
            'Nothing matched your search term: {}'.format(search_term)
        )
        return redirect(request.META.get('HTTP_REFERER'))
