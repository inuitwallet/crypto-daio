from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^circulating_currency$', views.CirculatingChart.as_view())
]
