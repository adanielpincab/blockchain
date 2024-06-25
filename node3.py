from p2pnetwork.node import Node
from uuid import uuid4
from json import loads, dumps
import blockchain
from loguru import logger
from time import time
from sys import argv

class Message:
    def __init__(self, code, data={}):
        self.code = code
        self.data = data
        self.id = str(uuid4())
    
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
        self.asked = False
        self.transaction_pool = []
        self.transaction_pool_hashes = []
        self.best_chain = False
        self.pooled_block = None

    def outbound_node_connected(self, connected_node):
        print("outbound_node_connected: " + connected_node.id)

    def inbound_node_connected(self, connected_node):
        print("inbound_node_connected: " + connected_node.id)
        self.send_to_nodes(Message('NEW_NODE', {'host':connected_node.host, 'port':int(connected_node.port)}).to_json())

    def inbound_node_disconnected(self, connected_node):
        print("inbound_node_disconnected: " + connected_node.id)

    def outbound_node_disconnected(self, connected_node):
        print("outbound_node_disconnected: " + connected_node.id)

    def node_message(self, connected_node, data):
        print(str(self.id) + " node_message from " + connected_node.id + ": " + str(data))

        msg = Message.from_dict(data)

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
                self.send_to_nodes(msg.to_json())
            except blockchain.InvalidBlock:
                logger.error('Invalid block. ' + new_block.hash())
                if new_block.prevHash != self.bc.lastBlock().hash():
                    logger.error('Block does not match current chain.')
                    self.send_to_nodes(msg.to_json())
                    self.send_to_nodes(Message('CHAIN_INFO?').to_json())
            except blockchain.InvalidBlockTransaction:
                logger.error('Invalid transaction in block. ' + new_block.hash())
                self.send_to_nodes(Message('CHAIN_INFO?').to_json())
            
        elif msg.code == 'NEW_TRANSACTION':
            t = blockchain.Transaction.from_dict(msg.data)
            logger.info('New transaction received: ' + t.hash())

            if not t.hash() in self.transaction_pool_hashes:
                self.transaction_pool.append(t.to_dict())
                self.transaction_pool_hashes.append(t.hash())
                self.send_to_nodes(msg.to_json())
        
        elif msg.code == 'CHAIN_INFO?':
            self.send_to_node(connected_node, Message('CHAIN_INFO', 
                    {
                        'genesis': self.bc.getBlock(0).hash(),
                        'started_in': self.bc.getBlock(0).timestamp, 
                        'height': self.bc.length()-1
                    }).to_json())
        
        elif msg.code == 'CHAIN_INFO':
            chain_info = msg.data
            if chain_info['height'] < 1:
                return
            
            dens = minutesPassed(int(chain_info['started_in']))/int(chain_info['height'])
            self_dens = minutesPassed(self.bc.getBlock(0).timestamp)/(self.bc.length()-1)

            if ((dens > self_dens) and (chain_info['started_in'] <= self.bc.getBlock(0).timestamp)):
                self.best_chain = chain_info
                self.best_chain['node'] = connected_node
                logger.info('Better chain found.')

        elif msg.code == 'BLOCK?':
            height = int(msg.data['height'])

            if height > self.bc.length-1:
                self.send_to_nodes(Message('CHAIN_INFO?').to_json())
                return
            
            self.send_to_node(connected_node, Message('BLOCK', {'height': height, 'block':self.bc.getBlock(height).to_json()}))
        
        elif msg.code == 'BLOCK':
            if msg.data['height'] == self.bc.length():
                self.pooled_block = blockchain.Block.from_dict(msg.data['block'])

        
        # updating chain
        
        if self.best_chain:
            logger.info('Updating blockchain...')
            if self.bc.getBlock(0).hash == self.best_chain['genesis']:
                if not self.pooled_block:
                    self.send_to_node(self.best_chain['node'], Message('BLOCK?', {'height': self.bc.length()}).to_json())
                else:
                    try:
                        self.bc.insertNewBlock(new_block)
                        logger.success('New block added to the blockchain: ' + new_block.hash())
                    except:
                        # same genesis, but different blocks. Restart blockchain
                        self.pooled_block = None
                        open(CONFIG['blockchain_file'], 'w').close()
                
                        # get genesis and start new chain with it
                        self.restart_genesis = blockchain.Block.from_dict(get_json_data(node_ip, '/block/0'))
                        bc = blockchain.BlockChain(dbfilename=CONFIG['blockchain_file'], genesisBlock=genesis)
        
    def node_disconnect_with_outbound_node(self, connected_node):
        print("node wants to disconnect with oher outbound node: " + connected_node.id)
        
    def node_request_to_stop(self):
        print("node is requested to stop!")

node = P2PNode(CONFIG['host'], int(CONFIG['port']))
node.start()
for host, port in CONFIG['nodes']:
    node.connect_with_node(host, int(port))
node.send_to_nodes(Message('CHAIN_INFO?').to_json())