import logging
from django.db import models
from blocks.models import Transaction
from models import TxInput

logger = logging.getLogger(__name__)


class Address(models.Model):
    address = models.CharField(
        max_length=610,
        unique=True,
        db_index=True,
    )

    def __str__(self):
        return self.address

    @property
    def class_type(self):
        return 'Address'

    @property
    def balance(self):
        balance = 0
        for output in self.outputs.all():
            try:
                if output.input:
                    continue
            except TxInput.DoesNotExist:
                balance += output.display_value
        return balance

    @property
    def transactions(self):
        transactions = []
        for output in self.outputs.all().order_by(
            'transaction__block__height'
        ).values_list(
            'transaction',
            flat=True
        ):
            if output in transactions:
                continue
            transactions.append(output)
        return [Transaction.objects.get(id=tx_pk) for tx_pk in transactions]


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
