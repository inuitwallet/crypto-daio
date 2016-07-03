from daio_wallet.utils import AddressCheck
from django import forms
from django.core.exceptions import ValidationError


class AddForm(forms.Form):
    # the Wallet id from Daio
    id = forms.IntegerField(
        required=True,
    )
    # the mnemonic from the other service
    mnemonic = forms.CharField(
        required=True,
        max_length=255,
    )
    # the level of HD the address was generated at
    level = forms.IntegerField(
        required=True,
    )
    # the hash of the extpub_key for validation
    extpub_key_hash = forms.CharField(
        required=True,
        max_length=8,
    )


class WatchForm(forms.Form):
    address = forms.CharField(
        required=True,
        max_length=255,
    )
    amount = forms.DecimalField(
        required=True,
        max_digits=22,
        decimal_places=8,
    )
    callback = forms.URLField()

    def clean_address(self):
        address = self.cleaned_data['address']
        # check the address is valid
        if address[0] != 'B':
            raise ValidationError(
                '%(address)s is not a valid NBT address. It should start with a \'B\'',
                code='invalid address',
                params={'address': address},
            )
        address_check = AddressCheck()

        if not address_check.check_checksum(address):
            raise ValidationError(
                '%(address)s is not a valid NBT address. The checksum doesn\'t match',
                code='invalid address',
                params={'address': address},
            )


class BalanceForm(forms.Form):
    address = forms.CharField(
        required=True,
        max_length=255,
    )

    def clean_address(self):
        address = self.cleaned_data['address']
        # check the address is valid
        if address[0] != 'B':
            raise ValidationError(
                '%(address)s is not a valid NBT address. It should start with a \'B\'',
                code='invalid address',
                params={'address': address},
            )
        address_check = AddressCheck()

        if not address_check.check_checksum(address):
            raise ValidationError(
                '%(address)s is not a valid NBT address. The checksum doesn\'t match',
                code='invalid address',
                params={'address': address},
            )


class SendForm(forms.Form):
    # The wallet id
    id = forms.IntegerField(
        required=True,
    )
    # the matching mnemonic
    mnemonic = forms.CharField(
        required=True,
        max_length=255,
    )
    # the level of HD to use to generate the address
    level = forms.IntegerField(
        required=True,
    )
    # the hash of the extpub_key for validation
    extpub_key_hash = forms.CharField(
        required=True,
        max_length=8,
    )
    # the address to send the funds to
    to_address = forms.CharField(
        required=True,
        max_length=255,
    )
    # the amount to send
    amount = forms.DecimalField(
        required=True,
        max_digits=22,
        decimal_places=8,
    )
    # the amount of fees
    fees = forms.DecimalField(
        required=True,
        max_digits=22,
        decimal_places=8,
    )
    # optional callback
    callback = forms.URLField()

    def clean_to_address(self):
        address = self.cleaned_data['to_address']
        # check the address is valid
        if address[0] != 'B':
            raise ValidationError(
                '%(address)s is not a valid NBT address. It should start with a \'B\'',
                code='invalid address',
                params={'address': address},
            )
        address_check = AddressCheck()

        if not address_check.check_checksum(address):
            raise ValidationError(
                '%(address)s is not a valid NBT address. The checksum doesn\'t match',
                code='invalid address',
                params={'address': address},
            )
