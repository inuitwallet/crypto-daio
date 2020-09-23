import logging

from django.db import models

from blocks.models import Address
from daio.models import Coin

logger = logging.getLogger(__name__)


class CustodianVote(models.Model):
    block = models.ForeignKey("Block", blank=True, null=True, on_delete=models.CASCADE)
    address = models.ForeignKey(
        Address, blank=True, null=True, on_delete=models.SET_NULL
    )
    amount = models.DecimalField(max_digits=25, decimal_places=8, default=0)

    def __str__(self):
        return "{}:{}:{}".format(self.block, self.address, self.amount)

    class Meta:
        unique_together = ("block", "address", "amount")


class MotionVote(models.Model):
    block = models.ForeignKey("Block", blank=True, null=True, on_delete=models.CASCADE)
    hash = models.CharField(max_length=255, blank=True, null=True)
    block_percentage = models.FloatField(default=0)
    sdd_percentage = models.FloatField(default=0)

    class Meta:
        unique_together = ("block", "hash")


class FeesVote(models.Model):
    block = models.ForeignKey("Block", blank=True, null=True, on_delete=models.CASCADE)
    coin = models.ForeignKey(Coin, blank=True, null=True, on_delete=models.CASCADE)
    fee = models.FloatField(default=0)

    class Meta:
        unique_together = ("block", "coin", "fee")


class ParkRate(models.Model):
    blocks = models.IntegerField(default=0)
    rate = models.FloatField(default=0)

    def __str__(self):
        return "{}:{}".format(self.blocks, self.rate)

    class Meta:
        unique_together = ("blocks", "rate")
        ordering = ["blocks"]

    @property
    def days(self):
        """
        Return the approximate number of days this block period covers
        """
        return round((self.blocks / 60) / 24, 1)

    @property
    def years(self):
        return round(self.days / 365, 1)

    @property
    def daily_percentage(self):
        """
        Calculate the daily return from the rate (%APR)
        """
        return round(self.rate / 365, 8)

    @property
    def overall_return(self):
        """
        calculate the overall return if 1000 coin is parked at this rate for this length of time
        """
        return round((self.daily_percentage * self.days) * 1000, 8)


class ParkRateVote(models.Model):
    block = models.ForeignKey("Block", blank=True, null=True, on_delete=models.CASCADE)
    coin = models.ForeignKey(Coin, blank=True, null=True, on_delete=models.CASCADE)
    rates = models.ManyToManyField("ParkRate")

    class Meta:
        unique_together = ("block", "coin")
