
from django.db import models
from django.utils.timezone import now

from daio.models import Coin


class InfoManager(models.Manager):
    def get_closest_to(self, target):
        closest_greater_qs = self.filter(
            time_added__gt=target
        ).order_by(
            'time_added'
        )

        closest_less_qs = self.filter(
            time_added__lt=target
        ).order_by(
            '-time_added'
        )

        try:
            try:
                closest_greater = closest_greater_qs[0]
            except IndexError:
                return closest_less_qs[0]

            try:
                closest_less = closest_less_qs[0]
            except IndexError:
                return closest_greater_qs[0]
        except IndexError:
            raise self.model.DoesNotExist(
                "There is no closest value because there are no values."
            )

        if closest_greater.time_added - target > target - closest_less.time_added:
            return closest_less
        else:
            return closest_greater


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

    objects = InfoManager()

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


class Orphan(models.Model):
    hash = models.CharField(
        max_length=610,
        unique=True,
        db_index=True,
    )
    date_time = models.DateTimeField(
        default=now
    )


class ActiveParkRate(models.Model):
    block = models.ForeignKey(
        'Block',
        blank=True,
        null=True
    )
    coin = models.ForeignKey(
        Coin,
        blank=True,
        null=True
    )
    rates = models.ManyToManyField(
        'ParkRate'
    )


class NetworkFund(models.Model):
    """"
    Network owned funds that should be removed from the Circulating currency calculation
    """
    name = models.CharField(
        max_length=255
    )
    value = models.DecimalField(
        max_digits=25,
        decimal_places=8
    )
