from django.contrib import admin
from .models import Chain, Coin


class ChainAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

admin.site.register(Chain, ChainAdmin)


class CoinAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'unit_code', 'chain', 'rpc_port')
    search_fields = ('name', 'code', 'unit_code', 'chain')

admin.site.register(Coin, CoinAdmin)
