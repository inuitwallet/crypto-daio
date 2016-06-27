from daio_wallet.bip32utils import BIP32Key
from daio_wallet.mnemonic import Mnemonic
from rest_framework import serializers
from .models import Wallet


class NewWalletSerializer(serializers.HyperlinkedModelSerializer):
    """
    Given a user id, generate half of a mnemonic pair for use as an HD seed
    """
    pk = serializers.IntegerField(read_only=True)
    mnemonic = serializers.CharField(max_length=255)
    id = serializers.IntegerField()
    extpub = serializers.CharField(max_length=255)

    def to_representation(self, data):
        """
        Build a representation of the Wallet for the new endpoint
        :param data:
        :return:
        """
        mnem = Mnemonic('english')
        local_words = mnem.generate(256)
        export_words = mnem.generate(128)
        key = BIP32Key.fromEntropy(mnem.to_seed(local_words, export_words))
        extpub = key.ExtendedKey(private=False, encoded=True)

        return {
            'mnemonic': export_words,
            'id': wallet.id,
            'extpub': extpub
        }

    def to_internal_value(self, data):
        wallet = Wallet.objects.create(mnemonic=local_words)
