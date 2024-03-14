import blockchain

a = blockchain.Address()

print(a.__dict__)

print(blockchain.Transaction('a', 'b', 10).__dict__)