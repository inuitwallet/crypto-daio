from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^new$', views.new, name='new'),
    url(r'^add$', views.add, name='add'),
    url(r'^watch$', views.watch, name='watch'),
    url(r'^balance', views.balance, name='balance'),
]
