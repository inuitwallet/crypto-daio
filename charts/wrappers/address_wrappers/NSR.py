from charts.models import WatchedAddressBalance
from blocks.models import Address


class NSR(object):
    @staticmethod
    def get_address_balance(watched_address):
        try:
            address = Address.objects.get(address=watched_address.address)
            balance = address.balance
        except Address.DoesNotExist:
            balance = None

        WatchedAddressBalance.objects.create(
            address=watched_address,
            balance=balance
        )
