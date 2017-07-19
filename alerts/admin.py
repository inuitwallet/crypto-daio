from django.contrib import admin

from alerts.models import Alert


class AlertAdmin(admin.ModelAdmin):
    list_display = ('content_type', 'alert_operator', 'alert_value')
    raw_id_fields = ('content_type',)

admin.site.register(Alert, AlertAdmin)
