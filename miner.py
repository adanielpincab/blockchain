from blockchain import Block, BlockChain, reward, Transaction
import requests
from json import loads
from time import sleep, time
from loguru import logger

with open('minerconfig.json', 'r') as f:
    CONFIG = loads(f.read())
    
blockchain = BlockChain(dbfilename=CONFIG['blockchain_file'])

valid_transactions = []

def update_pool():
    global valid_transactions
    valid_transactions = []

    logger.info('Updating transaction pool...')
    transactions = get_json_data(CONFIG['node'], '/transaction_pool')

    for t in transactions:
        t = Transaction.from_dict(t)
        
        if not t.verify():
            continue

        utxos = {}

        for utxo in blockchain.get_utxos():
            utxos[utxo[0]] = utxo[3]

        balance = 0

        for i in t.inputs:
            # all inputs are unspent outputs
            pass
        
        valid_transactions.append(t)

def minutesPassed(start):
    return int((time() - start)/60)

def get_json_data(ip, path):
    try: 
        return requests.get(ip + path, timeout=5).json()
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        if ip in CONFIG['nodes']:
            logger.error('Node ' + ip + ' timed out. Removing it from list of nodes.')
            CONFIG['nodes'].remove(ip)

def sync_chain():
    global blockchain

    logger.debug('Looking up chain...')
    chain_info = get_json_data(CONFIG['node'], '/chain_info')

    logger.debug('Updating chain...')
    # either I'm in the wrong chain or I am behind the last block
    if chain_info['genesis'] != blockchain.getBlock(0).hash:
        get_from = 0 # get the whole new chain
    else:
        get_from = blockchain.length()+1 # only get the latest blocks

    for h in range(get_from, chain_info['length']):
        if h == 0:
            # reset blockchain (empty)
            blockchain.closeConnection()
            open(CONFIG['blockchain_file'], 'w').close()
            
            # get genesis and start new chain with it
            genesis = Block.from_dict(get_json_data(CONFIG['node'], '/block/0'))
            blockchain = BlockChain(dbfilename=CONFIG['blockchain_file'], genesisBlock=genesis)
            logger.success('New genesis block: ' + genesis.hash())
        else: 
            print(get_json_data(CONFIG['node'], '/block/'+str(h)))
            new_block = Block.from_dict(get_json_data(CONFIG['node'], '/block/'+str(h)))
            print(new_block.__dict__)
            blockchain.insertNewBlock(new_block)
            logger.success('New block: ' + new_block.hash())
    logger.debug('Chain updated.')

while True:
    sync_chain()
    update_pool()

    last_block = blockchain.lastBlock()
    new_block = Block(prevHash=last_block.hash())

    rew = reward(blockchain.length()-1)

    new_block.addTransaction(Transaction([], [{'address':CONFIG['address'], 'amount':rew}]))
    for t in valid_transactions:
        new_block.addTransaction(t)

    print('Waiting to mine.')
    while not (time() - last_block.timestamp) > 30:
        pass
    
    print('Mining...')
    while not BlockChain.valid(last_block, new_block):
        new_block.nonce += 1
        new_block.timestamp = int(time())
    
    print('New block mined.')

    requests.post(CONFIG['node']+'/new_block', json=new_block.to_dict())

    sleep(1)