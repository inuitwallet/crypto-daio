from django.conf.urls import url
from . import views

block_hash_pattern = r'([A-Za-z0-9]{64})'
secret_hash_pattern = r'([A-Za-z0-9]{32})'


urlpatterns = [

    # Daemon notification
    url(
        r'^notify/block/(?P<secret_hash>{})/(?P<block_hash>{})$'.format(
            secret_hash_pattern,
            block_hash_pattern
        ),
        views.Notify.as_view(),
        name='notify'
    ),

    # Explorer
    url(r'^$', views.LatestBlocksList.as_view(), name='index'),
    url(r'^block/(?P<block_height>.*)$', views.BlockDetailView.as_view(), name='block'),
]
