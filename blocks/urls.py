from django.conf.urls import url
from . import views
from blocks.views import BlockView

base64_pattern = r'(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$'

urlpatterns = [
    url(
        r'^notify/(?P<block_hash>{})'.format(base64_pattern),
        views.notify,
        name='notify'
    ),
    url(r'^all/$', BlockView.as_view(), name='all_blocks'),
    url(r'^(?P<block_height>\d+)', views.get_block, name='get_block'),
    url(r'^parse/', views.parse, name='parse'),
]
