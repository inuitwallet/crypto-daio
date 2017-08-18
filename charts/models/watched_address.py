from django.db import models

from charts.models import Currency


class WatchedAddress(models.Model):
    address = models.CharField(
        max_length=610,
    )
    currency = models.ForeignKey(
        Currency
    )

    def __str__(self):
        return self.address


class WatchedAddressBalanceManager(models.Manager):
    def get_closest_to(self, address, target):
        closest_greater_qs = self.filter(
            address__address=address
        ).filter(
            date_time__gt=target
        ).order_by(
            'date_time'
        )

        closest_less_qs = self.filter(
            address__address=address
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


class WatchedAddressBalance(models.Model):
    date_time = models.DateTimeField(
        auto_now=True
    )
    address = models.ForeignKey(
        WatchedAddress
    )
    balance = models.DecimalField(
        max_digits=26,
        decimal_places=10,
        blank=True,
        null=True
    )

    objects = WatchedAddressBalanceManager()

    def __str__(self):
        return '{}@{}:{}'.format(self.address, self.date_time, self.balance)
