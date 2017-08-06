import datetime

import logging

from decimal import Decimal

import itertools
from django.core.management import BaseCommand
from django.utils.timezone import make_aware

from alerts import providers
from alerts.models import BalanceAlert
from alerts.models.alerts import Notification, WatchedAddressBalanceAlert
from charts.models import Balance, WatchedAddressBalance

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    @staticmethod
    def send_notification(alert, value):
        # append additional data to alert message
        message = '{}\n\nCurrent Value ={}'.format(alert.message, value)

        # prepend the message with the icon if one exists
        if alert.icon:
            message = '<img src="{}" />\n\n{}'.format(alert.icon.url, message)

        for connector in alert.connectors.all():
            provider_wrapper = getattr(providers, connector.provider.title())
            provider = provider_wrapper(
                base_url=connector.base_url,
                api_key=connector.api_key,
                api_username=connector.api_user_name
            )
            logger.info('sending notification {} for {}'.format(connector, alert))
            provider.send_notification(connector.target_channel, message)

    def alert_comparison(self, alert, value):
        if alert.alert_operator == 'LESS_THAN':
            if Decimal(value) < Decimal(alert.alert_value):
                self.send_notification(alert, value)
                Notification.objects.create(content_object=alert)

        if alert.alert_operator == 'GREATER_THAN':
            if Decimal(value) > Decimal(alert.alert_value):
                self.send_notification(alert, value)
                Notification.objects.create(content_object=alert)

        if alert.alert_operator == 'EQUALS':
            if Decimal(value) == Decimal(alert.alert_value):
                self.send_notification(alert, value)
                Notification.objects.create(content_object=alert)

    def check_balance_alert(self, alert):
        # Get the balance to be checked
        balance = Balance.objects.filter(
            pair=alert.pair
        ).exclude(
            base_amount=None
        ).exclude(
            quote_amount=None
        ).order_by(
            '-date_time'
        ).first()

        check_balance = balance.base_amount

        if alert.currency == 'QUOTE':
            check_balance = balance.quote_amount

        self.alert_comparison(
            alert,
            check_balance
        )

    def check_watched_address_balance_alert(self, alert):
        # Get the balance to be checked
        watched_address_balance = WatchedAddressBalance.objects.filter(
            address=alert.address
        ).order_by(
            '-date_time'
        ).first()

        self.alert_comparison(
            alert,
            watched_address_balance.balance
        )

    @staticmethod
    def yield_alert():
        for alert in itertools.chain(BalanceAlert.objects.all(),
                                     WatchedAddressBalanceAlert.objects.all()):

            notification = alert.notifications.order_by('-date_time').first()

            if notification:
                if make_aware(datetime.datetime.now()) < notification.date_time + alert.period:  # noqa
                    logger.warning('period for {} has not yet elapsed'.format(alert))
                    continue

            logger.info('handling alert {}'.format(alert))

            yield alert

    def handle(self, *args, **options):
        """
        :param args:
        :param options:
        :return:
        """
        for alert in self.yield_alert():
            # handle balance_alerts
            if alert.__class__.__name__ == 'BalanceAlert':
                self.check_balance_alert(alert)

            # handle watched_address_balance_alerts
            if alert.__class__.__name__ == 'WatchedAddressBalanceAlert':
                self.check_watched_address_balance_alert(alert)
