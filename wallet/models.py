from __future__ import unicode_literals

import uuid

from django.db import models


class Wallet(models.Model):
    """
    This is the modular representation of a HD wallet mnemonic
    It is intended that an external service will send most of these details in the
    initial request
    """
    # this is the mnemonic to be saved
    mnemonic = models.CharField(
        max_length=255
    )


class ClientToken(models.Model):
    """
    Simple Auth token
    """
    token = models.UUIDField(
        default=uuid.uuid4,
    )


class Transaction(models.Model):
    """
    Contains a partial or full transaction made with a wallet address
    """
    wallet = models.ForeignKey(
        Wallet,
        related_name='transaction',
        related_query_name='transactions',
    )
    level = models.IntegerField()
    to_address = models.CharField(
        max_length=255,
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
    )
    fee = models.DecimalField(
        max_digits=20,
        decimal_places=8,
    )
    tx_id = models.CharField(
        max_length=255
    )
    complete = models.BooleanField()
    callback = models.URLField()
