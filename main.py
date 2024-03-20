import blockchain
from time import time, sleep

check = int(time())

while True:
    print(int(time()) - check, blockchain.difficulty(check, int(time())))
    sleep(1)