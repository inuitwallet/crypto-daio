from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^trade_table', TradeValueTable.as_view(), name='trade_table'),
    url(r'^usd_nav$', NAVChart.as_view()),
    url(r'^circulating_currency$', CirculatingChart.as_view()),
    url(r'^current_liquidity$', CurrentLiquidityChart.as_view()),
]
