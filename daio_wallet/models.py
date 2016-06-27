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
    token = models.CharField(
        max_length=255,
        default=uuid.uuid4,
        editable=False
    )
