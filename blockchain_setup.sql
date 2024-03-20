CREATE TABLE IF NOT EXISTS TTransaction (
    addr_from TEXT,
    addr_to TEXT,
    amount INTEGER,
    fee INTEGER,
    timestamp INTEGER,
    pub_key TEXT,
    signature TEXT
);

CREATE TABLE IF NOT EXISTS TInMerkle (
    proof_order INTEGER,
    proof_hash TEXT,
    proof TEXT,
    side TEXT
);

CREATE TABLE IF NOT EXISTS TInBlock (
    transaction_hash TEXT,
    block_hash TEXT
);

CREATE TABLE IF NOT EXISTS Block (
    transactions_root TEXT,
    timestamp INTEGER, 
    nonce INTEGER,
    miner TEXT,
    prevhash TEXT
);