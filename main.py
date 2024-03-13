import crypto

priv, pub = crypto.generate_key_pair()

print(priv)
print(pub)