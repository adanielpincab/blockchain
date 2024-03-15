import unittest
import crypto
import os

class SignAndVerify(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.priv, self.pub = crypto.generate_key_pair()
    
    def test_serialization(self):
        crypto.private_to_pem_file(self.priv, "mock.pem", "mock1234")
        crypto.private_from_pem("mock.pem", "mock1234")

        crypto.public_deserialized(
            crypto.public_serialized(self.pub)
            )

        with self.assertRaises(ValueError):
            wrong_priv = crypto.private_from_pem("mock.pem", "wrongpass")
        
        os.remove("mock.pem")
    
    def test_sign_verify(self):
        signature = crypto.sign("mensaje de prueba".encode(), self.priv)
        self.assertTrue(
            crypto.verify(signature, "mensaje de prueba".encode(), self.pub)
        )
        
        bad_signature = signature[:3] + '0' + signature[4:]
        self.assertFalse(
            crypto.verify(bad_signature, "mensaje de prueba".encode(), self.pub)
        )