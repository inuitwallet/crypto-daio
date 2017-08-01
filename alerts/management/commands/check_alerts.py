from django.core.management import BaseCommand

from alerts.models import BalanceAlert
from charts.models import Balance


class Command(BaseCommand):

    def check_balance_alerts(self):
        """
        Fetch each Balance Alert and check their conditions.
        Send Appropriate notifications when conditions are met
        :return:
        """
        for alert in BalanceAlert.objects.all():
            # Get the balance to be checked
            balance = Balance.objects.filter(
                pair=alert.pair
            ).order_by(
                '-date_time'
            ).first()
            print('balance = {}'.format(balance))
            # check their conditions
        # send notification appropriately

    def handle(self, *args, **options):
        """

        :param args:
        :param options:
        :return:
        """

