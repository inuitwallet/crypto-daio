from django.contrib import admin

from .models import *


class BlockAdmin(admin.ModelAdmin):
    list_display = ('height', 'hash', 'time')
    search_fields = ('height', 'hash')
    ordering = ('-height',)
    raw_id_fields = ('previous_block', 'next_block')


admin.site.register(Block, BlockAdmin)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('index', 'tx_id', 'block', 'coin')
    search_fields = ('tx_id',)
    ordering = ('block',)
    raw_id_fields = ('block', 'coin')


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
    raw_id_fields = ('transaction', 'address')


admin.site.register(TxOutput, TxOutputAdmin)


class AddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'balance', 'network_owned')
    search_fields = ('address',)


admin.site.register(Address, AddressAdmin)


class WatchAddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'amount', 'call_back', 'complete')


admin.site.register(WatchAddress, WatchAddressAdmin)


class NetworkFundAdmin(admin.ModelAdmin):
    list_display = ('name', 'value')


admin.site.register(NetworkFund, NetworkFundAdmin)


class CustodianVoteAdmin(admin.ModelAdmin):
    list_display = ('block', 'address', 'amount')


admin.site.register(CustodianVote, CustodianVoteAdmin)


class MotionVoteAdmin(admin.ModelAdmin):
    list_display = ('block', 'hash')


admin.site.register(MotionVote, MotionVoteAdmin)


class FeesVoteAdmin(admin.ModelAdmin):
    list_display = ('block', 'coin', 'fee')


admin.site.register(FeesVote, FeesVoteAdmin)


class ParkRateVoteAdmin(admin.ModelAdmin):
    list_display = ('block', 'coin')


admin.site.register(ParkRateVote, ParkRateVoteAdmin)


class ActiveParkRateAdmin(admin.ModelAdmin):
    list_display = ('block', 'coin')


admin.site.register(ActiveParkRate, ActiveParkRateAdmin)
