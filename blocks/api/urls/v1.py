from django.conf.urls import url
from blocks.api.views import v1


urlpatterns = [
    # Address API
    url(
        r'address/(?P<address>.*)/balance$',
        v1.AddressBalance.as_view(),
        name='v1.address_balance'
    ),
    url(
        r'address/(?P<address>.*)/unspent$',
        v1.AddressUnspent.as_view(),
        name='v1.address_unspent'
    ),

    # Transaction API
    url(
        r'tx/broadcast$',
        v1.TransactionBroadcast.as_view(),
        name='v1.tx_broadcast'
    ),
    url(
        r'tx/(?P<transaction>.*)/outputs$',
        v1.TransactionOutputs.as_view(),
        name='v1.tx_outputs'
    ),

    # Coin API
    url(
        r'coin/(?P<coin>.*)/supply/total$',
        v1.TotalSupply.as_view(),
        name='v1.total_supply'
    ),
    url(
        r'coin/(?P<coin>.*)/supply/parked$',
        v1.ParkedSupply.as_view(),
        name='v1.parked_supply'
    ),
    url(
        r'coin/(?P<coin>.*)/supply/circulating$',
        v1.CirculatingSupply.as_view(),
        name='v1.circulating_supply'
    ),
    url(
        r'coin/(?P<coin>.*)/network_funds$',
        v1.NetworkFunds.as_view(),
        name='v1.network_funds'
    ),

    # Wallet Trusted Server
    url(
        r'getvalidhashes$',
        v1.GetValidHashes.as_view(),
        name='v1.getvalidhashes'
    ),

    # Active Peers
    url(
        r'active_peers$',
        v1.ActivePeers.as_view(),
        name='v1.active_peers'
    ),

    # Park Rates
    url(
        r'active_park_rates/(?P<block_height>.*)$',
        v1.ParkRateData.as_view(),
        name='v1.active_park_rates'
    ),
]
