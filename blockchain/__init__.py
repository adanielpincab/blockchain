import crypto
from time import time
from hashlib import sha256
from json import loads, dumps
import sqlite3
from math import ceil

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

    def preHash(self):
        '''
        Binary transaction information for inserting the
        transaction into a merkle tree.
        Generates same hash in the tree than self.hash()
        '''
        return str(
            [
                self.addrFrom,
                self.addrTo,
                self.amount,
                self.fee,
                self.timestamp
            ]
        ).encode()
    
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
    def __init__(self, _list=None):
        self.l = _list
        self.levels = []
    
    def add(self, item):
        '''
        Items ARE EXPECTED TO BE HASHED before adding the to the list
        '''
        if not self.l:
            self.l = [item]
        else:
            self.l.append(item)
        self.recalc()
    
    def recalc(self):
        self.levels = [tuple(self.l)] # reset, first level
        while len(self.levels[-1]) > 1:
            print(self.levels[-1])
            nextLevel = []
            pair = []
            for i in self.levels[-1]:
                pair.append(i)
                if len(pair) == 2:
                    nextLevel.append(
                        sha256((pair[0] + pair[1]).encode())
                        .hexdigest()
                    )
                    pair = []
            if len(pair) == 1:
                nextLevel.append(pair[0])
            self.levels.append(tuple(nextLevel))
    
    def root(self):
        return self.levels[-1][0]
    
    def proof(self, hash):
        res = [
            ('hash', hash)
        ]
        for l in range(len(self.levels[:-1])):
            level = self.levels[l]
            ind = level.index(hash)
            if (ind == len(level)-1) and (len(level)%2 != 0):
                continue # last hash with no pairs just goes up to the next level
            if ind%2 == 0:
                res.append(
                    ('right', level[ind+1])
                )
            else:
                res.append(
                    ('left', level[ind-1])
                )
            hash = self.levels[l+1][ceil(ind/2)-1]
        return res
            

class Block:
    def __init__(self, prevHash=None):
        self.transactions = []
        self.timestamp = int(time())
        self.nonce = 0
        self.miner = None
        self.prevHash = prevHash

    def addTransaction(self, transaction):
        if type(transaction) == Transaction:
            transaction = transaction.hash()
        
        self.transactions.append(transaction)
    
    def hash(self):
        return sha256(str(
            self.__dict__
        ).encode()).hexdigest()
    
class BlockChain:
    def __init__(self, db_name):
        self.db_con = sqlite3.connect(db_name)
        self.db_cur = self.db_con.cursor()
        with open("setup.sql", 'r') as f:
            self.db_cur.execute(f.read())
    
    def length(self):
        return len(self.blocks)

    def prevHash(self):
        return self.blocks[0].prevHash()
        