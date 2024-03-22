CREATE TABLE IF NOT EXISTS TTransaction (
    addr_from TEXT,
    addr_to TEXT,
    amount INTEGER,
    fee INTEGER,
    timestamp INTEGER,
    pub_key TEXT,
    signature TEXT,
    hash TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS TInMerkle (
    proof_for_transaction TEXT,
    proof_order INTEGER,
    proof_hash TEXT,
    proof_side TEXT
);

CREATE TABLE IF NOT EXISTS TInBlock (
    transaction_hash TEXT PRIMARY KEY,
    block_hash TEXT
);

CREATE TABLE IF NOT EXISTS Block (
    transactions_root TEXT,
    timestamp INTEGER, 
    nonce INTEGER,
    miner TEXT,
    prevhash TEXT,
    hash TEXT PRIMARY KEY
);