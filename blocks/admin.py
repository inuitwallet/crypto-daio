from django.contrib import admin
from .models import *


class BlockAdmin(admin.ModelAdmin):
    list_display = ('height', 'hash', 'time')
    search_fields = ('height', 'hash')
    ordering = ('-height',)
    raw_id_fields = ('previous_block', 'next_block')

admin.site.register(Block, BlockAdmin)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('index', 'tx_id', 'block')
    search_fields = ('tx_id',)
    ordering = ('block',)
    raw_id_fields = ('block',)

admin.site.register(Transaction, TransactionAdmin)


class TxInputAdmin(admin.ModelAdmin):
    list_display = ('index', 'transaction', 'previous_output')
    search_fields = ('transaction', 'previous_output')
    ordering = ('transaction',)
    raw_id_fields = ('transaction',)

admin.site.register(TxInput, TxInputAdmin)


class TxOutputAdmin(admin.ModelAdmin):
    list_display = ('index', 'transaction', 'index', 'value')
    search_fields = ('transaction',)
    ordering = ('transaction',)
    raw_id_fields = ('transaction', 'addresses')

admin.site.register(TxOutput, TxOutputAdmin)


class AddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'balance')

admin.site.register(Address, AddressAdmin)


class WatchAddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'amount', 'call_back', 'complete')

admin.site.register(WatchAddress, WatchAddressAdmin)
