CREATE TABLE IF NOT EXISTS Transaction(
    addr_from TEXT,
    addr_to TEXT,
    amount NUMBER,
    fee NUMBER,
    timestamp NUMBER,
    pub_key TEXT,
    signature TEXT
)

CREATE TABLE IF NOT EXISTS TMerkleProof (
    transaction_hash TEXT,
    order NUMBER,
    side TEXT
)

CREATE TABLE IF NOT EXISTS TInBlock (
    transaction_hash TEXT,
    block_hash TEXT
)

CREATE TABLE IF NOT EXISTS Block(
    transactions_root TEXT,
    timestamp NUMBER, 
    nonce NUMBER,
    miner TEXT,
    prevhash TEXT
)