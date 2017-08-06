import codecs
import time
import hashlib
import hmac
from datetime import datetime
from urllib import parse
import logging
import requests
from decimal import Decimal

from django.utils.timezone import make_aware

from charts.models import Balance, Trade, Order, Withdrawal, Deposit

logger = logging.getLogger(__name__)


class Bittrex(object):
    def __init__(self, api_key, api_secret, base_url):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def get_headers(self, url, params):
        uri = '{}/{}?{}'.format(self.base_url, url, parse.urlencode(params))
        return {
            'apisign': hmac.new(
                codecs.encode(self.api_secret),
                msg=codecs.encode(uri),
                digestmod=hashlib.sha512
            ).hexdigest()
        }

    def make_request(self, url, params):
        params['nonce'] = int(time.time()) * 1000
        params['apikey'] = self.api_key
        response = requests.get(
            url='{}/{}?{}'.format(self.base_url, url, parse.urlencode(params)),
            headers=self.get_headers(url, params)
        )

        try:
            return response.json()
        except ValueError:
            return response.text

    def get_balances(self, pair):
        balance = Balance.objects.create(
            pair=pair,
            base_amount=None,
            quote_amount=None
        )
        balances = self.make_request('account/getbalances', {})
        for ex_balance in balances.get('result', []):
            if ex_balance.get('Currency') == pair.quote_currency.code:
                balance.quote_amount = Decimal(ex_balance.get('Balance'))
            if ex_balance.get('Currency') == pair.base_currency.code:
                balance.base_amount = Decimal(ex_balance.get('Balance'))
        balance.save()

    def get_trade_history(self, pair):
        trade_history = self.make_request(
            'account/getorderhistory',
            {
                'market': '{}-{}'.format(
                    pair.base_currency.code,
                    pair.quote_currency.code
                )
            }
        )
        for historic_trade in trade_history.get('result', []):
            amount = Decimal(historic_trade.get('Quantity', 0))
            rate = Decimal(historic_trade.get('PricePerUnit', 0))

            try:
                timestamp = datetime.strptime(
                    historic_trade.get('TimeStamp'),
                    '%Y-%m-%dT%H:%M:%S.%f'
                )
            except ValueError:
                timestamp = datetime.strptime(
                    historic_trade.get('TimeStamp'),
                    '%Y-%m-%dT%H:%M:%S'
                )

            trade, _ = Trade.objects.update_or_create(
                order_id=historic_trade.get('OrderUuid'),
                pair=pair,
                defaults={
                    'date_time': make_aware(timestamp),
                    'order_type': (
                        'BUY' if
                        historic_trade.get('OrderType') == 'LIMIT_BUY'
                        else 'SELL'
                    ),
                    'amount': amount,
                    'rate': rate,
                    'fee': Decimal(historic_trade.get('Commission', 0)),
                    'total': Decimal(amount * rate)
                }
            )

    def get_withdrawals(self, pair):
        withdrawal_history = self.make_request(
            'account/getwithdrawalhistory',
            {}
        )
        for withdrawal in withdrawal_history.get('result', []):
            currency = None

            if pair.quote_currency.code == withdrawal.get('Currency'):
                currency = pair.quote_currency

            if pair.base_currency.code == withdrawal.get('Currency'):
                currency = pair.base_currency

            if not currency:
                continue

            completed = False

            try:
                date_time = make_aware(
                    datetime.strptime(
                        withdrawal.get('Opened'),
                        '%Y-%m-%dT%H:%M:%S.%f'
                    )
                )
            except ValueError:
                date_time = make_aware(
                    datetime.strptime(
                        withdrawal.get('Opened'),
                        '%Y-%m-%dT%H:%M:%S'
                    )
                )

            if withdrawal.get('Authorized') \
                    and not withdrawal.get('PendingPayment') \
                    and not withdrawal.get('InvalidAddress') \
                    and not withdrawal.get('Canceled'):
                completed = True

            Withdrawal.objects.update_or_create(
                pair=pair,
                exchange_tx_id=withdrawal.get('PaymentUuid'),
                defaults={
                    'currency': currency,
                    'date_time': date_time,
                    'complete': completed,
                    'amount': withdrawal.get('Amount'),
                    'fee': withdrawal.get('TxCost'),
                    'tx_id': withdrawal.get('TxId'),
                    'address': withdrawal.get('Address'),
                }
            )

    def get_deposits(self, pair):
        deposit_history = self.make_request(
            'account/getdeposithistory',
            {}
        )
        for deposit in deposit_history.get('result', []):
            currency = None

            if pair.quote_currency.code == deposit.get('Currency'):
                currency = pair.quote_currency

            if pair.base_currency.code == deposit.get('Currency'):
                currency = pair.base_currency

            if not currency:
                continue

            completed = (
                True
                if deposit.get('Confirmations', 0) > 0 else
                False
            )

            try:
                date_time = make_aware(
                    datetime.strptime(
                        deposit.get('LastUpdated'),
                        '%Y-%m-%dT%H:%M:%S.%f'
                    )
                )
            except ValueError:
                date_time = make_aware(
                    datetime.strptime(
                        deposit.get('LastUpdated'),
                        '%Y-%m-%dT%H:%M:%S'
                    )
                )

            Deposit.objects.update_or_create(
                pair=pair,
                exchange_tx_id=deposit.get('Id'),
                defaults={
                    'currency': currency,
                    'date_time': date_time,
                    'complete': completed,
                    'amount': deposit.get('Amount'),
                    'tx_id': deposit.get('TxId'),
                }
            )

    def get_open_orders(self, pair):
        # close all open orders for the pair
        for open_order in Order.objects.filter(pair=pair, open=True):
            open_order.open = False
            open_order.save()

        open_orders = self.make_request(
            'market/getopenorders',
            {
                'market': '{}-{}'.format(
                    pair.base_currency.code,
                    pair.quote_currency.code
                )
            }
        )

        for open_order in open_orders.get('result', []):
            try:
                date_time = make_aware(
                    datetime.strptime(
                        open_order.get('Opened'),
                        '%Y-%m-%dT%H:%M:%S.%f'
                    )
                )
            except ValueError:
                date_time = make_aware(
                    datetime.strptime(
                        open_order.get('Opened'),
                        '%Y-%m-%dT%H:%M:%S'
                    )
                )
            order, _ = Order.objects.update_or_create(
                pair=pair,
                order_id=open_order.get('OrderUuid'),
                defaults={
                    'order_type': (
                        'BUY'
                        if open_order.get('OrderType') == 'LIMIT_BUY'
                        else 'SELL'
                    ),
                    'amount': open_order.get('Quantity'),
                    'rate': open_order.get('Limit'),
                    'date_time': date_time,
                    'remaining': open_order.get('QuantityRemaining'),
                    'total': open_order.get('Quantity') * open_order.get('Limit'),
                    'open': True
                }
            )
