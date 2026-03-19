-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create Afternic domains table
CREATE TABLE IF NOT EXISTS afternic_domains (
    domain TEXT,
    price FLOAT,
    category TEXT,
    is_fast_transfer INT,
    domain_search TSVECTOR
);

-- Create ICANN domains table
CREATE TABLE IF NOT EXISTS icann_domains (
    domain TEXT,
    tld TEXT
);

-- Create indexes for afternic_domains
CREATE INDEX IF NOT EXISTS idx_afternic_domain ON afternic_domains(domain);
CREATE INDEX IF NOT EXISTS idx_afternic_lower ON afternic_domains(LOWER(domain));
CREATE INDEX IF NOT EXISTS idx_afternic_fts ON afternic_domains USING GIN(domain_search);
CREATE INDEX IF NOT EXISTS idx_afternic_trgm ON afternic_domains USING GIN(LOWER(domain) gin_trgm_ops);

-- Create indexes for icann_domains
CREATE INDEX IF NOT EXISTS idx_icann_domain ON icann_domains(domain);
CREATE INDEX IF NOT EXISTS idx_icann_name ON icann_domains(LOWER(SPLIT_PART(domain, '.', 1)));