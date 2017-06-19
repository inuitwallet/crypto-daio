from django.contrib import admin

# Register your models here.
from charts.models import Exchange, Currency, Pair, Balance, Trade, CurrencyValue


class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'chain')
    search_fields = ('name', )
    raw_id_fields = ('chain', )

admin.site.register(Exchange, ExchangeAdmin)


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'get_usd_value')
    search_fields = ('name', 'code')

admin.site.register(Currency, CurrencyAdmin)


class CurrencyValueAdmin(admin.ModelAdmin):
    list_display = ('currency', 'usd_value', 'date_time')
    search_fields = ('currency', )

admin.site.register(CurrencyValue, CurrencyValueAdmin)


class PairAdmin(admin.ModelAdmin):
    list_display = ('name', 'exchange', 'base_currency', 'quote_currency')
    search_fields = ('name', 'exchange')
    raw_id_fields = ('exchange',)

admin.site.register(Pair, PairAdmin)


class BalanceAdmin(admin.ModelAdmin):
    list_display = ('pair', 'date_time', 'base_amount', 'quote_amount')
    search_fields = ('pair',)
    raw_id_fields = ('pair',)

admin.site.register(Balance, BalanceAdmin)


class TradeAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'pair', 'date_time')
    search_fields = ('order_id', 'pair')
    raw_id_fields = ('pair',)

admin.site.register(Trade, TradeAdmin)
