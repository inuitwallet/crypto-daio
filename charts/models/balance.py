from django.db import models

from .exchange import Pair


class BalanceManager(models.Manager):
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


class Balance(models.Model):
    pair = models.ForeignKey(
        Pair,
        related_name='balances',
        related_query_name='balance'
    )
    date_time = models.DateTimeField(auto_now=True)
    base_amount = models.DecimalField(
        max_digits=26,
        decimal_places=10,
        blank=True,
        null=True
    )
    quote_amount = models.DecimalField(
        max_digits=26,
        decimal_places=10,
        blank=True,
        null=True
    )

    objects = BalanceManager()

    def __str__(self):
        return '{} {}/{} {}'.format(
            self.pair.quote_currency.code,
            self.quote_amount,
            self.pair.base_currency.code,
            self.base_amount
        )
