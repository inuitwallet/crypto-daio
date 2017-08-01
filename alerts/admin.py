from django.contrib import admin

from alerts.models import (
    BalanceAlert,
    Connector,
    Notification
)


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('date_time', 'content_object',)

admin.site.register(Notification, NotificationAdmin)


class ConnectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'base_url', 'api_user_name', 'target_channel')
    search_fields = ('name', 'provider', 'base_url', 'api_user_name')

admin.site.register(Connector, ConnectorAdmin)


class BalanceAlertAdmin(admin.ModelAdmin):
    list_display = ('pair', 'currency', 'alert_operator', 'alert_value', 'period')

admin.site.register(BalanceAlert, BalanceAlertAdmin)
