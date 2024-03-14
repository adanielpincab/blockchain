import unittest
from blockchain import *

class TestAddressesTransactions(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.a = Address()
        self.t = self.a.newTransaction('b', 10, 0)
        self.tjson = self.t.to_json()
    
    def test_blockchain_address(self):
        self.assertEqual(len(self.a.address), 64)

        self.assertEqual(
            Address.generate_blockchain_address(
                self.a.pub
            ),
            Address.generate_blockchain_address(
                self.a.sign('mock')[0]
            )
        )
    
    def test_transaction_json(self):
        self.assertEqual(
            Transaction.from_json(self.tjson).hash(),
            self.t.hash()
        )
    
    def test_verify(self):
        self.assertTrue(self.t.verify())
        self.t.addrTo = 'tampered'
        self.assertFalse(self.t.verify())