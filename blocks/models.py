from __future__ import unicode_literals

from decimal import Decimal
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
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    next_block = models.ForeignKey(
        'Block',
        related_name='next',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
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

    @property
    def class_type(self):
        return 'Block'


class Transaction(models.Model):
    """
    A transaction within a block
    belongs to one block but can have multiple inputs and outputs
    """
    block = models.ForeignKey(
        Block,
        related_name='transactions',
        related_query_name='transaction',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    tx_id = models.CharField(
        max_length=610,
        unique=True,
    )
    version = models.IntegerField(
        blank=True,
        null=True,
    )
    lock_time = models.IntegerField(
        blank=True,
        null=True,
    )
    unit = models.CharField(
        max_length=15,
        blank=True,
        null=True,
    )
    is_coin_base = models.NullBooleanField()
    is_coin_stake = models.NullBooleanField()

    def __str__(self):
        return str(self.tx_id)

    @property
    def class_type(self):
        return 'Transaction'


class TxInput(models.Model):
    """
    A transaction input.
    Belongs to a single transaction
    """
    transaction = models.ForeignKey(
        Transaction,
        related_name='inputs',
        related_query_name='input',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    tx_id = models.CharField(
        max_length=610,
        blank=True,
        null=True,
    )
    output_transaction = models.ForeignKey(
        Transaction,
        related_name='inout_txs',
        related_query_name='inout_tx',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
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
    script_sig_asm = models.TextField(
        blank=True,
        null=True,
    )
    script_sig_hex = models.TextField(
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

    @property
    def class_type(self):
        return 'Address'

    @property
    def balance(self):
        value = Decimal(0.0)
        # get the outputs for the address
        outputs = TxOutput.objects.filter(
            addresses__address=self.address,
            is_unspent=True,
        )
        for output in outputs:
            value += Decimal(output.value)
        return value


class TxOutput(models.Model):
    transaction = models.ForeignKey(
        Transaction,
        related_name='outputs',
        related_query_name='output',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
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
        related_query_name='tx_output',
    )
    is_unspent = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return str(self.pk)

    def Meta(self):
        self.unique_together = (self.transaction, self.n)
        ordering = '-n'


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
