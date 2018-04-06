from django.conf.urls import url, include
from blocks.views import *

block_hash_pattern = r'([A-Za-z0-9]{64})'
secret_hash_pattern = r'([A-Za-z0-9]{32})'


urlpatterns = [

    # Daemon notification
    url(
        r'^notify/block/(?P<secret_hash>{})/(?P<block_hash>{})$'.format(
            secret_hash_pattern,
            block_hash_pattern
        ),
        Notify.as_view(),
        name='notify'
    ),

    # Explorer
    url(r'^$', LatestBlocksList.as_view(), name='index'),
    url(r'^blocks$', AllBlocks.as_view(), name='blocks'),
    url(r'^block/(?P<block_height>.*)$', BlockDetailView.as_view(), name='block'),
    url(r'^address/(?P<address>.*)$', AddressDetailView.as_view(), name='address'),

    url(r'^search$', Search.as_view(), name='search'),

    url(r'^health$', HealthView.as_view(), name='health'),

    url(r'^menu/charts$', ChartsView.as_view(), name='charts_menu'),

    url(r'^motions$', MotionView.as_view(), name='motions'),
    url(r'^grants$', GrantView.as_view(), name='grants'),

    url(r'^angular$', AngularExplorer.as_view(), name='angular_explorer'),

    # API
    url(r'^api/v1/', include('blocks.api.urls.v1'))
]
