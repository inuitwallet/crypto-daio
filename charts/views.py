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
            info_objects = Info.objects.filter(unit=coin.unit_code).order_by('time_added')
            coin_data['coins'].append(
                {
                    'type': "lineWithFocusChart",
                    'name': 'Circulating {}'.format(coin.name),
                    'extra': {
                        'x_is_date': True,
                    },
                    'container': '{}_container'.format(coin.unit_code),
                    'data': {
                        'x': [
                            int(time.mktime(info_object.time_added.timetuple()) * 1000)
                            for info_object in info_objects
                        ],
                        'y1': [
                            float(info_object.money_supply)
                            for info_object in info_objects
                        ],
                        'name1': 'Circulating {}'.format(coin.name),
                        'extra1': extra_data,
                        'color_category': 'category10'
                    }
                }
            )

        return render(request, 'charts/circulating_currency.html', coin_data)

