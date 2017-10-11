import base64
import codecs
import hashlib
import hmac
import json
from urllib import parse
from datetime import datetime

import logging
import requests
import time

from decimal import Decimal
from django.utils.timezone import make_aware

from charts.models import Trade, Balance, Pair, Exchange, Order, Withdrawal, Deposit

logger = logging.getLogger(__name__)


class SouthXchange(object):

    def __init__(self, api_key, api_secret, base_url):
        self.name = 'SouthXchange'
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def get_signature(self, url, nonce, post_params):
        parameter = "{}POST{}{}{}".format(
            self.api_key,
            parse.quote(self.base_url + url, safe='').lower(),
            nonce,
            base64.b64encode(hashlib.md5(codecs.encode(json.dumps(post_params))).digest()).decode("utf-8")  # noqa
        )
        return hmac.new(
            base64.b64decode(self.api_secret),
            msg=codecs.encode(parameter),
            digestmod=hashlib.sha256
        ).hexdigest()

    def get_headers(self, url, nonce, post_params):
        header_value = 'amx {}:{}:{}'.format(
            self.api_key,
            self.get_signature(url, nonce, post_params),
            nonce
        )
        headers = {
            'Content-Type': 'application/json',
            'Hash': header_value
        }
        return headers

    def make_request(self, url, post_params):
        response = requests.post(
            url=self.base_url + url,
            headers=self.get_headers(url, int(time.time() * 1000), post_params),
            data=json.dumps(post_params),
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
        balances = self.make_request(
            'GetBalance',
            {}
        )
        for ex_balance in balances.get('Data', []):
            if ex_balance.get('Symbol') == pair.quote_currency.code:
                balance.quote_amount = Decimal(ex_balance.get('Total'))
            if ex_balance.get('Symbol') == pair.base_currency.code:
                balance.base_amount = Decimal(ex_balance.get('Total'))
        balance.save()

    def get_trade_history(self, pair):
        trade_history = self.make_request(
            'GetTradeHistory',
            {
                'Market': '{}/{}'.format(
                    pair.quote_currency.code,
                    pair.base_currency.code
                ),
                'Count': 1000
            }
        )
        for historic_trade in trade_history.get('Data', []):
            amount = Decimal(historic_trade.get('Amount', 0))
            rate = Decimal(historic_trade.get('Rate', 0))

            trade, _ = Trade.objects.update_or_create(
                order_id=historic_trade.get('TradeId'),
                pair=pair,
                defaults={
                    'date_time': make_aware(
                        datetime.strptime(
                            historic_trade.get('TimeStamp')[:-1],
                            '%Y-%m-%dT%H:%M:%S.%f'
                        )
                    ),
                    'order_type': (
                        'BUY'
                        if historic_trade.get('Type') == 'Buy'
                        else 'SELL'
                    ),
                    'amount': amount,
                    'rate': rate,
                    'fee': Decimal(historic_trade.get('Fee', 0)),
                    'total': Decimal(historic_trade.get('Total', amount * rate))
                }
            )

    def get_withdrawals(self, pair):
        withdrawal_history = self.make_request(
            'GetTransactions',
            {
                'Type': 'Withdraw',
                'Count': 1000
            }
        )
        for withdrawal in withdrawal_history.get('Data', []):
            currency = None

            if pair.quote_currency.code == withdrawal.get('Currency'):
                currency = pair.quote_currency

            if pair.base_currency.code == withdrawal.get('Currency'):
                currency = pair.base_currency

            if not currency:
                continue

            completed = (
                True
                if withdrawal.get('Status') == 'Complete' else
                False
            )
            date_time = make_aware(
                datetime.strptime(
                    withdrawal.get('Timestamp')[:-1],
                    '%Y-%m-%dT%H:%M:%S.%f'
                )
            )
            Withdrawal.objects.update_or_create(
                pair=pair,
                exchange_tx_id=withdrawal.get('Id'),
                defaults={
                    'currency': currency,
                    'date_time': date_time,
                    'complete': completed,
                    'amount': withdrawal.get('Amount'),
                    'fee': withdrawal.get('Fee'),
                    'tx_id': withdrawal.get('TxId'),
                    'address': withdrawal.get('Address'),
                }
            )

    def get_deposits(self, pair):
        deposit_history = self.make_request(
            'GetTransactions',
            {
                'Type': 'Deposit',
                'Count': 1000
            }
        )
        for deposit in deposit_history.get('Data', []):
            currency = None

            if pair.quote_currency.code == deposit.get('Currency'):
                currency = pair.quote_currency

            if pair.base_currency.code == deposit.get('Currency'):
                currency = pair.base_currency

            if not currency:
                continue

            completed = (
                True
                if deposit.get('Status') == 'Confirmed' else
                False
            )
            date_time = make_aware(
                datetime.strptime(
                    deposit.get('Timestamp'),
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
                    'fee': deposit.get('Fee'),
                    'tx_id': deposit.get('TxId'),
                }
            )

    def get_open_orders(self, pair):
        # close all open orders for the pair
        for open_order in Order.objects.filter(pair=pair, open=True):
            open_order.open = False
            open_order.save()

        open_orders = self.make_request(
            'GetOpenOrders',
            {
                'Market': '{}/{}'.format(
                    pair.quote_currency.code,
                    pair.base_currency.code
                ),
                'Count': 1000
            }
        )

        for open_order in open_orders.get('Data', []):
            order, _ = Order.objects.update_or_create(
                pair=pair,
                order_id=open_order.get('OrderId'),
                defaults={
                    'order_type': (
                        'BUY'
                        if open_order.get('Type') == 'Buy'
                        else 'SELL'
                    ),
                    'amount': open_order.get('Amount'),
                    'rate': open_order.get('Rate'),
                    'date_time': make_aware(
                        datetime.strptime(
                            open_order.get('TimeStamp')[:-1],
                            '%Y-%m-%dT%H:%M:%S.%f'
                        )
                    ),
                    'total': open_order.get('Total'),
                    'open': True,
                    'remaining': open_order.get('Remaining')
                }
            )
