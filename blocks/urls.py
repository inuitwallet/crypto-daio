from django.conf.urls import url
from . import views

base64_pattern = r'(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$'

urlpatterns = [
    url(
        r'^notify/(?P<block_hash>{})'.format(base64_pattern),
        views.notify,
        name='notify'
    ),
    url(r'^parse/', views.parse, name='parse'),
    url(r'^blocks/$', views.BlockList.as_view(), name='all_blocks'),
    url(r'^block/(?P<block_hash>\w+)', views.BlockDetail.as_view(), name='get_block'),
    url(r'^tx/(?P<tx_id>\w+)', views.TransactionDetail.as_view(), name='get_tx'),
]
