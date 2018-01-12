import codecs
import logging
from decimal import Decimal

from django.db import connection
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from blocks.models import Block, Address, Info, Transaction, NetworkFund
from daio.models import Coin
from blocks.utils.rpc import send_rpc
from blocks.utils.exchange_balances import get_exchange_balances

logger = logging.getLogger(__name__)


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
                            'amount': output.display_value
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
                            'amount': output.display_value
                        } for output in tx.outputs.filter(input__isnull=True)
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
        coin_object = get_object_or_404(Coin, code=coin.upper())
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
        coin_object = get_object_or_404(Coin, code=coin.upper())
        latest_info = Info.objects.filter(
            unit=coin_object.unit_code
        ).order_by(
            '-time_added'
        ).first()
        return HttpResponse(latest_info.total_parked if latest_info.total_parked else 0)


class CirculatingSupply(View):
    @staticmethod
    def get(request, coin):
        coin_object = get_object_or_404(Coin, code=coin.upper())
        latest_info = Info.objects.filter(
            unit=coin_object.unit_code
        ).order_by(
            '-time_added'
        ).first()

        total_supply = latest_info.money_supply
        parked = latest_info.total_parked if latest_info.total_parked else 0

        # funds at network addresses
        network_owned_addresses = Address.objects.filter(
            network_owned=True,
            coin=coin_object
        )
        total_network_owned_funds = 0

        for address in network_owned_addresses:
            total_network_owned_funds += Decimal(address.balance / 10000)

        # other network owned funds
        other_funds = NetworkFund.objects.filter(coin=coin_object).aggregate(Sum('value'))
        total_network_owned_funds += (
            other_funds['value__sum'] if other_funds['value__sum'] else 0
        )

        # exchange balances
        for exchange_balance in get_exchange_balances(coin_object):
            total_network_owned_funds += Decimal(exchange_balance.get('balance'))

        return HttpResponse(
            round(
                total_supply - (parked + total_network_owned_funds),
                coin_object.decimal_places
            )
        )


class NetworkFunds(View):
    @staticmethod
    def get(request, coin):
        coin_object = get_object_or_404(Coin, code=coin.upper())

        return JsonResponse(
            {
                'network_owned_addresses': [
                    {
                        'address': address.address,
                        'balance': float(
                            round(
                                Decimal(address.balance / 10000),
                                coin_object.decimal_places
                            )
                        )
                    } for address in Address.objects.filter(
                        network_owned=True,
                        coin=coin_object
                    )
                ],
                'other_network_funds': [
                    {
                        'name': fund.name,
                        'value': float(
                            round(
                                fund.value,
                                coin_object.decimal_places
                            )
                        )
                    } for fund in NetworkFund.objects.filter(coin=coin_object)
                ],
                'network_funds_on_exchange': [
                    {
                        'exchange': balance.get('exchange'),
                        'balance': float(
                            round(
                                balance.get('balance'),
                                coin_object.decimal_places
                            )
                        )
                    } for balance in get_exchange_balances(coin_object)
                ]
            }
        )


class GetValidHashes(View):
    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(GetValidHashes, self).dispatch(request, *args, **kwargs)

    @staticmethod
    def post(request):
        # data arrives in request.body
        sent_hashes = codecs.encode(request.body, 'hex')
        start = 0
        index = 64
        start_height = None
        return_hash = b''

        # loop through the data to check the sent hashes
        while not start_height:
            try_hash = codecs.encode(codecs.decode(sent_hashes[start:index], 'hex')[::-1], 'hex').decode()  # noqa
            logger.info('looking for block hash {}'.format(try_hash))

            try:
                block = Block.objects.get(hash=try_hash)
                start_height = block.height
            except Block.DoesNotExist:
                start = index
                index += 64
                if index == len(sent_hashes):
                    break

        if not start_height:
            logger.error('Didn\'t identify any hashes when searching for valid hashes')
            return HttpResponse(return_hash)

        # get hashes starting form the first one recognised
        for block in Block.objects.filter(
            height__gte=start_height
        ).order_by(
            'height'
        )[:50000]:
            return_hash += codecs.decode(block.hash.encode(), 'hex')[::-1][:16]

        return HttpResponse(return_hash)
