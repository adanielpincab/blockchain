from flask import Flask, request
from json import loads, dumps, JSONDecodeError
from uuid import uuid4
from loguru import logger
from time import time, sleep
import requests
from hashlib import sha256
from _thread import start_new_thread
from sys import argv
import blockchain

VERSION = '0.0.1'
ID = str(uuid4())
MAX_BOUNCE = 5

if len(argv) > 1:
    CONFIG_FILE = argv[1]
else:
    CONFIG_FILE = 'nodeconfig.json'

with open(CONFIG_FILE, 'r') as f:
    CONFIG = loads(f.read())
    f.close()

def saveConfig():
    with open(CONFIG_FILE, 'w') as f:
        f.write(dumps(CONFIG))
        f.close()

IP = 'http://' + CONFIG['host'] + ':' + str(CONFIG['port'])

def minutesPassed(start):
    return int((time() - start)/60)

class Message:
    def __init__(self, code, data={}):
        self.code = code
        self.sender_id = ID
        self.sender_ip = IP
        self.bounce = MAX_BOUNCE
        self.data = data
    
    @staticmethod
    def from_dict(_dict):
        m = Message('', '')
        m.__dict__ = _dict
        return m

# BLOCKCHAIN
bc = blockchain.BlockChain(dbfilename=CONFIG['blockchain_file'])

# requests client 

def get_json_data(ip, path):
    try: 
        return requests.get(ip + path, timeout=5).json()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        if ip in CONFIG['nodes']:
            logger.error('Node ' + ip + ' timed out. Removing it from list of nodes.')
            CONFIG['nodes'].remove(ip)

def send(ip, path, json):
    try: 
        requests.post(ip + path, json=json, timeout=2)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        if ip in CONFIG['nodes']:
            logger.error('Node ' + ip + ' timed out. Removing it from list of nodes.')
            CONFIG['nodes'].remove(ip)

def broadcast(message: Message):
    message.bounce = (message.bounce-1)%MAX_BOUNCE
    if (message.bounce > 0):
        for ip in CONFIG['nodes']:
            send(ip, '/broadcast', message.__dict__)

sync_trigger = True # forces chain syncing on startup

# process message
def process(msg: Message):
    global sync_trigger
    global bc

    if msg.code == 'HELLO':
        if (not msg.sender_ip in CONFIG['nodes']) and (not msg.sender_ip == IP):
            CONFIG['nodes'].append(msg.sender_ip)
            saveConfig()
            logger.info('New node connected: ' + msg.sender_ip)
        broadcast(msg)

    if msg.code == 'NEW_BLOCK':
        new_block = blockchain.Block.from_dict(msg.data)

        if new_block.hash() == bc.lastBlock().hash():
            return

        logger.info('New block received: ' + new_block.hash())
        try: 
            bc.insertNewBlock(new_block)
            logger.success('New block added to the blockchain: ' + new_block.hash())
            broadcast(msg)
            return 'accepted'
        except blockchain.InvalidBlock:
            logger.success('Invalid block. ' + new_block.hash())
            if new_block.prevHash() != bc.lastBlock().hash():
                logger.info('Block does not match current chain.')
                broadcast(msg)
                sync_trigger = True
            return 'denied'

# flask server (receive)
app = Flask(__name__)

@app.route('/')
@app.route('/index')
def index():
    return 'Blockchain v' + VERSION

@app.route('/broadcast', methods=['POST'])
def broadcast_receiver():
    msg = Message.from_dict(request.json)
    process(msg)
    return 'ack'

@app.route('/chain_info', methods=['GET'])
def chain_info():
    genesis = bc.getBlock(0)
    return {
        'length': bc.length(),
        'genesis': genesis.hash(),
        'date_start': genesis.timestamp
    }

@app.route('/block/<height>', methods=['GET'])
def get_block(height):
    if height == 'last':
        block = bc.lastBlock()
    else:
        try:
            height = int(height)
        except:
            return 'Error.'
        
        block = bc.getBlock(height)
    return block.to_dict()

@app.route('/new_block', methods=['POST'])
def new_block():
    return process(Message('NEW_BLOCK', dict(request.json)))

logger.debug('Starting Flask server...')
start_new_thread(lambda: app.run(CONFIG['host'], CONFIG['port']), ())
logger.debug('Flask server started.')

# node

def sync_chain():
    global bc

    logger.debug('Looking up chains...')
    best = None
    for n in CONFIG['nodes']:
        chain_info = get_json_data(n, '/chain_info')
        
        try:
            dens = chain_info['length']/minutesPassed(chain_info['date_start'])
        except ZeroDivisionError:
            dens = 0
        
        if not best:
            best = (dens, n, chain_info)
        else:
            if best[0] < dens:
                best = (dens, n, chain_info)
    
    if not best:
        logger.debug('No better chain found.')
        return

    dens, node_ip, chain_info = best
    try:
        self_dens = bc.length()/minutesPassed(bc.getBlock(0).timestamp)
    except ZeroDivisionError:
        self_dens = 0

    if dens > self_dens:
        logger.debug('Found better chain. Updating...')
        # either I'm in the wrong chain or I am behind the last block
        if chain_info['genesis'] != bc.getBlock(0).hash:
            get_from = 0 # get the whole new chain
        else:
            get_from = bc.length()+1 # only get the latest blocks
        
        for h in range(get_from, chain_info['length']):
            if h == 0:
                # reset blockchain (empty)
                bc.closeConnection()
                open(CONFIG['blockchain_file'], 'w').close()
                
                # get genesis and start new chain with it
                genesis = blockchain.Block.from_dict(get_json_data(node_ip, '/block/0'))
                bc = blockchain.BlockChain(dbfilename=CONFIG['blockchain_file'], genesisBlock=genesis)
                logger.success('New genesis block: ' + genesis.hash())
            else: 
                new_block = blockchain.Block.from_dict(get_json_data(node_ip, '/block/'+str(h)))
                bc.insertNewBlock(new_block)
                logger.success('New block: ' + new_block.hash())
    
    logger.debug('Chain updated.') 

logger.debug('Saying hello...')
broadcast(Message('HELLO'))

while True:
    if sync_trigger:
        sync_trigger = False
        sync_chain()
    sleep(1)