from sys import argv
from blockchain import Address, BlockChain
from crypto import private_to_pem_file, private_from_pem_file
from getpass import getpass

db_filename = 'bc1.db'
blockchain = BlockChain(db_filename)

if len(argv) > 2:
    print('Error. This script only accepts one argument (wallet file)')

class App:
    def load_wallet(self):
        self.wallet = None
        if len(argv) == 1:
            print('No wallet file provided. Creating new wallet.')

            self.wallet = Address()

            filename = input('Enter the name of your new wallet:') + '.wallet'
            password = getpass(prompt='Enter password for your new wallet:')
            
            private_to_pem_file(wallet.priv, filename, password)

        else:
            password = getpass(prompt='Enter your wallet password:')
            self.wallet = Address(priv_key=private_from_pem_file(argv[1], password))

    def display_balance(self):
        self.balance = 0
        for utxo in self.blockchain.get_utxos().values():
            if utxo['address'] == self.wallet.address:
                self.balance += utxo['amount']
        print(f'BALANCE: {self.balance/1000000}')

    def run(self):
        self.blockchain = BlockChain(db_filename)
        self.load_wallet()
        print(self.wallet.address)
        while True:
            self.display_balance()
            input()

app = App()
app.run()