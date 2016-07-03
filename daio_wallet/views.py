import hashlib
from decimal import Decimal
from blocks.models import WatchAddress, TxOutput, TxInput
from daio_wallet.bip32utils import BIP32Key
from daio_wallet.mnemonic import Mnemonic
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Wallet, ClientToken
from .forms import AddForm, SendForm, WatchForm, BalanceForm
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


def validate_mnemonic(key, check_hash):
    """
    given a key and hash, verify that the hashed key matches the hash
    """
    extpub_key_hash = hashlib.sha256(
        hashlib.sha256(
            key.ExtendedKey(
                private=False,
                encoded=True
            )
        ).digest()
    ).hexdigest()[:8]
    # check it against the supplied check_hash
    if extpub_key_hash != check_hash:
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
def watch(request):
    """
    Add an address to the watch list
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

    form = WatchForm(request.POST)

    if form.is_valid():
        # save the address to the watchlist
        watch_address = WatchAddress.objects.create(
            address=request.POST['address'],
            amount=request.POST['amount'],
            callback=request.POST['callback'],
        )
        if not watch_address:
            return JsonResponse(
                {
                    'success': False,
                    'message': 'Failed to create watch for {}'.format(
                        request.POST['address']
                    )
                }
            )
        return JsonResponse(
            {
                'success': True,
                'message': 'Watch created for {}'.format(
                    request.POST['address']
                )
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


@csrf_exempt
def balance(request):
    """
    Endpoint to check balance of an address
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

    form = BalanceForm(request.POST)

    if form.is_valid():
        value = Decimal(0.0)
        # get the outputs for the address
        outputs = TxOutput.objects.filter(addresses__address=request.POST['address'])
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
    # if the form has errors return them
    else:
        return JsonResponse(
            {
                'success': False,
                'error': form.errors
            }
        )


@csrf_exempt
def send(request):
    """
    Transact the given amount from the from address to the too adress
    note the fees and change address
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

    form = SendForm(request.POST)
    if form.is_valid():
        pass
        # validate the mnemonic
        # calculate the from address based on HD level
        # scan the blockchain for a tx that matches the necessary outputs to use as ins
        # build the tx
        # submit the tx to the blockchain
        # enter the tx into the database to retain data
        # once tx is accepted into block, mark as complete and hit callback url?



    # if the form has errors return them
    else:
        return JsonResponse(
            {
                'success': False,
                'error': form.errors
            }
        )
