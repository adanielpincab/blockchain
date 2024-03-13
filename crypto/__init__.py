from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.exceptions import InvalidSignature
from pathlib import Path
from cryptography.hazmat.primitives import serialization

def generate_key_pair():
    key_size = 4096  # Should be at least 2048

    private_key = rsa.generate_private_key(
        public_exponent=65537,  # Do not change
        key_size=key_size,
    )

    public_key = private_key.public_key()
    return private_key, public_key

''' TODO: Si no hace falta se quita
def encrypt(message, public_key):
    return public_key.encrypt(
        message,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

def decrypt(message_encrypted, private_key):
    try:
        message_decrypted = private_key.decrypt(
            message_encrypted,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return message_decrypted
    except ValueError:
        raise ValueError
'''

def sign(message, private_key):
    return private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    ).hex()

def verify(hex_signature, message, public_key):
    try:
        public_key.verify(
            bytearray.fromhex(hex_signature),
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    except InvalidSignature:
        raise InvalidSignature

def private_to_pem(private_key, pem_file, password):
    password = password.encode()
    key_pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,  # PEM Format is specified
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password),
    )

    # Filename could be anything
    key_pem_path = Path(pem_file)
    key_pem_path.write_bytes(key_pem_bytes)

def private_from_pem(pem_file, password):
    password = password.encode()
    private_pem_bytes = Path(pem_file).read_bytes()

    try:
        return serialization.load_pem_private_key(
                    private_pem_bytes,
                    password=password,
                )
    except ValueError:
        raise ValueError

def public_serialized(public_key):
    public_pem_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return public_pem_bytes.decode()

def public_deserialized(serialized):
    return serialization.load_pem_public_key(serialized.encode())