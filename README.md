# Afternic Marketplace Search API

A production-grade REST API for searching and enriching domain marketplace listings, built during a Software Engineering OJT at Eversun Software Philippines Corporation. It serves fast, paginated search over a combined dataset of **325M+ rows** — Afternic marketplace listings cross-referenced against the full ICANN domain registry — deployed on a Linux server.

## What it does

The API lets a client search Afternic's for-sale domain listings by keyword (with prefix/suffix/substring matching) and, for each result, enriches it with registration data pulled from the ICANN dataset — showing which other top-level domains (TLDs) the same domain name is already registered under.

**Example:** searching `tech` returns matching domains for sale, and for each one tells you whether `tech.com`, `tech.io`, `tech.ai`, etc. are already taken — useful signal for domain buyers evaluating a name's market value.

## Key Engineering Highlights

- **325M+ row dataset** — Afternic marketplace listings joined against the full ICANN registered-domains dataset at query time.
- **Trigram (`pg_trgm`) indexing** — GIN indexes using `gin_trgm_ops` enable fast `LIKE '%keyword%'` substring search across hundreds of millions of rows, which a plain B-tree index can't do efficiently.
- **Chunked bulk ingestion** — the ICANN dataset (distributed as a `.zst`-compressed CSV) is streamed and decompressed on the fly, then loaded via PostgreSQL's `COPY` protocol (`cursor.copy_from`) in 100,000-row batches, committing after each batch to keep memory usage flat while loading tens of millions of rows.
- **Single-query pagination with window functions** — result count and paginated rows are fetched in one query using `COUNT(*) OVER()`, avoiding a separate `COUNT(*)` query on a 325M-row table.
- **Batched enrichment lookups** — rather than looking up ICANN data per result, all domain names on the current page are enriched in a single `ANY(%s)` query using `SPLIT_PART` and `STRING_AGG`, minimizing round trips.
- **Linux deployment** — deployed and managed on a remote Linux server via SSH/PuTTY.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | PostgreSQL (`psycopg2`), `pg_trgm` extension |
| Data ingestion | `zstandard` (streaming decompression), PostgreSQL `COPY` |
| Config | `python-dotenv` |
| Deployment | Linux server (SSH/PuTTY) |

## Project Structure

```
Afternic-marketplace-search-API/
├── main.py               # Flask app entry point, registers blueprints
├── database.py            # PostgreSQL connection (env-based config)
├── schema.sql               # Table definitions, pg_trgm + GIN indexes
├── routes/
│   └── search.py               # /api/search/<keyword> endpoint — core search logic
├── data/
│   └── import.py                  # Streaming, chunked bulk loader for the ICANN dataset
└── requirements.txt                  # Python dependencies
```

## Database Schema

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE afternic_domains (
    domain TEXT,
    price FLOAT,
    category TEXT,
    is_fast_transfer INT,
    domain_search TSVECTOR
);

CREATE TABLE icann_domains (
    domain TEXT,
    tld TEXT
);
```

Indexes include a standard B-tree on `domain`, a full-text search GIN index on `domain_search`, and — critically — a trigram GIN index (`gin_trgm_ops`) on the lowercased domain, which is what makes substring search performant at scale.

## Getting Started

### Prerequisites

- Python 3.x
- PostgreSQL with the `pg_trgm` extension available
- Afternic listings data and an ICANN domain dataset (`.zst`-compressed CSV) to import

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/AndreNathanielBarbasa/Afternic-marketplace-search-API.git
   cd Afternic-marketplace-search-API
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=your_database_name
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   ```

4. Set up the schema:
   ```bash
   psql -U your_db_user -d your_database_name -f schema.sql
   ```

5. Import the ICANN dataset (edit the `.zst` file path in `data/import.py` first):
   ```bash
   python data/import.py
   ```

6. Run the API:
   ```bash
   python main.py
   ```

## API Reference

### `GET /api/search/<keyword>`

Search Afternic domain listings by keyword, enriched with ICANN registration data.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | int | `1` | Page number |
| `limit` | int | `100` | Results per page |
| `is_prefix` | int (0/1) | `0` | Match domains starting with the keyword |
| `is_suffix` | int (0/1) | `0` | Match domains ending with the keyword |

If neither `is_prefix` nor `is_suffix` is set, the search matches the keyword anywhere in the domain name.

**Example request:**
```
GET /api/search/tech?page=1&limit=50&is_prefix=1
```

**Example response:**
```json
{
  "status": "ok",
  "total_count": 1245,
  "current_page_count": 50,
  "current_page": 1,
  "last_page": 25,
  "per_page": 50,
  "domains": [
    {
      "root_domain": "techstack.com",
      "domain_name": "techstack",
      "domain_extension": "com",
      "price": 2999.0,
      "fast_transfer": 1,
      "domain_details": {
        "name_length": 9,
        "has_hyphen": false,
        "has_digit": false,
        "tld_availability": {
          "registered_gtlds": "com, io, net",
          "registered_gtld_count": 3
        }
      }
    }
  ]
}
```

## Author

**Andre Nathaniel Barbasa**
- Portfolio: [andrenathanielbarbasa.github.io/andre-portfolio](https://andrenathanielbarbasa.github.io/andre-portfolio/)
- GitHub: [@AndreNathanielBarbasa](https://github.com/AndreNathanielBarbasa)
- LinkedIn: [andrenathanielbarbasa](https://linkedin.com/in/andrenathanielbarbasa)
- Email: dreisbetter@gmail.com
