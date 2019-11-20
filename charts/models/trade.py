from django.db import models

from charts.models import Pair


class TradeManager(models.Manager):
    def get_closest_to(self, pair, target):
        closest_greater_qs = self.filter(
            pair=pair
        ).filter(
            date_time__gt=target
        ).order_by(
            'date_time'
        )

        closest_less_qs = self.filter(
            pair=pair
        ).filter(
            date_time__lt=target
        ).order_by(
            '-date_time'
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

        if closest_greater.date_time - target > target - closest_less.date_time:
            return closest_less
        else:
            return closest_greater


class Trade(models.Model):
    order_id = models.CharField(max_length=255)
    pair = models.ForeignKey(
        Pair,
        related_name='orders',
        related_query_name='order'
    )
    date_time = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True
    )
    order_type = models.CharField(
        max_length=255,
        choices=[
            ('BUY', 'Buy'),
            ('SELL', 'Sell')
        ],
        blank=True,
        null=True
    )
    amount = models.DecimalField(max_digits=26, decimal_places=10, blank=True, null=True)
    rate = models.DecimalField(max_digits=26, decimal_places=10, blank=True, null=True)
    total = models.DecimalField(max_digits=26, decimal_places=10, blank=True, null=True)
    fee = models.DecimalField(max_digits=26, decimal_places=10, blank=True, null=True)

    objects = TradeManager()

    def __str__(self):
        return '{}@{}'.format(self.order_id, self.pair)

    class Meta:
        unique_together = ('order_id', 'pair')
        ordering = ('-date_time',)


class Order(Trade):
    open = models.BooleanField(default=True)
    remaining = models.DecimalField(
        max_digits=26,
        decimal_places=10,
        blank=True,
        null=True
    )
