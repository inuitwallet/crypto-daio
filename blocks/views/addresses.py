from django.db import connection
from django.shortcuts import render, get_object_or_404
from django.views import View

from blocks.models import Address


class AddressDetailView(View):
    @staticmethod
    def get(request, address):
        return render(
            request,
            'explorer/address_detail.html',
            {
                'object': get_object_or_404(Address, address=address),
                'chain': connection.tenant,
            }
        )
