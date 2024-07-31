from p2pnetwork.node import Node
from uuid import uuid4
from json import loads, dumps
import blockchain
from loguru import logger
from time import time, sleep
from sys import argv
import os

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

def minutesPassed(start):
    return int((time() - start)/60)

if len(argv) > 1:
    CONFIG_FILE = argv[1]
else:
    CONFIG_FILE = 'nodeconfig.json'
 
with open(CONFIG_FILE, 'r') as f:
    CONFIG = loads(f.read())
    f.close()

class P2PNode(Node):
    def __init__(self, host, port, id=None, callback=None, max_connections=0):
        super(P2PNode, self).__init__(host, port, id, callback, max_connections)

        self.bc = blockchain.BlockChain(CONFIG['blockchain_file'])
        self.responses = {}
        self.transaction_pool = []

    def outbound_node_connected(self, connected_node):
        print("outbound_node_connected: " + connected_node.id)

    def inbound_node_connected(self, connected_node):
        print("inbound_node_connected: " + connected_node.id)
        self.send_to_nodes(Message('NEW_NODE', {'host':connected_node.host, 'port':int(connected_node.port)}).to_json())

    def inbound_node_disconnected(self, connected_node):
        print("inbound_node_disconnected: " + connected_node.id)

    def outbound_node_disconnected(self, connected_node):
        print("outbound_node_disconnected: " + connected_node.id)

    def ask(self, node, message):
        self.responses[message.id] = None
        
        self.send_to_node(node, message.to_json())

        while not self.responses[message.id]:
            sleep(0.1)
        
        res = dict(self.responses[message.id])
        del self.responses[message.id]
        return res
    
    def sync_chain(self):
        # get chain from all connected nodes, checks if there's a better blockchain

        better = None 
        self_dens = self.bc.length()/minutesPassed(self.bc.getBlock(0).timestamp)

        for node in self.all_nodes:
            node_chain_data = self.ask(node, Message('CHAIN_INFO?'))

            dens = node_chain_data['length']/minutesPassed(node_chain_data['started_in'])

            if self_dens > dens:
                continue

            if better == None:
                node_chain_data['node'] = node
                node_chain_data['dens'] = dens
                better = node_chain_data
            elif (dens > better['dens']):
                node_chain_data['node'] = node
                node_chain_data['dens'] = dens
                better = node_chain_data

        if not better:
            logger.info('no better chain found.')
            return # if there's no better, return
        
        # sync with best chain.              
        logger.success('better blockchain found!')                                           
        self_last_exists = self.ask(node, Message('HAVE_THIS_BLOCK_HASH?', {'hash':self.bc.lastBlock().hash()}))['exists']   
        new_chain = False
        next_height = None
        if not self_last_exists:
            logger.success('need to reset chain.')
            new_chain = True
            next_height = 0
        else:
            logger.success('no need to reset chain.')
            next_height = self.bc.length()
        
        while self.bc.length() < better['length']:
            logger.info(f"Updating chain ({self.bc.length()}/{better['length']})")
            next_block = blockchain.Block.from_dict(self.ask(node, Message('BLOCK?', {'height': next_height})))
            if new_chain:
                os.remove(CONFIG['blockchain_file'])
                self.bc = blockchain.BlockChain(CONFIG['blockchain_file'], genesisBlock=next_block)
                new_chain = False
            else:
                self.bc.insertNewBlock(next_block)

            next_height += 1
        
        logger.success('chain updated.')

    def node_message(self, connected_node, data):
        # print(str(self.id) + " node_message from " + connected_node.id + ": " + str(data))

        msg = Message.from_dict(data)

        if msg.response_to:
            if msg.response_to in self.responses.keys():
                self.responses[msg.response_to] = msg.data

        if msg.code == 'NEW_NODE':
            node = msg.data
            if (node['host'] == CONFIG['host']) and (int(node['port']) == int(CONFIG['port'])):
                return
            
            for n in self.all_nodes:
                if (node['host'] == n.host) and (int(node['port']) == int(n.port)):
                    return

            if self.connect_with_node(node['host'], node['port']):
                self.send_to_nodes(Message('NEW_NODE', {'host':connected_node.host, 'port':int(connected_node.port)}).to_json())

        elif msg.code == 'NEW_BLOCK':
            new_block = blockchain.Block.from_dict(msg.data)

            if new_block.hash() == self.bc.lastBlock().hash():
                return

            logger.info('New block received: ' + new_block.hash())

            try:
                self.bc.insertNewBlock(new_block)
                logger.success('New block added to the blockchain: ' + new_block.hash())

                # remove transactions unvalidated by new block
                for i in range(len(self.transaction_pool)):
                    t = self.transaction_pool.pop(0)
                    if self.valid_transaction(t):
                        self.transaction_pool.append(t)

                self.send_to_nodes(msg.to_json())
            except blockchain.InvalidBlock:
                logger.error('Invalid block. ' + new_block.hash())
                if new_block.prevHash != self.bc.lastBlock().hash():
                    logger.error('Block does not match current chain.')
                    self.syncing_thread = self.sync_chain()
            except blockchain.InvalidBlockTransaction:
                logger.error('Invalid transaction in block. ' + new_block.hash())
                self.sync_chain()

        elif msg.code == 'NEW_TRANSACTION':
            new_transaction = blockchain.Transaction.from_dict(msg.data)

            if new_transaction in self.transaction_pool:
                return

            logger.info('New transaction received: ' + new_transaction.hash())

            if self.valid_transaction(new_transaction):
                logger.success('New transaction added to the pool: ' + new_transaction.hash())
                self.send_to_nodes(msg.to_json())
            else:
                logger.error('Invalid transaction: ' + new_transaction.hash())
        
        elif msg.code == 'CHAIN_INFO?':
            res = msg.response('CHAIN_INFO', {'started_in': self.bc.getBlock(0).timestamp, 'length': self.bc.length(), 'genesis':self.bc.getBlock(0).hash()})
            self.send_to_node(connected_node, res.to_json())

        elif msg.code == 'HAVE_THIS_BLOCK_HASH?':
            self.send_to_node(connected_node, msg.response('HAVE_THIS_BLOCK_HASH', {'exists': self.bc.block_exists(msg.data['hash'])}).to_json())
        
        elif msg.code == 'BLOCK?':
            self.send_to_node(connected_node, msg.response('BLOCK', self.bc.getBlock(msg.data['height']).to_dict()).to_json())
    
    def valid_transaction(self, transaction: blockchain.Transaction):
        '''Returns Fee in case of valid'''

        if not transaction.verify():
            return False

        utxos = self.bc.get_utxos()
        fee = 0

        for i in transaction.inputs:
            if not i in utxos.keys():
                return False
            if utxos[i]['address'] != blockchain.Address.generate_blockchain_address(transaction.signature[0]):
                return False
            fee += utxos[i]['amount']
        
        for o in transaction.outputs:
            fee -= o['amount']
        
        if fee < 0:
            return False
        
        return (True, fee)

    def create_next_block(self):
        last_block = self.bc.lastBlock()
        new_block = blockchain.Block(prevHash=last_block.hash())
        rew = blockchain.reward(node.bc.length()-1)
        for t in self.transaction_pool:
            rew += self.valid_transaction(t)[1]
        new_block.addTransaction(blockchain.Transaction([], [{'address':CONFIG['mining_address'], 'amount':rew}]))
        for t in self.transaction_pool:
            new_block.addTransaction(t)
        return new_block

    def mine(self):
        while True:
            last_block = self.bc.lastBlock()
            new_block = self.create_next_block()

            logger.info('Waiting to mine.')
            while not (time() - last_block.timestamp) > 30:
                pass
            
            logger.info('Mining...')
            while not blockchain.BlockChain.valid(last_block, new_block):
                new_block.nonce += 1
                new_block.timestamp = int(time())

                if last_block != self.bc.lastBlock():
                    last_block = self.bc.lastBlock()
                    new_block = self.create_next_block()

            logger.success('New block mined.')

            self.bc.insertNewBlock(new_block)

            self.send_to_nodes(Message('NEW_BLOCK', new_block.to_dict()).to_json())
            sleep(1)

    def node_disconnect_with_outbound_node(self, connected_node):
        print("node wants to disconnect with oher outbound node: " + connected_node.id)
        
    def node_request_to_stop(self):
        print("node is requested to stop!")

node = P2PNode(CONFIG['host'], int(CONFIG['port']))
node.start()
for host, port in CONFIG['nodes']:
    node.connect_with_node(host, int(port))

node.sync_chain()
node.mine()