from blockchain import Block, BlockChain, reward
import requests
from time import sleep, time

node = 'http://localhost:5050'

while True:
    last_block = Block.from_dict(requests.get(node+'/block/last').json())
    new_block = Block(prevHash=last_block.hash())

    while not (time() - last_block.timestamp) > 30:
        pass

    while not BlockChain.valid(last_block, new_block):
        new_block.nonce += 1
        new_block.timestamp = int(time())
    
    print('New block mined.')
    print(new_block.to_dict())

    print(
        requests.post(node+'/new_block', json=new_block.to_dict()).text
    )
    sleep(1)