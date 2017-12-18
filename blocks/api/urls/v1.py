from django.conf.urls import url
from api.views import v1


urlpatterns = [
    url(
        r'address/(?P<address>.*)/balance$',
        v1.AddressBalance.as_view(),
        name='v1_address_balance'
    )
]
