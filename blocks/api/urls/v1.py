from django.conf.urls import url
from blocks.api.views import v1


urlpatterns = [
    url(
        r'address/(?P<address>.*)/balance$',
        v1.AddressBalance.as_view(),
        name='v1.address_balance'
    ),
    url(
        r'coin/(?P<coin>.*)/supply/total$',
        v1.TotalSupply.as_view(),
        name='v1.total_supply'
    ),
    url(
        r'coin/(?P<coin>.*)/supply/parked$',
        v1.ParkedSupply.as_view(),
        name='v1.parked_supply'
    )
]
