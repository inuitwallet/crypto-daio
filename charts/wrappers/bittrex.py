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

from charts.models import Balance, Trade

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
            base_amount=Decimal(0),
            quote_amount=Decimal(0)
        )
        balances = self.make_request('account/getbalances', {})
        for ex_balance in balances.get('result', []):
            if ex_balance.get('Currency') == pair.quote_currency.code:
                balance.quote_amount = Decimal(ex_balance.get('Balance', 0))
            if ex_balance.get('Currency') == pair.base_currency.code:
                balance.base_amount = Decimal(ex_balance.get('Balance', 0))
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
            trade, created = Trade.objects.get_or_create(
                order_id=historic_trade.get('OrderUuid'),
                pair=pair
            )
            if created:
                trade.date_time = make_aware(
                    datetime.strptime(
                        historic_trade.get('TimeStamp'),
                        '%Y-%m-%dT%H:%M:%S.%f'
                    )
                )
                trade.order_type = (
                    'BUY' if
                    historic_trade.get('OrderType') == 'LIMIT_BUY'
                    else 'SELL'
                )
                trade.amount = Decimal(historic_trade.get('Quantity'))
                trade.rate = Decimal(historic_trade.get('PricePerUnit'))
                trade.fee = Decimal(historic_trade.get('Commission'))
                trade.total = Decimal(
                    historic_trade.get('Quantity') * historic_trade.get('PricePerUnit')
                )
                trade.save()
