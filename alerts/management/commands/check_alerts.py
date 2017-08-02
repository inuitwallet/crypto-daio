import datetime

import logging

from decimal import Decimal
from django.core.management import BaseCommand
from django.utils.timezone import make_aware

from alerts import providers
from alerts.models import BalanceAlert
from alerts.models.alerts import Notification
from charts.models import Balance

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    @staticmethod
    def send_notification(alert, message):
        for connector in alert.connectors.all():
            provider_wrapper = getattr(providers, connector.provider.title())
            provider = provider_wrapper(
                base_url=connector.base_url,
                api_key=connector.api_key,
                api_username=connector.api_user_name
            )
            provider.send_notification(connector.target_channel, message)
            logger.info('sending notification {} for {}'.format(connector, alert))

    def check_balance_alerts(self):
        """
        Fetch each Balance Alert and check their conditions.
        Send Appropriate notifications when conditions are met
        :return:
        """
        for alert in BalanceAlert.objects.all():
            # Check that the same alert hasn't been sent within the last period
            notification = Notification.objects.filter(
                alerts=alert
            ).order_by(
                '-date_time'
            ).first()

            if notification:
                if make_aware(datetime.datetime.now()) < notification.date_time + alert.period:  # noqa
                    logger.warning('period has not yet elapsed')
                    continue

            # Get the balance to be checked
            balance = Balance.objects.filter(
                pair=alert.pair
            ).order_by(
                '-date_time'
            ).first()

            check_balance = balance.base_amount
            check_currency = alert.pair.base_currency

            if alert.currency == 'QUOTE':
                check_balance = balance.quote_amount
                check_currency = alert.pair.quote_currency

            logger.info(
                'balance: {} {} {}'.format(
                    balance.date_time,
                    balance.quote_amount,
                    balance.base_amount
                )
            )

            if alert.alert_operator == 'LESS_THAN':
                if Decimal(check_balance) < Decimal(alert.alert_value):
                    self.send_notification(
                        alert,
                        'The balance of {} on {} has fallen below {}.\n'
                        'The Current Balance is {}'.format(
                            check_currency,
                            alert.pair.exchange,
                            alert.alert_value,
                            check_balance
                        )
                    )
                    Notification.objects.create(content_object=alert)

            if alert.alert_operator == 'GREATER_THAN':
                if Decimal(check_balance) > Decimal(alert.alert_value):
                    self.send_notification(
                        alert,
                        'The balance of {} on {} has risen above {}.\n'
                        'The Current Balance is {}'.format(
                            check_currency,
                            alert.pair.exchange,
                            alert.alert_value,
                            check_balance
                        )
                    )
                    Notification.objects.create(content_object=alert)

            if alert.alert_operator == 'EQUALS':
                if Decimal(check_balance) == Decimal(alert.alert_value):
                    self.send_notification(
                        alert,
                        'The balance of {} on {} equals {}.'.format(
                            check_currency,
                            alert.pair.exchange,
                            alert.alert_value,
                        )
                    )
                    Notification.objects.create(content_object=alert)

    def handle(self, *args, **options):
        """

        :param args:
        :param options:
        :return:
        """
        self.check_balance_alerts()
