import crypto
from time import time
from hashlib import sha256
from json import loads, dumps
from math import floor, inf
import sqlite3

from blockchain.SQL_setup import SETUP

# TRANSACTION AMOUNT IN MICRO (1 coin = 1 000 000)
class Transaction:
    def __init__(
            self, 
            inputs: list[str],  
            outputs: list[dict]
        ):
        self.inputs = inputs # [tx_id, ... tx_id_N]
        self.outputs = outputs # [ {"amount":amount, "address":address}, ... ]
        self.timestamp = int(time())
        self.signature = [None, None] # [pub_key, signature]
    
    def hash(self):
        return sha256(str(
            [
                self.inputs,
                self.outputs,
                self.timestamp
            ]
        ).encode()).hexdigest()

    def verify(self):
        return crypto.verify(
            self.signature[1], 
            self.hash().encode(), 
            crypto.public_deserialized(
                self.signature[0]
            )
        )

    def to_json(self):
        return dumps(self.__dict__)

    @classmethod
    def from_json(self, json):
        new = Transaction([], [])
        new.__dict__ = loads(json)
        return new
    
    def to_tuple(self):
        return (self.timestamp, self.signature[0], self.signature[1], self.hash())
    
    def inputs_to_tuples(self):
        res = []
        h = self.hash()
        for i in self.inputs:
            res.append( (h, i) )
        return res
    
    def outputs_to_tuples(self):
        res = []
        h = self.hash()
        for o in self.outputs:
            res.append( (h, o["address"], o["amount"]) )
    
    @classmethod
    def from_tuple(self, tup):
        t = Transaction()
        t.timestamp = tup[0]
        t.signature = [tup[1], tup[2]]

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
                # last hash with no pairs just goes up to the next level
                continue
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
            self.prevHash
        ]).encode()).hexdigest()
    
    def to_dict(self):
        return {
            'transactionsRoot': self.transactionsRoot,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'prevHash': self.prevHash
        }
    
    @staticmethod
    def from_dict(dct):
        b = Block()
        b.transactionsRoot = dct['transactionsRoot']
        b.timestamp = dct['timestamp']
        b.nonce = dct['nonce']
        b.prevHash = dct['prevHash']
        return b

    def to_json(self):
        return dumps(self.to_dict())
    
    def to_tuple(self):
        return (
            self.transactionsRoot,
            self.timestamp,
            self.nonce,
            self.prevHash,
            self.hash()
        )

    @classmethod
    def from_json(self, json):
        data = loads(json)
        b = Block()
        b.transactionsRoot = data['transactionsRoot']
        b.timestamp = data['timestamp']
        b.nonce = data['nonce']
        b.prevHash = data['prevHash']

        return b
    
    @classmethod
    def from_tuple(self, db_tuple):
        b = Block()
        b.transactionsRoot = db_tuple[0]
        b.timestamp = db_tuple[1]
        b.nonce = db_tuple[2]
        b.prevHash = db_tuple[3]
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

'''
DIFFICULTY OF THE BLOCKCHAIN.
50 coins, halved every year.
'''
def reward(height):
    return int(50000000/(2**(int(height/525960))))

class InvalidBlockchain(Exception):
    def __init__(self):
        super().__init__(
            'Incorrect Blockchain. Blockchain data may have been tampered making the chain invalid.'
        )

class InvalidBlock(Exception):
    def __init__(self, block: Block):
        super().__init__(
            'The block ' + block.hash() + ' is not valid for this blockchain.'
        )

class BlockChain:
    def __init__(self, dbfilename, genesisBlock: Block = None, onlyHeaders=False):
        self.dbfilename = dbfilename
        self.SQLsafeNested = False # prevents inner callings from closing the db for the main function
        self.openConnection()
        self.cur.executescript(SETUP)
        self.closeConnection()
        if not self.verify(genesisBlock):
            raise InvalidBlockchain
    
    def openConnection(self):
        self.con = sqlite3.connect(self.dbfilename)
        self.cur = self.con.cursor()
    
    def closeConnection(self):
        self.con.close()

    def SQLsafe(func):
        def wrapper(self, *args):
            self.openConnection()
            with self.con:
                res = func(self, *args)
            self.closeConnection()
            return res
        return wrapper
    
    @SQLsafe
    def length(self):
        self.cur.execute('''SELECT MAX(ROWID) FROM Block''')
        return self.cur.fetchone()[0]
    
    @SQLsafe    
    def verify(self, genesisBlock: Block= None):
        self.cur.execute('''SELECT * FROM Block ORDER BY ROWID''')
        blocks = self.cur.fetchall()

        if len(blocks) == 0:
            b = genesisBlock if genesisBlock else Block()
            self.cur.execute(
                'INSERT INTO Block VALUES (?, ?, ?, ?, ?)',
                b.to_tuple()
            )
            self.con.commit()
        else:
            for i in range(len(blocks)):
                if i == 0:
                    continue
                current = Block.from_tuple(blocks[i])
                last = Block.from_tuple(blocks[i-1])

                if current.hash() != blocks[i][-1]:
                    return False
                if last.hash() != blocks[i-1][-1]:
                    return False
                if not self.valid(last, current):
                    return False
        
        return True

    @staticmethod
    def valid(lastBlock: Block,  newBlock: Block):
        if lastBlock.hash() != newBlock.prevHash:
            return False
        if newBlock.timestamp > int(time()):
            return False
        dif = difficulty(lastBlock.timestamp, newBlock.timestamp)
        if dif > 64:
            return False
        if newBlock.hash()[:dif] != '0'*dif:
            return False
        return True
    
    @SQLsafe
    def insertNewBlock(self, newBlock: Block):
        if self.valid(self.lastBlock(), newBlock):
            self.openConnection()
            with self.con:
                self.cur.execute(
                    'INSERT INTO Block VALUES (?, ?, ?, ?, ?)',
                    newBlock.to_tuple()
                )
                self.con.commit()
            self.closeConnection()
        else:
            raise InvalidBlock(newBlock)
    
    @SQLsafe
    def lastBlock(self):
        try:
            t = self.cur.execute('''
                    SELECT * FROM Block ORDER BY ROWID DESC LIMIT 1
                ''').fetchall()[0]
        except IndexError:
            return None
        
        return Block.from_tuple(t)
    
    @SQLsafe
    def getBlock(self, height):
        height += 1
        try:
            t = self.cur.execute('SELECT * FROM Block WHERE ROWID = (?)', (height, )).fetchall()[0]
        except IndexError:
            return None
        
        return Block.from_tuple(t)