import requests

from charts.models import CurrencyValue


class CoinMarketCap(object):

    @staticmethod
    def get_usd_values(currencies):
        response = requests.get(
            url='https://api.coinmarketcap.com/v1/ticker/'
        )
        currency_details = response.json()
        for currency_detail in currency_details:
            for currency in currencies:
                if currency_detail.get('symbol') == currency.code:
                    CurrencyValue.objects.create(
                        currency=currency,
                        usd_value=currency_detail.get('price_usd')
                    )
