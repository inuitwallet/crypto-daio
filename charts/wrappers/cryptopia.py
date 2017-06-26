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

from charts.models import Trade, Balance, Pair, Exchange, Order

logger = logging.getLogger(__name__)


class Cryptopia(object):

    def __init__(self, api_key, api_secret, base_url):
        self.name = 'Cryptopia'
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
        return base64.b64encode(
            hmac.new(
                base64.b64decode(self.api_secret),
                msg=codecs.encode(parameter),
                digestmod=hashlib.sha256
            ).digest()
        ).decode("utf-8")

    def get_headers(self, url, nonce, post_params):
        header_value = 'amx {}:{}:{}'.format(
            self.api_key,
            self.get_signature(url, nonce, post_params),
            nonce
        )
        headers = {
            'Content-Type': 'application/json',
            'Authorization': header_value
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
            base_amount=Decimal(0),
            quote_amount=Decimal(0)
        )
        balances = self.make_request(
            'GetBalance',
            {}
        )
        for ex_balance in balances.get('Data', []):
            if ex_balance.get('Symbol') == pair.quote_currency.code:
                balance.quote_amount = Decimal(ex_balance.get('Total', 0))
            if ex_balance.get('Symbol') == pair.base_currency.code:
                balance.base_amount = Decimal(ex_balance.get('Total', 0))
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
            trade, created = Trade.objects.get_or_create(
                order_id=historic_trade.get('TradeId'),
                pair=pair
            )
            if created:
                trade.date_time = make_aware(
                    datetime.strptime(
                        historic_trade.get('TimeStamp')[:-1],
                        '%Y-%m-%dT%H:%M:%S.%f'
                    )
                )
                trade.order_type = (
                    'BUY'
                    if historic_trade.get('Type') == 'Buy'
                    else 'SELL'
                )
                trade.amount = Decimal(historic_trade.get('Amount'))
                trade.rate = Decimal(historic_trade.get('Rate'))
                trade.fee = Decimal(historic_trade.get('Fee'))
                trade.total = Decimal(historic_trade.get('Total'))
                trade.save()
                logger.info('saved {}'.format(trade))

    def get_withdrawals(self, pair):
        pass

    def get_deposits(self, pair):
        pass

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
            order, _ = Order.objects.get_or_create(
                pair=pair,
                order_id=open_order.get('OrderId')
            )
            order.order_type = 'BUY' if open_order.get('Type') == 'Buy' else 'SELL'
            order.amount = open_order.get('Amount')
            order.rate = open_order.get('Rate')
            order.date_time = make_aware(
                datetime.strptime(
                    open_order.get('TimeStamp')[:-1],
                    '%Y-%m-%dT%H:%M:%S.%f'
                )
            )
            order.Total = open_order.get('Total')
            order.open = True
            order.Remaining = open_order.get('Remaining')
            order.save()
