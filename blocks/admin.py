from django.contrib import admin
from .models import *


class BlockAdmin(admin.ModelAdmin):
    list_display = ('height', 'hash', 'time')
    ordering = ('-height',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        this_block = Block.objects.get(id=request.path.split('/')[4])
        if db_field.name == 'previous_block':
            if this_block.previous_block:
                kwargs["queryset"] = Block.objects.filter(id=this_block.previous_block.id)
            else:
                kwargs["queryset"] = Block.objects.none()
        if db_field.name == 'next_block':
            if this_block.next_block:
                kwargs["queryset"] = Block.objects.filter(id=this_block.next_block.id)
            else:
                kwargs["queryset"] = Block.objects.none()
        return super(BlockAdmin, self).formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )

admin.site.register(Block, BlockAdmin)


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('block', 'tx_id', 'is_coin_base', 'is_coin_stake')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'block':
            tx = Transaction.objects.get(id=request.path.split('/')[4])
            kwargs["queryset"] = Block.objects.filter(id=tx.block.id)
        return super(TransactionAdmin, self).formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )

admin.site.register(Transaction, TransactionAdmin)


class TxInputAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'tx_id', 'v_out')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'transaction':
            tx_input = TxInput.objects.get(id=request.path.split('/')[4])
            kwargs["queryset"] = Transaction.objects.filter(id=tx_input.transaction.id)
        if db_field.name == 'output_transaction':
            tx_input = TxInput.objects.get(id=request.path.split('/')[4])
            kwargs["queryset"] = Transaction.objects.filter(id=tx_input.output_transaction.id)
        return super(TxInputAdmin, self).formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )

admin.site.register(TxInput, TxInputAdmin)


class TxOutputAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'n', 'value')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'transaction':
            tx_output = TxOutput.objects.get(id=request.path.split('/')[4])
            kwargs["queryset"] = Transaction.objects.filter(id=tx_output.transaction.id)
        return super(TxOutputAdmin, self).formfield_for_foreignkey(
            db_field,
            request,
            **kwargs
        )

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "addresses":
            tx_output = TxOutput.objects.get(id=request.path.split('/')[4])
            kwargs["queryset"] = Address.objects.filter(tx_output=tx_output)
        return super(TxOutputAdmin, self).formfield_for_manytomany(
            db_field,
            request,
            **kwargs
        )

admin.site.register(TxOutput, TxOutputAdmin)


class AddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'balance')

admin.site.register(Address, AddressAdmin)


class WatchAddressAdmin(admin.ModelAdmin):
    list_display = ('address', 'amount', 'call_back', 'complete')

admin.site.register(WatchAddress, WatchAddressAdmin)
