import hashlib
import string
from random import choice

import pytest
from tenant_schemas.test.cases import TenantTestCase

from blocks.models import Transaction, TxOutput, Address, TxInput


class TestTxOutputs(TenantTestCase):
    def test_is_spent(self):
        block = pytest.helpers.generate_block("test_is_spent")
        tx0 = Transaction.objects.create(
            tx_id=hashlib.sha256(b"Tx0").hexdigest(), block=block, index=0
        )
        tx1 = Transaction.objects.create(
            tx_id=hashlib.sha256(b"Tx1").hexdigest(), block=block, index=1
        )
        # create an output for tx 1 at index 1 with an address output
        address = Address.objects.create(
            address="".join(choice(string.hexdigits) for _ in range(28))
        )
        output = TxOutput.objects.create(transaction=tx1, index=1, address=address)
        # output has no associated input so should report as unspent
        self.assertFalse(output.is_spent)
        # create an input spending the output
        TxInput.objects.create(transaction=tx0, index=1, previous_output=output)
        # output should now report as spent
        self.assertTrue(output.is_spent)
