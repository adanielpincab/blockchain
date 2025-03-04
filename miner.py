from p2pnetwork.node import Node
from uuid import uuid4
from json import loads, dumps
import blockchain
from loguru import logger
from time import time, sleep
from sys import argv
import os

from blockchain.network import BlockchainNode, Message

if len(argv) > 1:
    CONFIG_FILE = argv[1]
else:
    CONFIG_FILE = 'minerconfig.json'
 
with open(CONFIG_FILE, 'r') as f:
    CONFIG = loads(f.read())
    f.close()

class Miner(BlockchainNode):
    def create_next_block(self):
        self.clean_transaction_pool()

        new_block = self.bc.get_new_block_template()
        
        rew = blockchain.reward(node.bc.length()-1)
        
        for t in self.transaction_pool:
            rew += self.valid_transaction(t)[1]
        if rew > 0:
            new_block.addTransaction(blockchain.Transaction([], [{'address':CONFIG['mining_address'], 'amount':rew}]))
        for t in self.transaction_pool:
            new_block.addTransaction(t)
        return new_block

    def mine(self):
        while True:
            last_block = self.bc.lastBlock()
            new_block = self.create_next_block()

            block_changed = False
            new_transactions = False
            logger.info('Mining... (difficulty - ' + str(new_block.difficulty) + ')')
            while (
                (not blockchain.BlockChain.valid(last_block, new_block)) and
                (not block_changed) and
                (not new_transactions)
                ):
                new_block.nonce += 1
                new_block.timestamp = int(time())

                if last_block != self.bc.lastBlock():
                    last_block = self.bc.lastBlock()
                    new_block = self.create_next_block()
                    block_changed = True
                if len(self.transaction_pool) > len(new_block.transactionsRaw):
                    last_block = self.bc.lastBlock()
                    new_block = self.create_next_block()
                    new_transactions = True

            if block_changed:
                logger.info('Block changed. Re-starting miner.')                
            elif new_transactions:
                logger.info('New transactions. Adding them to new block.')
            else:
                logger.success('New block mined.')
                self.bc.insertNewBlock(new_block)
                self.send_to_nodes(Message('NEW_BLOCK', new_block.to_dict()).to_json())
                sleep(1)
                self.clean_transaction_pool()

node = Miner(CONFIG['host'], int(CONFIG['port']), blockchain_file=CONFIG['blockchain_file'])
node.start()
for host, port in CONFIG['nodes']:
    node.connect_with_node(host, int(port))

node.sync_chain()
node.mine()