import crypto
from time import time
from hashlib import sha256
from json import loads, dumps

class Transaction:
    def __init__(self, addrFrom: str, addrTo: str, amount: int, fee=0):
        self.addrFrom = addrFrom
        self.addrTo = addrTo
        self.amount = amount
        self.fee = fee
        self.timestamp = int(time())
        self.signature = (None, None) # pub_key, signature
    
    def hash(self):
        return sha256(str(
            [
                self.addrFrom,
                self.addrTo,
                self.amount,
                self.fee,
                self.timestamp
            ]
        ).encode()).hexdigest()
    
    def verify(self):
        return (
            crypto.verify(
                self.signature[1], 
                self.hash().encode(), 
                crypto.public_deserialized(
                    self.signature[0]
                )
            )
            and
            (Address.generate_blockchain_address(self.signature[0]) == self.addrFrom)
            )

    def to_json(self):
        return dumps(self.__dict__)

    @classmethod
    def from_json(self, json):
        new = Transaction(0, 0, 0, 0)
        new.__dict__ = loads(json)
        return new

class Address:
    def __init__(self, priv_pem=None):
        if not priv_pem:
            self.priv, self.pub = crypto.generate_key_pair()
        else:
            self.priv = crypto.private_from_pem(priv_pem)
            self.pub = self.priv.public_key
        
        self.address = self.generate_blockchain_address(self.pub)
    
    @classmethod
    def generate_blockchain_address(self, public_key):
        if type(public_key) == str:
            pem = public_key
        else:
            pem = crypto.public_serialized(public_key)
        
        return sha256(pem.encode()).hexdigest()
    
    def newTransaction(self, to: str, amount: int, fee=0):
        nt = Transaction(self.address, to, amount, fee)
        nt.signature = self.sign(nt.hash())
        return nt
    
    def sign(self, str_data):
        return (
            crypto.public_serialized(self.pub), 
            crypto.sign(str_data.encode(), self.priv)
        )
    
class Merkle:
    def __init__(self):
        self.l = []
    
    def add(self, item):
        self.l.append(item)
        self.l.sort()
    
    def hash(self):
        if len(self.l) % 2 != 0:
            self.l.append(self.l[-1])
        