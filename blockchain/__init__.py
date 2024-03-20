import crypto
from time import time
from hashlib import sha256
from json import loads, dumps
from math import floor, inf
import sqlite3

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
    def __init__(self, _list=None):
        self.l = _list
        self.levels = []

        if _list:
            self.recalc()
    
    def add(self, item: str):
        '''
        Items ARE EXPECTED TO BE HASHED before being added to the list
        '''
        if not self.l:
            self.l = [item]
        else:
            self.l.append(item)
        self.recalc()
    
    def recalc(self):
        self.l.sort()
        self.levels = [tuple(self.l)] # reset, first level
        while len(self.levels[-1]) > 1:
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
        res = {
            'root': self.root(),
            'path':[]
        }
        for l in range(len(self.levels[:-1])):
            level = self.levels[l]
            ind = level.index(hash)
            if (ind == len(level)-1) and (len(level)%2 != 0):
                continue # last hash with no pairs just goes up to the next level
            if ind%2 == 0:
                res['path'].append(
                    ('right', level[ind+1])
                )
            else:
                res['path'].append(
                    ('left', level[ind-1])
                )
            hash = self.levels[l+1][int(ind/2)]
        return res
    
    def __iter__(self):
        return self.l.__iter__()

class Block:
    def __init__(self, prevHash=None):
        self.transactions = Merkle()
        self.transactionsRoot = None
        self.timestamp = int(time())
        self.nonce = 0
        self.miner = None
        self.prevHash = prevHash

    def addTransaction(self, transaction):
        if type(transaction) == Transaction:
            transaction = transaction.hash()
        self.transactions.add(transaction)
        self.transactionsRoot = self.transactions.root()
    
    def hash(self):
        return sha256(str([
            self.transactionsRoot,
            self.timestamp,
            self.nonce,
            self.miner,
            self.prevHash
        ]).encode()).hexdigest()
    
    def to_json(self):
        return dumps({
            'transactionsRoot': self.transactionsRoot,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'miner': self.miner,
            'prevHash': self.prevHash
        })
    
    @classmethod
    def from_json(self, json):
        data = loads(json)
        b = Block()
        b.transactionsRoot = data['transactionsRoot']
        b.timestamp = data['timestamp']
        b.nonce = data['nonce']
        b.miner = data['miner']
        b.prevHash = data['prevHash']

        return b

'''
DIFFICULTY OF THE BLOCKCHAIN.
Automatically adapted depending on the last block's timestamp.
The more time has passed, the easier the difficulty gets.
'''
def difficulty(timeLast, timeNew):
    if (timeNew - timeLast) <= 30:
        return inf
    return floor(500/ ((timeNew-timeLast) - 30) )

class BlockChain:
    def __init__(self, dbfilename):
        self.con = sqlite3.connect(dbfilename)
        self.cur = self.con.cursor()
        with open('setup.sql', 'r') as setup:
            self.cur.execute(setup.read())
            setup.close()
        self.verify()
    
    def length(self):
        # TODO return last block id
        pass
    
    def verify(self):
        # TODO verify blockchain on load
        pass

    def valid(self, newBlock: Block):
        # TODO verify if a block is valid
        pass

    def prevHash(self):
        return self.blocks[0].prevHash()
        