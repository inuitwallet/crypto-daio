from django.conf.urls import include, url

import blocks.views as views

block_hash_pattern = r"([A-Za-z0-9]{64})"
secret_hash_pattern = r"([A-Za-z0-9]{32})"


urlpatterns = [
    # Daemon notification
    url(
        r"^notify/block/(?P<secret_hash>{})/(?P<block_hash>{})$".format(
            secret_hash_pattern, block_hash_pattern
        ),
        views.Notify.as_view(),
        name="notify",
    ),
    # Explorer
    url(r"^$", views.LatestBlocksList.as_view(), name="index"),
    url(r"^blocks$", views.AllBlocks.as_view(), name="blocks"),
    url(r"^block/(?P<block_height>.*)$", views.BlockDetailView.as_view(), name="block"),
    url(
        r"^address/(?P<address>.*)$", views.AddressDetailView.as_view(), name="address"
    ),
    url(r"^search$", views.Search.as_view(), name="search"),
    url(r"^health$", views.HealthView.as_view(), name="health"),
    # url(r'^menu/charts$', ChartsView.as_view(), name='charts_menu'),
    url(r"^motions$", views.MotionView.as_view(), name="motions"),
    url(r"^grants$", views.GrantView.as_view(), name="grants"),
    # API
    url(r"^api/v1/", include("blocks.api.urls.v1")),
]
