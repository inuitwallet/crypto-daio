from __future__ import unicode_literals
from django.db import models


class Block(models.Model):
    """
    Object definition of a block
    """
    hash = models.CharField(
        max_length=610,
        unique=True,
    )
    size = models.BigIntegerField(
        blank=True,
        null=True,
    )
    height = models.BigIntegerField(
        blank=True,
        null=True,
        unique=True,
    )
    version = models.BigIntegerField(
        blank=True,
        null=True,
    )
    merkle_root = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    time = models.DateTimeField(
        blank=True,
        null=True,
    )
    nonce = models.BigIntegerField(
        blank=True,
        null=True,
    )
    bits = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    difficulty = models.FloatField(
        blank=True,
        null=True,
    )
    mint = models.FloatField(
        blank=True,
        null=True,
    )
    previous_block = models.ForeignKey(
        'Block',
        related_name='previous',
    )
    next_block = models.ForeignKey(
        'Block',
        related_name='next',
        blank=True,
        null=True,
    )
    flags = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    proof_hash = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    entropy_bit = models.BigIntegerField(
        blank=True,
        null=True,
    )
    modifier = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    modifier_checksum = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    coinage_destroyed = models.BigIntegerField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return str(self.hash)


class Transaction(models.Model):
    """
    A transaction within a block
    belongs to one block but can have multiple inputs and outputs
    """
    block = models.ForeignKey(
        Block,
        related_name='transactions',
        related_query_name='transaction',
    )
    tx_id = models.CharField(
        max_length=610,
        unique=True,
    )
    version = models.IntegerField()
    lock_time = models.IntegerField(
        blank=True,
        null=True,
    )
    is_coin_base = models.BooleanField()
    is_coin_stake = models.BooleanField()

    def __str__(self):
        return str(self.tx_id)


class TxInput(models.Model):
    """
    A transaction input.
    Belongs to a single transaction
    """
    transaction = models.ForeignKey(
        Transaction,
        related_name='inputs',
        related_query_name='input',
    )
    tx_id = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    v_out = models.BigIntegerField(
        blank=True,
        null=True,
    )
    coin_base = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    sequence = models.BigIntegerField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return str(self.pk)

    def Meta(self):
        self.unique_together = (self.tx_id, self.v_out)


class Address(models.Model):
    address = models.CharField(
        max_length=610,
        unique=True,
    )

    def __str__(self):
        return str(self.address)


class TxOutput(models.Model):
    transaction = models.ForeignKey(
        Transaction,
        related_name='outputs',
        related_query_name='output',
    )
    value = models.FloatField()
    n = models.IntegerField()
    script_pub_key_asm = models.TextField(
        max_length=610,
        blank=True,
        null=True,
    )
    script_pub_key_hex = models.TextField(
        max_length=610,
        blank=True,
        null=True,
    )
    script_pub_key_type = models.TextField(
        max_length=610,
        blank=True,
        null=True,
    )
    script_pub_key_req_sig = models.TextField(
        max_length=610,
        blank=True,
        null=True,
    )
    addresses = models.ManyToManyField(
        Address,
        related_name='output_addresses',
        related_query_name='output_address',
    )

    def __str__(self):
        return str(self.pk)

    def Meta(self):
        self.unique_together = (self.transaction, self.n)

    def is_unspent(self):
        """
        Check if the output has been used as an input on a different Tx
        :return: Boolean
        """
        return (
            False
            if TxInput.objects.filter(
                tx_id=self.transaction.tx_id
            )
            else True
        )


class CustodianVote(models.Model):
    pass


class MotionVote(models.Model):
    pass


class ParkRateVote(models.Model):
    pass


class FeesVote(models.Model):
    pass


class ParkRate(models.Model):
    pass


class WatchAddress(models.Model):
    address = models.ForeignKey(
        Address,
        related_name='watch_addresses',
        related_query_name='watch_address',
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=6
    )
    call_back = models.URLField(
        max_length=610,
    )
    complete = models.BooleanField(
        default=False,
    )
