from django.db import connection
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from blocks.models import Address, Info, Transaction
from daio.models import Coin
from blocks.utils.rpc import send_rpc


class AddressBalance(View):
    """
    Give the balance of a passed address.
    Used by Lambda functions
    """
    @staticmethod
    def get(request, address):
        address_object = get_object_or_404(Address, address=address)
        return JsonResponse({'balance': address_object.balance})


class AddressUnspent(View):
    """
    Give the unspent outputs for a passed address.
    Used by CoinToolKit
    """
    @staticmethod
    def get(request, address):
        address_object = get_object_or_404(Address, address=address)
        return JsonResponse(
            {
                'status': 'success',
                'data': {
                    'unspent': [
                        {
                            'tx': output.transaction.tx_id,
                            'n': output.index,
                            'script': output.script_pub_key_asm,
                            'amount': output.value
                        } for output in address_object.outputs.filter(
                            input__isnull=True,
                            transaction__block__isnull=False,
                            transaction__block__height__isnull=False
                        )
                    ]
                }
            }
        )


class TransactionBroadcast(View):
    """
    Broadcast the raw hex transaction passed in POST
    Used by CointoolKit
    """
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(TransactionBroadcast, self).dispatch(request, *args, **kwargs)

    @staticmethod
    def post(request):
        rpc = send_rpc(
            {
                'method': 'sendrawtransaction',
                'params': [request.POST.get('hex'), 1],
            },
            schema_name=connection.tenant.schema_name
        )
        if not rpc:
            return JsonResponse(
                {
                    'status': 'failure',
                }
            )

        return JsonResponse(
            {
                'status': 'success',
                'data': rpc
            }
        )


class TransactionInputs(View):
    """
    Return all previous output values for each transaction input.
    Used by CoinToolKit
    """
    @staticmethod
    def get(request, transaction):
        tx = get_object_or_404(Transaction, tx_id=transaction)
        return JsonResponse(
            {
                'status': 'success',
                'data': {
                    'vouts': [
                        {
                            'amount': input.previous_output.display_value
                        } for input in tx.inputs.all()
                    ]
                }
            }
        )


class TotalSupply(View):
    """
    Return A coins Total Supply (as received from the Coin Daemon)
    Used by CoinMarketCap
    """
    @staticmethod
    def get(request, coin):
        coin_object = get_object_or_404(Coin, code=coin)
        latest_info = Info.objects.filter(
            unit=coin_object.unit_code
        ).order_by(
            '-time_added'
        ).first()
        return HttpResponse(latest_info.money_supply)


class ParkedSupply(View):
    """
    Return the Amount of Coins Parked
    """
    @staticmethod
    def get(request, coin):
        coin_object = get_object_or_404(Coin, code=coin)
        latest_info = Info.objects.filter(
            unit=coin_object.unit_code
        ).order_by(
            '-time_added'
        ).first()
        return HttpResponse(latest_info.total_parked if latest_info.total_parked else 0)
