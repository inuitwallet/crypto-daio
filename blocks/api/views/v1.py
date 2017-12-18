from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from blocks.models import Address


class AddressBalance(View):
    def get(self, request, address):
        address_object = get_object_or_404(Address, address=address)
        return JsonResponse({'balance': address_object.balance})
