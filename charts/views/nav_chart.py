import datetime
import time
from decimal import Decimal
from django.db import connection
from django.db.models import Min, Max, Avg
from django.utils.timezone import make_aware
from django.views import View

from charts.models import Balance


class NAVChart(View):
    @staticmethod
    def get(request):
        x_data = []
        y_data = {}
        low_date = Balance.objects.all().aggregate(
            Min('date_time')
        )
        low_date = low_date['date_time__min']
        max_date = Balance.objects.all().aggregate(
            Max('date_time')
        )
        max_date = max_date['date_time__max']

        exchanges = list(connection.tenant.exchanges.all())

        currency_totals = {}

        for exchange in exchanges:
            y_data[exchange.name] = {}
            currency_totals[exchange] = {}
            for currency in exchange.currencies.all():
                currency_totals[exchange][currency] = Decimal(0)

        while low_date < max_date:
            midnight = make_aware(
                datetime.datetime(
                    low_date.year,
                    low_date.month,
                    low_date.day,
                    0,
                    0,
                    0
                )
            )
            tomorrow = midnight + datetime.timedelta(days=1)
            day = int(time.mktime(tomorrow.timetuple()) * 1000)
            x_data.append(day)

            for exchange in exchanges:
                for pair in exchange.pairs.all():
                    balance = Balance.objects.filter(
                        pair=pair
                    ).filter(
                        time_added__gte=midnight
                    ).filter(
                        time_added__lt=tomorrow
                    ).aggregate(
                        Avg('base_amount')
                    ).aggregate(
                        Avg('quote_amount')
                    )

                    if currency_totals[exchange][pair.base_currency] == Decimal(0):
                        currency_totals[exchange][pair.base_currency] = balance[
                            'base_amount__avg']  # noqa

                    if currency_totals[exchange][pair.quote_currency] == Decimal(0):
                        currency_totals[exchange][pair.quote_currency] = balance[
                            'quote_amount__avg']  # noqa

                        # for currency in currency_totals[exchange]:
                        #     if currency.get_usd_value:

                        # y_data[coin.unit_code].append(
                        #     info['money_supply__avg']
                        #     if info ['money_supply__avg'] is not None
                        #     else 0
                        # )

                        # low_date = tomorrow
