import datetime

from django.db import connection
from django.shortcuts import render
from django.utils.timezone import make_aware
from django.views import View

from charts.models import Balance, CurrencyValue


class LiquidityOperations(View):
    @staticmethod
    def get(request):
        # get the latest balances for latest table
        latest_balances_dedupe = []
        latest_balances = []
        for exchange in connection.tenant.exchanges.all():
            print(exchange)
            for pair in exchange.pairs.all():
                latest_balance = Balance.objects.get_closest_to(
                    pair,
                    datetime.datetime.now()
                )

                time_warning = 'success'
                if latest_balance.date_time < make_aware(datetime.datetime.now() - datetime.timedelta(minutes=2)):  # noqa
                    time_warning = 'danger'

                if (pair.quote_currency, pair.exchange) not in latest_balances_dedupe:
                    quote_amount = latest_balance.quote_amount
                    quote_amount_usd = quote_amount
                    quote_value = 1

                    if pair.quote_currency.get_usd_value:
                        quote_value = CurrencyValue.objects.get_closest_to(
                            pair.quote_currency,
                            datetime.datetime.now()
                        ).usd_value
                        quote_amount_usd = quote_amount * quote_value
                    latest_balances.append(
                        {
                            'currency': pair.quote_currency,
                            'exchange': pair.exchange,
                            'value': quote_amount,
                            'value_usd': quote_amount_usd,
                            'usd_price': quote_value,
                            'time': latest_balance.date_time,
                            'time_warning': time_warning
                        }
                    )
                    latest_balances_dedupe.append((pair.quote_currency, pair.exchange))

                if (pair.base_currency, pair.exchange) not in latest_balances_dedupe:
                    base_amount = latest_balance.base_amount
                    base_amount_usd = base_amount
                    base_value = 1

                    if pair.base_currency.get_usd_value:
                        base_value = CurrencyValue.objects.get_closest_to(
                            pair.base_currency,
                            datetime.datetime.now()
                        ).usd_value
                        base_amount_usd = base_amount * base_value
                    latest_balances.append(
                        {
                            'currency': pair.base_currency,
                            'exchange': pair.exchange,
                            'value': base_amount,
                            'value_usd': base_amount_usd,
                            'usd_price': base_value,
                            'time': latest_balance.date_time,
                            'time_warning': time_warning
                        }
                    )
                    latest_balances_dedupe.append((pair.base_currency, pair.exchange))

        context = {
            'chain': connection.tenant,
            'latest_balances': latest_balances
        }
        return render(request, 'charts/liquidity_operations.html', context)
