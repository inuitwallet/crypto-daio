from django import forms


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


