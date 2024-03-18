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
            'dd7ebdf165fe269f1afc094286c4b438f5f96150db60d9c79d305059822819cc'
        )
        m.add('445c06f8335048bf3af883b047f79163c70083de3874e79ba1f7e621e0073579')
        m.add('90984cc7ba5a96b3dcc55921ac4c7d7b344fcc37947a003cae10c475f4439377')
        m.add('f7c3cc7a2377dabee2d71a54e5b1ca93dae1006887d0747c0978e051a948fc15')
        self.assertEqual(
            m.root(), 
            'ca04ce6d7c2dfdba78c403305c8e7f61ed7050513db01408c706ca21de2eb850'
        )
        
        print(m.proof('445c06f8335048bf3af883b047f79163c70083de3874e79ba1f7e621e0073579'))
        self.assertEqual(
            m.proof('445c06f8335048bf3af883b047f79163c70083de3874e79ba1f7e621e0073579'),
            {
                    'root':'ca04ce6d7c2dfdba78c403305c8e7f61ed7050513db01408c706ca21de2eb850', 
                    'path': [
                        ('left', '3891f13300b85e89d403504b4c26abe3adf5f39420a2d111059423cb25b33b86'), 
                        ('right', '95dfe5def74e4c82811b7adbebcc111b3ae82d17cd905c920bae50867448225e'), 
                        ('right', 'f7c3cc7a2377dabee2d71a54e5b1ca93dae1006887d0747c0978e051a948fc15')
                    ]
            }
        )

        # same result, even with different order of input
        m2 = Merkle()
        m2.add('445c06f8335048bf3af883b047f79163c70083de3874e79ba1f7e621e0073579')
        m2.add('b221d9dbb083a7f33428d7c2a3c3198ae925614d70210e28716ccaa7cd4ddb79')
        m2.add('90984cc7ba5a96b3dcc55921ac4c7d7b344fcc37947a003cae10c475f4439377')
        m2.add('3891f13300b85e89d403504b4c26abe3adf5f39420a2d111059423cb25b33b86')
        m2.add('f7c3cc7a2377dabee2d71a54e5b1ca93dae1006887d0747c0978e051a948fc15')
        self.assertEqual(
            m2.proof('445c06f8335048bf3af883b047f79163c70083de3874e79ba1f7e621e0073579'),
            {
                    'root':'ca04ce6d7c2dfdba78c403305c8e7f61ed7050513db01408c706ca21de2eb850', 
                    'path': [
                        ('left', '3891f13300b85e89d403504b4c26abe3adf5f39420a2d111059423cb25b33b86'), 
                        ('right', '95dfe5def74e4c82811b7adbebcc111b3ae82d17cd905c920bae50867448225e'), 
                        ('right', 'f7c3cc7a2377dabee2d71a54e5b1ca93dae1006887d0747c0978e051a948fc15')
                    ]
            }
        )