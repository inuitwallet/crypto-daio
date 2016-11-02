import hashlib
from decimal import Decimal
from blocks import pynubitools
from blocks.models import WatchAddress, TxOutput, TxInput
from daio_wallet.bip32utils import BIP32Key
from daio_wallet.mnemonic import Mnemonic
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Wallet, ClientToken
from .forms import SendForm, WatchForm, BalanceForm
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


def get_balance(address):
    """
    Scan outputs for the given address and return the unspent balance
    :param address:
    :return:
    """
    value = Decimal(0.0)
    # get the outputs for the address
    outputs = TxOutput.objects.filter(addresses__address=address)
    for output in outputs:
        if output.is_unspent():
            # if unspent. add it to the value
            value += Decimal(output.value)
    return value


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
        value = get_balance(request.POST['address'])
        return JsonResponse(
            {
                'success': True,
                'balance': value
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
        # Get the wallet
        wallet = Wallet.objects.get(pk=request.POST['wallet_id'])
        # generate the base key with the supplied and saved details
        key = BIP32Key.fromEntropy(
            mnemonic.to_seed(
                wallet.mnemonic,
                request.POST['mnemonic']
            )
        )
        # validate that the key is correct by checking against the hash
        if not validate_mnemonic(key, request.POST['extpub_key_hash']):
            return JsonResponse(
                {
                    'success': False,
                    'error': 'checksum failed. check id'
                }
            )
        # generate the child key at the requested level
        child_key = key.ChildKey(int(request.POST['level']) + BIP32_HARDEN)
        # generate the address from the child key
        address = child_key.Address()
        # generate the change address from the next key in sequence
        change_key = key.ChildKey(int(request.POST['level']) + 1 + BIP32_HARDEN)
        change_address = change_key.Address()
        # check the balance of the address to make sure it can send the requested funds
        balance = get_balance(address)
        # The total Tx amount is (amount + fee)
        tx_amount = (Decimal(request.POST['amount']) + Decimal(request.POST['fee']))

        #if balance < tx_amount:
        #    return JsonResponse(
        #        {
        #            'success': False,
        #            'error': 'insufficient balance'
        #        }
        #    )

        balance = 12345
        # get the unspent outputs
        outputs = TxOutput.objects.filter(addresses__address=address)
        output_value = Decimal(0.0)
        inputs = []
        for output in outputs:
            # ignore spent outputs
            if not output.is_unspent():
                continue
            # calculate the cumulative output value
            output_value += Decimal(output.value)
            # add the output to the list of potential inputs
            inputs.append(output)
            # see if we have enough funds to complete the Tx
            if output_value >= tx_amount:
                break

        # build the tx_inputs
        tx_inputs = []
        for inp in inputs:
            tx_inputs.append(
                {
                    'outpoint': {
                        'hash': inp.transaction.tx_id,
                        'index': inp.n
                    },
                    'script': pynubitools.mk_pubkey_script(address),
                    'sequence': 4294967295,  # not using lock_time
                }
            )
        # build the tx_outputs
        # first is the tx amount
        # second is the change address (address_balance - amount - fee)
        tx_outputs = [
            {
                'script': pynubitools.mk_pubkey_script(request.POST['to_address']),
                'value': int(request.POST['amount'])
            },
            {
                'script': pynubitools.mk_pubkey_script(change_address),
                'value': int(balance) - int(tx_amount)
            }
        ]
        if not tx_outputs:
            return JsonResponse(
                {
                    'success': False,
                    'error': 'No available outputs for {}'.format(address)
                }
            )
        tx = pynubitools.mktx(
                tx_inputs,
                tx_outputs
            ),
        #tx = pynubitools.sign(
        #
        #    0,
        #    child_key.PrivateKey()
        #)
        return JsonResponse(
            {
                'success': True,
                'tx': tx
            }
        )
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
