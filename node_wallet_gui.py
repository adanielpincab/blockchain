from node import P2PNode
from flask import Flask, render_template, redirect, url_for
from sys import argv
from json import loads, dumps
from os import listdir
from os.path import isfile, join
from re import search

walletfiles = [f for f in listdir(".") if isfile(join(".", f))]
walletfiles = list(filter(lambda x: search(r'\.wallet$', x), walletfiles))

if len(argv) > 1:
    CONFIG_FILE = argv[1]
else:
    CONFIG_FILE = 'nodeconfig.json'
 
with open(CONFIG_FILE, 'r') as f:
    CONFIG = loads(f.read())
    f.close()

node = P2PNode(CONFIG['host'], int(CONFIG['port']))
node.start()
for host, port in CONFIG['nodes']:
    node.connect_with_node(host, int(port))
node.sync_chain()

WALLET = None

app = Flask(__name__)

@app.route('/')
@app.route('/index')
def index():
    if not WALLET:
        return render_template('password.html', wallet_files=walletfiles)
    
    return render_template('index.html')

@app.route('/balance')
def balance():
    if not WALLET: return
    balance = 0
    my_utxos = {}
    for hash, data in self.blockchain.get_utxos().items():
        if data['address'] == self.wallet.address:
            balance += data['amount']
            my_utxos[hash] = {'amount': data['amount']}
    
    for transaction in node.transaction_pool:
        for out in transaction.outputs:
            if out['address'] == 'my-address':
                balance += data['amount']
        for _in in transaction.inputs:
            if _in in my_utxos.keys():
                balance -= my_utxos[_in]['amount']
    
    return balance

app.run('localhost', 8888)