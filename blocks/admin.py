from django.contrib import admin
from .models import *


class BlockAdmin(admin.ModelAdmin):
    list_display = ('height', 'hash', 'time')
    ordering = ('-height',)

admin.site.register(Block, BlockAdmin)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('block', 'tx_id', 'is_coin_base', 'is_coin_stake')

admin.site.register(Transaction, TransactionAdmin)


class TxInputAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'tx_id', 'v_out')

admin.site.register(TxInput, TxInputAdmin)


class TxOutputAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'n', 'value')

admin.site.register(TxOutput, TxOutputAdmin)


class AddressAdmin(admin.ModelAdmin):
    list_display = ('address',)

admin.site.register(Address, AddressAdmin)


class WatchAddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'amount', 'callback', 'complete')

admin.site.register(WatchAddress, WatchAddressAdmin)
