import unittest
from blockchain import *
from time import sleep
import os
import shutil

class TestAddress(unittest.TestCase):
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
    
class TestTransaction(unittest.TestCase):
    @classmethod
    def setUpClass(self) -> None:
        self.a = Address()
        self.t = self.a.newTransaction('b', 10, 0)
        self.tjson = self.t.to_json()

    def test_transaction_json(self):
        self.assertEqual(
            Transaction.from_json(self.tjson).hash(),
            self.t.hash()
        )
        
    def test_transaction_verify(self):
        self.assertTrue(self.t.verify())
        self.t.addrTo = 'tampered'
        self.assertFalse(self.t.verify())

class TestMerkle(unittest.TestCase):
    def test_root(self):
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
    
    def test_proofs(self):
        m = Merkle()

        # arbitrary order
        m.add('b221d9dbb083a7f33428d7c2a3c3198ae925614d70210e28716ccaa7cd4ddb79')
        m.add('3891f13300b85e89d403504b4c26abe3adf5f39420a2d111059423cb25b33b86')
        m.add('445c06f8335048bf3af883b047f79163c70083de3874e79ba1f7e621e0073579')
        m.add('90984cc7ba5a96b3dcc55921ac4c7d7b344fcc37947a003cae10c475f4439377')
        m.add('f7c3cc7a2377dabee2d71a54e5b1ca93dae1006887d0747c0978e051a948fc15')
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

        # different arbitrary order, expected same result
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

class TestBlock(unittest.TestCase):
    def add_transaction(self):
        a = Address()
        t = a.newTransaction('a', 10, 0)
        b = Block()
        
        b.addTransaction(t)
        b.addTransaction(t.hash())

    def text_from_json(self):
        b = Block.from_json("""
                            {
                                'transactionsRoot': None,
                                'timestamp': 1710764231,
                                'nonce': 907567,
                                'miner': None,
                                'prevHash': None
                            }
                            """)
        self.assertEqual(b.hash(), '00000ce24ef39a5bee5e075a88b4b9beae79299e5d8fdf453cbf2c69fd7735c7')

    def text_from_tuple(self):
        b = Block.from_tuple((None, 1710764231, 907547, None, None))
        self.assertEqual(b.hash(), '00000ce24ef39a5bee5e075a88b4b9beae79299e5d8fdf453cbf2c69fd7735c7')

class TesstBlockChain(unittest.TestCase):
    @classmethod
    def setUpClass(self) -> None:
        self.DB_NAME = './tests/test-TESTING_COPY.db'
        shutil.copy('./tests/test.db', self.DB_NAME)
        self.b = BlockChain(self.DB_NAME)
    
    @classmethod
    def tearDownClass(self) -> None:
        self.b.closeConnection()
        os.remove(self.DB_NAME)
    
    def test_block_height(self):
        self.assertEqual(self.b.length(), 1)
    
    def test_insert_invalid_block(self):
        with self.assertRaises(InvalidBlock):
            instant_block = Block(self.b.lastBlock().hash())
            instant_block.timestamp = self.b.lastBlock().timestamp + 31
            self.b.insertNewBlock(instant_block)

        with self.assertRaises(InvalidBlock):
            self.b.insertNewBlock(Block('fakehash'))

    def test_insert_valid_block(self):
        newBlock = Block(self.b.lastBlock().hash())
        newBlock.timestamp = 1711121932
        newBlock.nonce = 39555497
        self.b.insertNewBlock(newBlock)
    
    def test_verify(self):
        b_prime = BlockChain(self.DB_NAME)
        # should verify without any problem
        b_prime.closeConnection()
    
    def test_verify_tampered_db(self):
        tampered_db_name_1 = self.DB_NAME + 'TAMP_1'
        tampered_db_name_2 = self.DB_NAME + 'TAMP_2'
        
        shutil.copy(self.DB_NAME, tampered_db_name_1)
        shutil.copy(self.DB_NAME, tampered_db_name_2)
        
        con = sqlite3.connect(tampered_db_name_1)
        cur = con.cursor()
        cur.execute('UPDATE Block SET nonce=42 WHERE ROWID=1')
        con.commit()
        con.close()

        con = sqlite3.connect(tampered_db_name_2)
        cur = con.cursor()
        cur.execute('UPDATE Block SET hash = "0000000000" WHERE ROWID=1')
        con.commit()
        con.close()

        for tampered in [tampered_db_name_1, tampered_db_name_2]:
            with self.assertRaises(InvalidBlockchain):
                BlockChain(tampered)
            os.remove(tampered)
