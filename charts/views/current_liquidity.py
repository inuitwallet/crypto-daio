from django.db import connection
from django.shortcuts import render
from django.views import View


class CurrentLiquidityChart(View):
    """
    Get open orders and graph them
    x axis = price
    y axis = amount in usd
    line for buy, line for sell for each pair/exchange
    """

    @staticmethod
    def get(request):
        return render(
            request,
            'charts/current_liquidity.html',
            {'chain': connection.tenant}
        )
