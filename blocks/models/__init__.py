from django.db import models
from .transaction import Transaction, TxInput, TxOutput
from .address import Address, WatchAddress
from .votes import CustodianVote, MotionVote, ParkRateVote, FeesVote, ParkRate
from .block import Block

__all__ = [
    'Block',
    'Transaction',
    'TxInput',
    'TxOutput',
    'Address',
    'WatchAddress',
    'CustodianVote',
    'MotionVote',
    'ParkRateVote',
    'FeesVote',
    'ParkRate',
    'Info',
    'Peer',
]


class Info(models.Model):
    unit = models.CharField(
        max_length=255
    )
    max_height = models.BigIntegerField()
    money_supply = models.DecimalField(
        max_digits=16,
        decimal_places=4
    )
    total_parked = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        blank=True,
        null=True
    )
    connections = models.BigIntegerField()
    difficulty = models.DecimalField(
        max_digits=16,
        decimal_places=10
    )
    pay_tx_fee = models.DecimalField(
        max_digits=16,
        decimal_places=4
    )
    time_added = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return '{}:{}@{}'.format(self.unit, self.max_height, self.time_added)


class Peer(models.Model):
    address = models.GenericIPAddressField(
        unique=True
    )
    port = models.IntegerField()
    services = models.IntegerField()
    last_send = models.DateTimeField()
    last_receive = models.DateTimeField()
    connection_time = models.DateTimeField()
    version = models.IntegerField()
    sub_version = models.CharField(
        max_length=255
    )
    inbound = models.BooleanField()
    release_time= models.IntegerField()
    height = models.IntegerField()
    ban_score = models.IntegerField()

    def __str__(self):
        return '{}:{}@{}'.format(self.address, self.port, self.height)
