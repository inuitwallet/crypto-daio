from django.contrib import admin
from .models import *


class BlockAdmin(admin.ModelAdmin):
    list_display = ('height', 'hash', 'time')
    ordering = ('-height',)

admin.site.register(Block, BlockAdmin)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('tx_id',)

admin.site.register(Transaction, TransactionAdmin)
admin.site.register(TxInput)
admin.site.register(TxOutput)
admin.site.register(Address)
admin.site.register(WatchAddress)
