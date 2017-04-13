import codecs
import hashlib
import json

from threading import Thread
import time
import requests
from channels import Channel
from django.core.management import BaseCommand

from blocks.models import Block, Transaction, TxInput, TxOutput, Address, WatchAddress
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils import timezone

from blocks.utils.numbers import get_var_int
from blocks.utils.rpc import send_rpc, get_block_hash
import logging

logger = logging.getLogger('block_parser')

tz = timezone.get_current_timezone()


class Command(BaseCommand):

    def save_transaction(self, block, tx):
        """
        Parse and save a transaction Object
        """
        # get the transaction details
        transaction, _ = Transaction.objects.get_or_create(
            block=block,
            tx_id=tx.get('txid', None),
        )

    def check_watch_addresses(self, address, value):
        """
        Check the list of watched addresses and reduce the expected amount by the value.
        Notify a callback url if one is preset and the value <= 0
        """
        # we work with unique addresses so get() should be safe here
        try:
            watched_address = WatchAddress.objects.get(address=address)
        except (MultipleObjectsReturned, ObjectDoesNotExist):
            return
        # we have a watched address. lets reduce the value
        watched_address.amount -= float(value)
        watched_address.save()
        if watched_address.amount <= 0.0:
            response = requests.post(
                url=watched_address.call_back,
                headers={'Content-Type': 'application/json'},
                data=json.loads(
                    {
                        'address': address,
                    }
                )
            )
            if response.status_code != requests.codes.ok:
                logger.warning(
                    'got an error posting to address callback: {} - {}'.format(
                        watched_address,
                        response.status_code
                    )
                )
        return

    def check_transaction(self):
        pass

    def trigger_transaction_parse(self, block, tx_hash, blocking=False):
        """
        For the given block object and transaction hash,
        request the tx json from the coin daemon and
        trigger the save method.
        specify blocking=True to call the save method directly
        otherwise it is called in a new thread
        """
        rpc = send_rpc(
            {
                'method': 'getrawtransaction',
                'params': [tx_hash, 1]
            }
        )
        tx = rpc['result'] if not rpc['error'] else None
        if tx:
            if blocking:
                self.save_transaction(block, tx)
            else:
                save = Thread(
                    target=self.save_transaction,
                    kwargs={
                        'block': block,
                        'tx': tx,
                    },
                    name=tx_hash
                )
                save.daemon = True
                save.start()

    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            '--start-height',
            help='The block height to start the parse from',
            dest='start_height',
            default=0
        )

    @staticmethod
    def byte_from_file(filename):
        with open(filename, "rb") as byte_file:
            while True:
                byte = byte_file.read(1)
                if byte:
                    yield byte
                else:
                    break

    @staticmethod
    def get_tx_output(vout_n, raw_block, counter):
        value = int.from_bytes(raw_block[counter:counter + 8], 'little')
        out_script_len, output_offset = get_var_int(raw_block[counter + 8:counter + 17])
        counter += output_offset
        out_script = codecs.encode(raw_block[counter:counter + out_script_len], 'hex')
        counter += out_script_len
        return {
            "n": vout_n,
            "value": value,
            "hash160": '',
            "scriptPubKey": {
                "hex": out_script,
            },
        }, counter

    @staticmethod
    def get_tx_input(raw_block, counter):
        txid = codecs.encode(raw_block[counter:counter + 32], 'hex')
        index = raw_block[counter + 32:counter + 36]

        # if input_index == "FF FF FF FF" then the index = -1
        if index == codecs.decode("ffffffff", 'hex'):
            vout = -1
        else:
            vout = int.from_bytes(index, 'big')

        input_script_len, script_len_offset = get_var_int(
            raw_block[counter + 36:counter + 45]
        )
        counter += script_len_offset

        input_script = codecs.encode(
            raw_block[counter:counter + input_script_len], 'hex'
        )
        counter += input_script_len
        sequence = codecs.encode(raw_block[counter:counter + 4], 'hex')
        counter += 4

        return {
            "txid": txid,
            "vout": vout,
            "scriptSig": {
                "hex": input_script.decode('utf-8'),
            },
            "sequence": sequence.decode('utf-8'),
        }, counter

    def get_tx_dict(self, block, raw_block, counter, tx_n, num_tx):
        tx_dict = {}
        tx_start = counter
        tx_dict['version'] = int.from_bytes(raw_block[counter:counter + 4], 'little')
        tx_dict["timestamp"] = int.from_bytes(
            raw_block[counter + 4: counter + 8], 'little'
        )
        counter += 8
        # -INPUT PARSING-
        tx_in_count, in_offset = get_var_int(raw_block[counter:counter + 9])
        counter += in_offset
        tx_dict["vin"] = []

        for i in range(0, tx_in_count):
            input_details, counter = self.get_tx_input(raw_block, counter)
            tx_dict["vin"].append(input_details)

        # -OUTPUT PARSING-
        # let's get output count
        tx_out_count, out_offset = get_var_int(raw_block[counter:counter+9])
        counter += out_offset
        tx_dict["vout"] = []
        # print "outCount", outCount
        # let's cycle through the outputs
        for o in range(0, tx_out_count):
            output_details, counter = self.get_tx_output(o, raw_block, counter)
            tx_dict["vout"].append(output_details)

        tx_dict['locktime'] = int.from_bytes(raw_block[counter:counter + 4], 'little')
        tx_dict["tx_id"] = codecs.encode(
            hashlib.sha256(
                hashlib.sha256(
                    raw_block[tx_start:counter + 5]
                ).digest()
            ).digest()[::-1],
            'hex'
        )

        # hash transaction
        # last tx in block is succeeded by a block-end-script
        if tx_n == num_tx - 1:
            end_script_len = int.from_bytes(raw_block[counter+5:counter+6], 'little') * 2
            tx_dict["end_script"] = raw_block[counter+6:counter+6+end_script_len]
            counter += 12 + end_script_len

        transaction, _ = Transaction.objects.get_or_create(
            block=block,
            tx_id=tx_dict['tx_id']
        )
        transaction.parse_rpc_tx(tx_dict)

        return counter

    def get_block_dict(self, raw_block, height):
        """
        :param block:
        :return:
        """
        # check the block size (0 size can be discarded)
        block_size = raw_block[4:8]
        if not block_size:
            return
        block_size = int.from_bytes(block_size, 'little')
        # split out the header to allow for hash calculation and parsing of header details
        block_header = raw_block[8:88]
        # calculate the block hash
        block_hash = codecs.encode(
            hashlib.sha256(hashlib.sha256(block_header).digest()).digest()[::-1],
            'hex'
        )
        # the number of transaction is held as a VarInt. see what that equals here
        num_tx, offset = get_var_int(raw_block[88:97])
        # we keep a pointer to the current byte to facilitate reading
        counter = 88 + offset

        block_dict = {
            'hash': block_hash,
            'height': height,
            'size': block_size,
            'version': int.from_bytes(block_header[:4], 'little'),
            'previousblockhash': codecs.encode(block_header[4:36][::-1], 'hex'),
            'merkleroot': codecs.encode(block_header[36:68][::-1], 'hex'),
            'time': time.strftime(
                '%Y-%m-%d %H:%M:%S %Z',
                time.gmtime(int.from_bytes(block_header[68:72], 'little'))
            ),
            'bits': codecs.encode(block_header[72:76][::-1], 'hex'),
            'nonce': int.from_bytes(block_header[76:80], 'little'),
        }

        block, _ = Block.objects.get_or_create(hash=block_hash)
        block.parse_rpc_block(block_dict)

        #transactions = []
        #for tx_n in range(0, num_tx):
        #    counter = transactions.append(
        #        self.get_tx_dict(block, raw_block, counter, tx_n, num_tx)
        #    )

    def handle(self, *args, **options):
        """
        Parse the block chain
        """
        start_hash = get_block_hash(options['start_height'])
        if not start_hash:
            logger.error('could not get start hash. check rpc connection')
        logger.info(
            'starting block chain parse at height {} with block {}'.format(
                options['start_height'],
                start_hash
            )
        )
        # send the hash to the channel for parsing a block
        Channel('parse_block').send({'block_hash': start_hash})




