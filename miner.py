from sys import argv
from json import loads, dumps
from node import P2PNode

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
node.mine()