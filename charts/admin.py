from django.contrib import admin

# Register your models here.
from charts.models import (
    Exchange,
    Currency,
    Pair,
    Balance,
    Trade,
    CurrencyValue,
    Order,
    Withdrawal,
    Deposit,
    WatchedAddress,
    WatchedAddressBalance,
)


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
    list_display = ('order_id', 'pair', 'date_time', 'order_type', 'amount', 'rate')
    search_fields = ('order_id', 'pair')
    raw_id_fields = ('pair',)

admin.site.register(Trade, TradeAdmin)


class OrderAdmin(admin.ModelAdmin):
    list_display = ('open', 'order_id', 'pair', 'date_time', 'order_type', 'amount', 'rate')  # noqa
    search_fields = ('order_id', 'pair')
    raw_id_fields = ('pair',)

admin.site.register(Order, OrderAdmin)


class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('complete', 'pair', 'exchange_tx_id', 'date_time', 'currency', 'amount', 'address')  # noqa
    search_fields = ('order_id', 'pair')
    raw_id_fields = ('currency', 'pair')

admin.site.register(Withdrawal, WithdrawalAdmin)


class DepositAdmin(admin.ModelAdmin):
    list_display = ('complete', 'pair', 'exchange_tx_id', 'date_time', 'currency', 'amount')  # noqa
    search_fields = ('order_id', 'pair')
    raw_id_fields = ('currency', 'pair')

admin.site.register(Deposit, DepositAdmin)


class WatchedAddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'currency')
    search_fields = ('address', 'currency')
    raw_id_fields = ('currency', )

admin.site.register(WatchedAddress, WatchedAddressAdmin)


class WatchedAddressBalanceAdmin(admin.ModelAdmin):
    list_display = ('date_time', 'address', 'balance')
    search_fields = ('address', 'date_time')
    raw_id_fields = ('address', )

admin.site.register(WatchedAddressBalance, WatchedAddressBalanceAdmin)
