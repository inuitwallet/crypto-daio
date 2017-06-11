import datetime
import time

from django.db import connection
from django.shortcuts import render
from django.views import View

from blocks.models import Info


class CirculatingChart(View):
    @staticmethod
    def get(request):
        coin_data = {'coins': []}
        extra_data = {
            "tooltip": {
                "y_start": "There are ",
                "y_end": " circulating"
            },
            "date_format": "%d %b %Y %H:%M:%S %p"
        }

        for coin in connection.tenant.coins.all():
            info_objects = Info.objects.filter(
                unit=coin.unit_code
            ).order_by(
                'time_added'
            )

            x_data = []
            y_data = []
            y_value = 0.0

            day_count = 0
            for info_object in info_objects:
                day = int(
                    time.mktime(
                        datetime.datetime(
                            info_object.time_added.year,
                            info_object.time_added.month,
                            info_object.time_added.day,
                            0,
                            0,
                            0
                        ).timetuple()
                    ) * 1000
                )

                if len(x_data) == 0:
                    x_data.append(day)

                if day not in x_data:
                    y_data.append(y_value / day_count)
                    x_data.append(day)
                    y_value = 0.0
                    day_count = 0

                y_value += float(info_object.money_supply)
                day_count += 1

            y_data.append(y_value / day_count)

            coin_data['coins'].append(
                {
                    'type': "lineChart",
                    'name': 'Circulating {}'.format(coin.name),
                    'extra': {
                        'x_is_date': True,
                    },
                    'container': '{}_container'.format(coin.unit_code),
                    'data': {
                        'x': x_data,
                        'y1': y_data,
                        'name1': 'Circulating {}'.format(coin.name),
                        'extra1': extra_data,
                        'color_category': 'category10'
                    }
                }
            )

        return render(request, 'charts/circulating_currency.html', coin_data)

