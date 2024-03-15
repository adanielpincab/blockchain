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
    
    def test_block(self):
        b = Block()
        b.addTransaction(self.t)
        b.addTransaction(self.t.hash())
    
    def test_merkle(self):
        m = Merkle()
        m.add('b221d9dbb083a7f33428d7c2a3c3198ae925614d70210e28716ccaa7cd4ddb79')
        self.assertEqual(
            m.root(), 
            'b221d9dbb083a7f33428d7c2a3c3198ae925614d70210e28716ccaa7cd4ddb79'
        )
        m.add('3891f13300b85e89d403504b4c26abe3adf5f39420a2d111059423cb25b33b86')
        self.assertEqual(
            m.root(), 
            '26086b9533dc45f23dfd7f4fe6cadf4a82ec83b310a49b828141a063eea0ea8e'
        )
        m.add('445c06f8335048bf3af883b047f79163c70083de3874e79ba1f7e621e0073579')
        m.add('90984cc7ba5a96b3dcc55921ac4c7d7b344fcc37947a003cae10c475f4439377')
        m.add('f7c3cc7a2377dabee2d71a54e5b1ca93dae1006887d0747c0978e051a948fc15')
        self.assertEqual(
            m.root(), 
            '5c9c2ba5982276088d42e30ff2c7f9f5093336a5684dc8ce18788cc8e7a7805c'
        )
        
        print(m.proof('445c06f8335048bf3af883b047f79163c70083de3874e79ba1f7e621e0073579'))