from django.conf.urls import url
from blocks.api.views import v1


urlpatterns = [
    url(
        r'address/(?P<address>.*)/balance$',
        v1.AddressBalance.as_view(),
        name='v1_address_balance'
    ),
    url(
        r'supply/(?P<coin>.*)/total$',
        v1.TotalSupply.as_view(),
        name='v1_total_supply'
    )
]
