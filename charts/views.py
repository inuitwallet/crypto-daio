import datetime
import time

from django.db import connection
from django.db.models import Min, Max, Avg
from django.shortcuts import render
from django.utils.timezone import make_aware
from django.views import View

from blocks.models import Info


class CirculatingChart(View):
    @staticmethod
    def get(request):
        x_data = []
        y_data = {}

        low_date = Info.objects.all().aggregate(
            Min('time_added')
        )
        low_date = low_date['time_added__min']
        max_date = Info.objects.all().aggregate(
            Max('time_added')
        )
        max_date = max_date['time_added__max']

        coins = list(connection.tenant.coins.all())

        for coin in coins:
            y_data[coin.unit_code] = []

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

            for coin in coins:
                info = Info.objects.filter(
                    unit=coin.unit_code
                ).aggregate(
                    Avg('money_supply')
                )
                y_data[coin.unit_code].append(info['money_supply__avg'])

            low_date = tomorrow

        series_data = {'x': x_data}
        index = 1

        for coin in coins:
            series_data['y{}'.format(index)] = y_data[coin.unit_code]
            series_data['name{}'.format(index)] = 'Circulating {}'.format(coin.name)
            series_data['extra{}'.format(index)] = {
                "tooltip": {
                    "y_start": "There are ",
                    "y_end": " circulating"
                },
                "date_format": "%d %b %Y %H:%M:%S %p"
            }
            index += 1

        chart_data = {
            'chart_type': "lineChart",
            'name': 'Circulating Currency',
            'series_data': series_data,
            'extra': {
                'x_is_date': True,
                'color_category': 'category10',
            },

        }

        print(chart_data)

        return render(request, 'charts/circulating_currency.html', chart_data)

