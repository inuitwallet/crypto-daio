from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View

from blocks.models import Address, Info
from daio.models import Coin


class AddressBalance(View):
    @staticmethod
    def get(request, address):
        address_object = get_object_or_404(Address, address=address)
        return JsonResponse({'balance': address_object.balance})


class TotalSupply(View):
    @staticmethod
    def get(request, coin):
        coin_object = get_object_or_404(Coin, code=coin)
        latest_info = Info.objects.filter(
            unit=coin_object.unit_code
        ).order_by(
            '-time_added'
        ).first()
        return HttpResponse(latest_info.money_supply)
