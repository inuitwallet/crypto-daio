import hashlib
from decimal import Decimal
from blocks.models import WatchAddress, TxOutput, TxInput
from daio_wallet.bip32utils import BIP32Key
from daio_wallet.mnemonic import Mnemonic
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Wallet, ClientToken
from .forms import AddForm
from .utils import AddressCheck

mnemonic = Mnemonic('english')
BIP32_HARDEN = 0x80000000  # choose from hardened set of child keys


def verify(request):
    """
    check the auth header for verification
    :param request:
    :return:
    """
    try:
        ClientToken.objects.get(token=request.META.get('HTTP_AUTHENTICATION'))
    except ObjectDoesNotExist:
        return False
    return True


def new(request):
    """
    Generate a new mnemonic pair and extended pub key.
    :param request:
    :return: json containing id, export_mnemonic and ext_pub key
    """
    # verify the auth header
    if not verify(request):
        return JsonResponse(
            {
                'success': False,
                'error': 'invalid token'
            }
        )
    local_mnemonic = mnemonic.generate(256)
    export_mnemonic = mnemonic.generate(128)
    key = BIP32Key.fromEntropy(
        mnemonic.to_seed(
            local_mnemonic,
            export_mnemonic
        )
    )
    extpub_key = key.ExtendedKey(
        private=False,
        encoded=True
    )
    wallet = Wallet.objects.create(
        mnemonic=local_mnemonic
    )
    return JsonResponse(
        {
            'success': True,
            'mnemonic': export_mnemonic,
            'id': wallet.id,
            'extpub': extpub_key
        }
    )


@csrf_exempt
def add(request):
    """
    Given an id, mnemonic and level, create an extended private key and
    generate a walletimport format private key
    :param request:
    :return:
    """
    # verify the auth header
    if not verify(request):
        return JsonResponse(
            {
                'success': False,
                'error': 'invalid token'
            }
        )
    # Error if not POST
    if request.method != 'POST':
        return JsonResponse(
            {
                'success': False,
                'error': 'must be a POST request'
            }
        )
    # bind the form for validation
    form = AddForm(request.POST)
    if form.is_valid():
        # get the wallet with the given id
        wallet = Wallet.objects.get(
            id=request.POST['id']
        )

        # using the supplied and saved mnemonics,
        # generate the extended public key check hash
        key = BIP32Key.fromEntropy(
            mnemonic.to_seed(
                wallet.mnemonic,
                request.POST['mnemonic']
            )
        )
        extpub_key_hash = hashlib.sha256(
            hashlib.sha256(
                key.ExtendedKey(
                    private=False,
                    encoded=True
                )
            ).digest()
        ).hexdigest()[:8]
        # check it against the supplied check_hash
        if extpub_key_hash != request.POST['extpub_key_hash']:
            return JsonResponse(
                {
                    'success': False,
                    'error': 'mnemonic or id is incorrect. check hash doesn\'t match'
                }
            )

        # Using the generated HD key, create the WIF private key
        new_key = key.ChildKey(int(request.POST['level']) + BIP32_HARDEN)
        wif = new_key.WalletImportFormat()
        return JsonResponse(
            {
                'success': True,
                'wif': wif
            }
        )

    # if the form has errors return them
    else:
        return JsonResponse(
            {
                'success': False,
                'error': form.errors
            }
        )


def watch(request):
    """
    Add an address to the watch list
    :param request:
    :return:
    """
    # verify the auth header
    if not verify(request):
        return JsonResponse(
            {
                'success': False,
                'error': 'invalid token'
            }
        )

    # Error if not POST
    if request.method != 'POST':
        return JsonResponse(
            {
                'success': False,
                'error': 'must be a POST request'
            }
        )

    address = request.POST['address']

    # check the address is valid
    if address[0] != 'B':
        return JsonResponse(
            {
                'success': False,
                'message': '{} is not a valid NBT address. It '
                           'should start with a \'B\''.format(address)
            }
        )
    address_check = AddressCheck()

    if not address_check.check_checksum(address):
        return JsonResponse(
            {
                'success': False,
                'message': '{} is not a valid NBT address. The '
                           'checksum doesn\'t match'.format(address)
            }
        )

    # save the address to the watchlist
    watch_address = WatchAddress.objects.create(
        address=address,
        amount=request.POST['amount'],
        callback=request.POST['callback'],
    )
    if not watch_address:
        return JsonResponse(
            {
                'success': False,
                'message': 'Failed to create watch for {}'.format(address)
            }
        )
    return JsonResponse(
        {
            'success': True,
            'message': 'Watch created for {}'.format(address)
        }
    )


def balance(request):
    """
    Endpoint to check balance of an address
    :param request:
    :return:
    """
    # verify the auth header
    if not verify(request):
        return JsonResponse(
            {
                'success': False,
                'error': 'invalid token'
            }
        )
    # Error if not POST
    if request.method != 'POST':
        return JsonResponse(
            {
                'success': False,
                'error': 'must be a POST request'
            }
        )

    value = Decimal(0.0)
    # get the outputs for the address
    outputs = TxOutput.objects.filter(addresses_address=request.POST['address'])
    for output in outputs:
        # for each output, gather the inputs
        inputs = TxInput.objects.filter(tx_id=output.transaction.tx_id)
        if inputs:
            # if inputs exist using the output transaction, the value has been spent
            continue
        # if unspent. add it to the value
        value += Decimal(output.value)

    return JsonResponse(
        {
            'success': True,
            'value': value
        }
    )
