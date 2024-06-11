SETUP = """CREATE TABLE IF NOT EXISTS TTransaction (
    timestamp INTEGER,
    pub_key TEXT,
    signature TEXT,
    hash TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS TInput (
    tx_hash TEXT,
    utxo_hash TEXT 
);

CREATE TABLE IF NOT EXISTS TOutput (
    hash TEXT PRIMARY KEY,
    tx_hash TEXT,
    address TEXT,
    amount INTEGER
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
    prevhash TEXT,
    hash TEXT PRIMARY KEY
);"""