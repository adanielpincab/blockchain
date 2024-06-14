import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.pardir, 'blockchain')))

from blockchain import Block, BlockChain, reward, Transaction, Address
import requests
from json import loads, dumps
from time import sleep, time
from loguru import logger
from _thread import start_new_thread
from flask import Flask, render_template, url_for, redirect
from flask_socketio import SocketIO
import crypto

with open('walletconfig.json', 'r') as f:
    CONFIG = loads(f.read())
    f.close()

open(CONFIG['wallet_file'], 'a').close()
with open(CONFIG['wallet_file'], 'r') as f:
    data = f.read()
    if data == '':
        WALLET = {}
    else:
        WALLET = loads(data)
    f.close()

def save_data():
    with open(CONFIG['wallet_file'], 'w') as f:
        f.write(dumps(WALLET))

blockchain = BlockChain(dbfilename=CONFIG['blockchain_file'])

update_ui = False

def get_json_data(ip, path):
    try: 
        return requests.get(ip + path, timeout=5).json()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return None

# --- SYNC CHAIN
def sync_chain():
    global blockchain
    global update_ui

    while True:
        logger.debug('Looking up chain...')
        chain_info = get_json_data(CONFIG['node'], '/chain_info')

        logger.debug('Updating chain...')

        # either I'm in the wrong chain or I am behind the last 
        
        if chain_info['genesis'] != blockchain.getBlock(0).hash():
            get_from = 0 # get the whole new chain
        else:
            get_from = blockchain.length() # only get the latest blocks
        
        if (int(time())-blockchain.lastBlock().timestamp > 30):
            wait_secs = 10
        else:
            wait_secs = 30

        for h in range(get_from, chain_info['length']):
            wait_secs = 30
            if h == 0:
                # reset blockchain (empty)
                blockchain.closeConnection()
                open(CONFIG['blockchain_file'], 'w').close()
                
                # get genesis and start new chain with it
                genesis = Block.from_dict(get_json_data(CONFIG['node'], '/block/0'))
                blockchain = BlockChain(dbfilename=CONFIG['blockchain_file'], genesisBlock=genesis)
                logger.success('New genesis block: ' + genesis.hash())
            else: 
                new_block = Block.from_dict(get_json_data(CONFIG['node'], '/block/'+str(h)))
                blockchain.insertNewBlock(new_block)
                logger.success('New block: ' + new_block.hash())
        logger.debug('Chain updated.')
        update_ui = True
        sleep(wait_secs)

start_new_thread(sync_chain, ())
# --- SYNC CHAIN

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
@app.route('/index')
def index():
    update_ui = True
    if WALLET == {}:
        return render_template('index.html', first_time=True)
    
    return render_template('index.html', first_time=False)

@socketio.on('create_new')
def create_new(data):
    if WALLET != {}:
        return
    
    a = Address()
    WALLET['address'] = a.address
    WALLET['private'] = crypto.private_to_pem_bytes(a.priv, data['password']).decode()
    save_data()

    socketio.emit('my_addresses_response', WALLET['address'])

@socketio.on('my_address')
def my_address():
    socketio.emit('my_addresses_response', WALLET['address'])

@socketio.on('request_update')
def my_address():
    update_ui = True

@socketio.on('get_transactions')
def handle(data):
    blockchain.get_utxos
    socketio.emit('response', 'Server received your message: ' + data)

# --- UI UPDATER ---
transactions = []
balance = 0

def get_transaction_pool_utxos():
    pool = get_json_data(CONFIG['node'], '/transaction_pool')
    res = []
    for t in pool:
        t = Transaction.from_dict(t)
        for out in t.outputs:
            if out['address'] == WALLET['address']:
                out['transaction'] = t.hash()
                res.append(out) 

    return res   

def calc_from_utxos():
    global balance
    global transactions
    global address

    utxos = blockchain.get_utxos()

    transactions = []
    balance = 0

    for u in [*utxos.values(), *get_transaction_pool_utxos()]:
        if u['address'] == WALLET['address']:
            balance += u['amount']
            transactions.append(blockchain.get_transaction(u['transaction']).to_dict())
    
    transactions.reverse()

def ui_updater():
    global update_ui
    global balance

    while True:
        while not update_ui:
            pass
        update_ui = False

        calc_from_utxos()
        
        socketio.emit('ui_update', {
            'balance': balance,
            'address':WALLET['address'],
            'transactions':transactions
            })

start_new_thread(ui_updater, ())
# ^^^ UI UPDATER ^^^

app.run(CONFIG["frontend_host"], CONFIG["frontend_port"], debug=True)