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
        self.inputs = inputs # [utxo_hash 1, ... utxo_hash N]
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
        if self.signature == [None, None]:
            return False
        return crypto.verify(
            self.signature[1], 
            self.hash().encode(), 
            crypto.public_deserialized(
                self.signature[0]
            )
        )
    
    def to_dict(self):
        return self.__dict__
    
    @staticmethod
    def from_dict(dct):
        t = Transaction([], [])
        t.__dict__ = dct
        return t

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

    def load_inputs_from_tuples(self, tuple_list):
        for t in tuple_list:
            self.inputs.append(t[1]) # input
    
    def outputs_to_tuples(self):
        res = []
        h = self.hash()
        for o in self.outputs:
            res.append( (
                sha256(str((h, o['address'], o['amount'])).encode()).hexdigest(), 
                h, 
                o["address"], 
                o["amount"]
                ) )
        return res
    
    def load_outputs_from_tuples(self, tuple_list):
        for t in tuple_list:
            self.outputs.append({'address':t[2], 'amount':t[3]})
    
    @classmethod
    def from_tuple(self, tup):
        t = Transaction([], [])
        t.timestamp = tup[0]
        t.signature = [tup[1], tup[2]]
        return t

class Address:
    def __init__(self, priv_key=None):
        if not priv_key:
            self.priv, self.pub = crypto.generate_key_pair()
        else:
            self.priv = priv_key
            self.pub = self.priv.public_key()
        
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
            try:
                ind = level.index(hash)
            except ValueError:
                return None
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
        self.transactionsRaw = [] # transaction dicts
        self.transactionsTree = Merkle() # merkle tree (transaction hashes)
        self.transactionsRoot = None # root of the merkle tree
        self.timestamp = int(time())
        self.nonce = 0
        self.prevHash = prevHash

    def addTransaction(self, transaction: Transaction):
        transaction_hash = transaction.hash()
        self.transactionsTree.add(transaction_hash)
        self.transactionsRaw.append(transaction.to_dict())
        self.transactionsRoot = self.transactionsTree.root()
    
    def hash(self):
        return sha256(str([
            self.transactionsRoot,
            self.timestamp,
            self.nonce,
            self.prevHash
        ]).encode()).hexdigest()
    
    def to_dict(self):
        return {
            'transactions':self.transactionsRaw,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'prevHash': self.prevHash
        }
    
    @staticmethod
    def from_dict(dct):
        b = Block()
        b.timestamp = dct['timestamp']
        b.nonce = dct['nonce']
        b.prevHash = dct['prevHash']

        for td in dct['transactions']:
            b.addTransaction(Transaction.from_dict(td))

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

class InvalidBlockTransaction(Exception):
    def __init__(self, block: Block, transaction: Transaction):
        super().__init__(
            'Transaction ' + transaction.hash() + ' es not valid in block ' + block.hash()
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
        if not self.valid(self.lastBlock(), newBlock):
            raise InvalidBlock(newBlock)

        if newBlock.transactionsRaw != []:
            utxos = self.get_utxos()

            fees = 0
            for i in range(1, len(newBlock.transactionsRaw)): # transctions after coinbase
                t = Transaction.from_dict(newBlock.transactionsRaw[i])
                for _in in t.inputs: # any other transaction
                    if not _in in utxos.keys(): # already spent, or unexistent
                        raise InvalidBlockTransaction(t, newBlock)
                    if (
                        utxos[_in]['address'] != 
                        Address.generate_blockchain_address(t.signature[0])
                        ): # unspent, but don't belong to the sender
                        raise InvalidBlockTransaction(t, newBlock)
                    fees += utxos[_in]['amount']
                for out in t.outputs:
                    fees -= out['amount']
            
            # coinbase transaction
            t = Transaction.from_dict(newBlock.transactionsRaw[0])
            rew = reward(self.length()-1) + fees
            if t.inputs != []:
                raise InvalidBlockTransaction(t, newBlock)
            if len(t.outputs) != 1:
                raise InvalidBlockTransaction(t, newBlock)
            if t.outputs[0]['amount'] > rew:
                raise InvalidBlockTransaction(t, newBlock)

        self.openConnection()
        with self.con:
            self.cur.execute(
                'INSERT INTO Block VALUES (?, ?, ?, ?, ?)',
                newBlock.to_tuple()
            )
        for t in newBlock.transactionsRaw:
            t = Transaction.from_dict(t)
            proof = newBlock.transactionsTree.proof(t.hash())
            if not proof:
                raise InvalidBlockTransaction(newBlock, t)
            self.cur.execute(
                'INSERT INTO TInBlock VALUES (?, ?)',
                (t.hash(), newBlock.hash())
            )
            self.cur.execute(
                'INSERT INTO TTransaction VALUES (?, ?, ?, ?)',
                (t.timestamp, t.signature[0], t.signature[1], t.hash())
            )
            for inp in t.inputs_to_tuples():
                self.cur.execute(
                    'INSERT INTO TInput VALUES (?, ?)',
                    inp
                )
            for out in t.outputs_to_tuples():
                self.cur.execute(
                    'INSERT INTO TOutput VALUES (?, ?, ?, ?)',
                    out
                )
        self.con.commit()
    
    @SQLsafe
    def get_utxos(self):
        utxos = {}
        utxos_tuple = self.cur.execute('''
        SELECT * FROM TOutput WHERE NOT EXISTS (SELECT * FROM TInput WHERE TInput.utxo_hash = TOutput.hash)
        ''').fetchall()
        for i in utxos_tuple:
            utxos[i[0]] = {'address':i[2], 'amount':i[3]} # utxo_hash, utxo_address, utxo_quant
        return utxos

    @SQLsafe
    def lastBlock(self):
        return self.getBlock(self.length()-1)
    
    @SQLsafe
    def getBlock(self, height):
        height += 1
        try:
            t_block = self.cur.execute('SELECT * FROM Block WHERE ROWID = (?)', (height, )).fetchall()[0]
            block = Block.from_tuple(t_block)
            block_transaction_hashes = self.cur.execute('SELECT * FROM TInBlock WHERE block_hash = (?)', (block.hash(), )).fetchall()
            for (th, bh) in block_transaction_hashes:
                trans = self.get_transaction(th)
                block.addTransaction(trans)
        except IndexError:
            return None

        return block
    
    @SQLsafe
    def get_transaction(self, t_hash):
        try:
            transaction_tuple = self.cur.execute('SELECT * FROM TTransaction WHERE hash = (?)', (t_hash, )).fetchall()[0]
            inputs_tuple = self.cur.execute('SELECT * FROM TInput WHERE tx_hash = (?)', (t_hash,)).fetchall()
            outputs_tuple = self.cur.execute('SELECT * FROM TOutput WHERE tx_hash = (?)', (t_hash,)).fetchall()
        except IndexError:
            return None
        
        trans = Transaction.from_tuple(transaction_tuple)
        trans.load_inputs_from_tuples(inputs_tuple)
        trans.load_outputs_from_tuples(outputs_tuple)

        return trans
    
