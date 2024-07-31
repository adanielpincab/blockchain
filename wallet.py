from sys import argv
from blockchain import Address, BlockChain, Transaction
from crypto import private_to_pem_file, private_from_pem_file
from getpass import getpass
from p2pnetwork.node import Node
from uuid import uuid4
from json import dumps, loads

HOST, PORT = ('localhost', 8888)
db_filename = 'bc1.db'
blockchain = BlockChain(db_filename)
BROADCAST_NODE = ('localhost', 8081)

if len(argv) > 2:
    print('Error. This script only accepts one argument (wallet file)')

class Message:
    def __init__(self, code, data={}):
        self.code = code
        self.data = data
        self.id = str(uuid4())
        self.response_to = None
    
    def to_json(self):
        return dumps(self.__dict__)
    
    @staticmethod
    def from_json(_json):
        new = Message('')
        new.__dict__ = loads(_json)
        return 
    
    @staticmethod
    def from_dict(_dict):
        new = Message('')
        new.__dict__ = _dict
        return new
    
    def __repr__(self) -> str:
        return str(self.to_json())
    
    def response(self, code, data={}):
        res = Message(code, data)
        res.response_to = self.id
        return res

class App:
    def __init__(self):
        self.wallet = None
        self.balance = 0
        self.utxos = []

    def load_wallet(self):
        if len(argv) == 1:
            print('No wallet file provided. Creating new wallet.')

            self.wallet = Address()

            filename = input('Enter the name of your new wallet:') + '.wallet'
            password = getpass(prompt='Enter password for your new wallet:')
            
            private_to_pem_file(self.wallet.priv, filename, password)

        else:
            password = getpass(prompt='Enter your wallet password:')
            self.wallet = Address(priv_key=private_from_pem_file(argv[1], password))

    def display_balance(self):
        self.balance = 0
        self.utxos = []

        for hash, data in self.blockchain.get_utxos().items():
            if data['address'] == self.wallet.address:
                self.balance += data['amount']
                self.utxos.append({'hash':hash, 'amount':data['amount']})
        print(f'BALANCE: {self.balance/1000000}')

    def select(self):
        selection = None
        while not selection:
            print("select your action:")
            print("\t1. Send")
            
            selection = input('> ')
            if not selection in ['1']:
                print('Invalid number.')
                selection = None
        return selection

    def send_to_address(self):
        self.display_balance()
        amount = None
        while not amount:
            try:
                amount = float(input('Select amount to send: '))
            except ValueError:
                print('Not a valid number.')
                amount = None
            
            amount *= 1000000
            if (amount <= 0) or (amount > self.balance):
                print('Not a valid amount. Check balance.')
                amount = None
        receiver = input('Enter address to send: ')

        using_utxos = []
        change = 0
        outputs = [{'address': receiver, 'amount': amount}]

        final_amount = amount
        for utxo in self.utxos:
            if utxo['amount'] <= amount:
                amount -= utxo['amount']
                using_utxos.append(utxo['hash'])
            elif utxo['amount'] > amount:
                change = utxo['amount'] - amount
                using_utxos.append(utxo['hash'])
                amount = 0
            if amount == 0:
                break
        
        if change > 0:
            outputs.append({'address': self.wallet.address, 'amount': change})

        transaction = Transaction(inputs=using_utxos, outputs=outputs)
        transaction.signature = self.wallet.sign(transaction.hash())

        print('SEND TO Address:', receiver, 'AMOUNT:', final_amount)
        confirmation = input('CONFIRM? (Y/N)')

        if confirmation.upper() in ['Y', 'YES']:
            node = Node(HOST, PORT)
            node.start()
            node.connect_with_node(BROADCAST_NODE[0], BROADCAST_NODE[1])
            node.send_to_nodes(Message('NEW_TRANSACTION', data=transaction.to_dict()).to_json())
            node.stop()
            print('Transaction sent for confirmation.')
        else:
            print('Transaction cancelled.')


    def run(self):
        self.blockchain = BlockChain(db_filename)
        self.load_wallet()
        print(self.wallet.address)
        while True:
            self.display_balance()
            command = self.select()
            if command == '1':
                self.send_to_address()

app = App()
app.run()