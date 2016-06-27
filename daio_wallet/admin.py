from django.contrib import admin
from .models import *


class TokenAdmin(admin.ModelAdmin):
    list_display = ('token',)

admin.site.register(ClientToken, TokenAdmin)
admin.site.register(Wallet)
