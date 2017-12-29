import logging
from django.db import models

from daio.models import Coin
from blocks.models import Address

logger = logging.getLogger(__name__)


class CustodianVote(models.Model):
    block = models.ForeignKey(
        'Block',
        blank=True,
        null=True
    )
    address = models.ForeignKey(
        Address,
        blank=True,
        null=True
    )
    amount = models.DecimalField(
        max_digits=25,
        decimal_places=8,
        default=0
    )

    def __str__(self):
        return '{}:{}:{}'.format(self.block, self.address, self.amount)

    class Meta:
        unique_together = ("block", "address", "amount")


class MotionVote(models.Model):
    block = models.ForeignKey(
        'Block',
        blank=True,
        null=True
    )
    hash = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        unique_together = ("block", "hash")


class FeesVote(models.Model):
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
    fee = models.DecimalField(
        max_digits=25,
        decimal_places=10,
        default=0
    )

    class Meta:
        unique_together = ("block", "coin", "fee")


class ParkRate(models.Model):
    blocks = models.IntegerField(
        default=0
    )
    rate = models.DecimalField(
        max_digits=25,
        decimal_places=10,
        default=0
    )

    def __str__(self):
        return '{}:{}'.format(self.blocks, self.rate)

    class Meta:
        unique_together = ("blocks", "rate")


class ParkRateVote(models.Model):
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

    class Meta:
        unique_together = ("block", "coin")
