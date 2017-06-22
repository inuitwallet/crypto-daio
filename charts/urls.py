from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^trade_table', views.TradeValueTable.as_view()),
    url(r'^usd_nav$', views.NAVChart.as_view()),
    url(r'^circulating_currency$', views.CirculatingChart.as_view()),
]
