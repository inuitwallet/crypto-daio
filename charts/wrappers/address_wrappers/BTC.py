import requests

from charts.models import WatchedAddressBalance


class BTC(object):

    def __init__(self):
        self.supported_currencies = ['BTC']

    def get_address_balance(self, watched_address):
        response = requests.get(
            url='https://blockchain.info/q/addressbalance/{}'.format(
                watched_address.address
            )
        )
        satoshi_balance = int(response.text)
        WatchedAddressBalance.objects.create(
            address=watched_address,
            balance=satoshi_balance/100000000
        )
