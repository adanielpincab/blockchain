# SENDER
import socket
from uuid import uuid4
import struct
from json import dumps, loads

MCAST_GROUP = '224.1.1.1'
MCAST_PORT = 5004
ttl = 3 # 3-hop restriction in network
self_id = str(uuid4())

def send(bin_message: bytes):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    sock.sendto(bin_message, (MCAST_GROUP, MCAST_PORT))

def receive() -> bytes:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', MCAST_PORT))
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GROUP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        yield sock.recv(10240)

class Message:
    def __init__(self, code, data={}):
        self.code = code
        self.sender_id = self_id
        self.data = data

    def to_bin(self) -> bytes:
        return dumps(self.__dict__).encode('utf-8')
    
    @staticmethod
    def from_bin(bin: bytes):
        m = Message('')
        m.__dict__ = loads(bin.decode('utf-8'))
        return m

send(Message('hello').to_bin())
for m in receive(): # processing messages
    print(Message.from_bin(m))