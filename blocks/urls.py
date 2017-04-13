from django.conf.urls import url
from . import views

base64_pattern = r'(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$'

urlpatterns = [

    # Daemon notification
    url(
        r'^notify/block/(?P<block_hash>{})'.format(base64_pattern),
        views.Notify.as_view(),
        name='notify'
    ),

    # Explorer
    url(r'^', views.LatestBlocksList.as_view(), name='index'),
]
