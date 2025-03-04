from p2pnetwork.node import Node
from uuid import uuid4
from json import loads, dumps
import blockchain
from loguru import logger
from time import time, sleep
from sys import argv
import os
from cryptography.fernet import Fernet
from crypto import generate_key_pair, sign, verify, pem_bytes_to_private, private_to_pem_bytes
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit

from blockchain.network import BlockchainNode, Message

if len(argv) > 1:
    CONFIG_FILE = argv[1]
else:
    CONFIG_FILE = 'walletconfig.json'
 
with open(CONFIG_FILE, 'r') as f:
    CONFIG = loads(f.read())
    f.close()

class WalletNode(BlockchainNode):
    def __init__(self, host, port, blockchain_file, name, password, ui_update_func):
        super().__init__(host, port, blockchain_file=blockchain_file)
        
        self.name = name
        self.wallet_file = f'{name}.wallet'
        self.address = None

        if os.path.exists(self.wallet_file):
            with open(self.wallet_file, 'rb') as f:
                self.private_key_encrypted = f.read()
            self.address = blockchain.Address(pem_bytes_to_private(self.private_key_encrypted, password))
        else:
            self.address = blockchain.Address()
            with open(self.wallet_file, 'wb') as f:
                f.write(private_to_pem_bytes(self.address.priv, password))
                f.close()
        self.ui_update_func = ui_update_func
        self.update()

    def node_message(self, connected_node, data):
        super().node_message(connected_node, data)

        if self.bc.lastBlock().hash() != self.block_last_update:
            self.update()
    
    def its_mine(transaction: blockchain.Transaction):
        for out in tx.ouputs:
            if out['address'] == self.address.address:
                return True
        for utxo_hash in tx.inputs:
            if id in self.utxos.keys():
                return True
        
        return False

    def new_transaction(self, new_transaction: blockchain.Transaction):
        super().new_transaction(new_transaction)

    def update(self):
        self.utxos = {}
        self.transactions = []
        self.transactions_in_pool = set()
        self.balance = 0
        self.block_last_update = 0

        for id, utxo in self.bc.get_utxos().items():
            if utxo["address"] == self.address.address:
                self.utxos[id] = utxo
        
        #confirmed transactions
        self.transactions = self.bc.get_all_transactions_for_address(self.address.address)

        # unconfirmed transactions
        for tx in self.transaction_pool:
            if self.its_mine(tx):
                self.transactions_in_pool.add(tx)
                for utxo_hash in tx.inputs:
                    if id in self.utxos.keys():
                        del self.utxos[id]
        
        for utxo in self.utxos.values():
            self.balance += utxo['amount']

        self.block_last_update = self.bc.lastBlock().hash()

    def get_transactions(self):
        return self.transactions
    
    def get_balance(self):
        return self.balance
    
    def get_utxos(self):
        return self.utxos

NAME = "test"
PASSWORD = "test"

def ui_update():
    if node:
        socketio.emit('update', {'balance': node.balance, 'utxos': node.utxos, 'transactions': node.transactions, 'transactions_in_pool': node.transactions_in_pool})

node = WalletNode(host=CONFIG['host'], port=int(CONFIG['port']), blockchain_file=CONFIG['blockchain_file'], name=NAME, password=PASSWORD, ui_update_func=ui_update)
for host, port in CONFIG['nodes']:
    node.connect_with_node(host, int(port))
node.sync_chain()

app = Flask(__name__)
socketio = SocketIO(app,debug=True,cors_allowed_origins='*')

@app.route('/transactions/total', methods=['get'])
def transactions_total():
    return jsonify({'total': len(node.get_transactions())})

@app.route('/transactions/<start>/<end>', methods=['get'])
def transactions(start, end):
    return jsonify({'transactions': 
    [ t.json() for t in node.get_transactions()[int(start):int(end)] ]})

@app.route('/balance', methods=['get'])
def balance():
    return jsonify({'balance': node.get_balance()})

@app.route('/utxos', methods=['get'])
def utxos():
    return jsonify({'utxos': node.get_utxos()})

@socketio.on('message')
def handle_message(data):
    print('received message: ' + data)

@app.route('/')
@app.route('/index')
@app.route('/home')
def index():
    return render_template('app.html')
    
node.start()
app.run(host="localhost", port="9999")