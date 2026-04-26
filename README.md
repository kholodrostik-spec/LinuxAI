# LinuxAI

> RAG system for automatic Linux diagnostics and configuration — drivers, firmware, packages, laptop hardware.

---

## What it is

LinuxAI is a local knowledge base + vector search system for helping with Linux configuration. The system collects information about drivers, packages, and devices, stores it in PostgreSQL with pgvector, and allows searching by the meaning of a query, not only by exact words.

**Example:** query `"Ubuntu does not load the NVIDIA driver after installation"` → the system finds relevant instructions through vector similarity, even if the exact words from the query are not present in the text.

---

## Stack

| Component | Technology |
|---|---|
| Database | PostgreSQL 18+ |
| Vector search | pgvector |
| Language | Python 3.11+ |
| Embedding model | `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions) |
| ORM / driver | psycopg3 (`psycopg[binary]`) |

---

## Project structure

```text
linuxai/
├── app/
│   ├── config.py          # Configuration from .env
│   ├── db.py              # PostgreSQL connection
│   └── embedding.py       # Vector generation (sentence-transformers)
│
├── database/
│   └── schema.sql         # Database schema (tables + indexes)
│
├── scripts/
│   ├── init_db.py             # Create tables from schema.sql
│   ├── seed_base_data.py      # Fill distros, drivers, devices
│   ├── ingest_manual_notes.py # Load notes → embeddings → DB
│   ├── create_vector_index.py # Create ivfflat index (after ingest)
│   └── test_vector_search.py  # Test semantic search
│
├── data/
│   ├── manual_notes.json  # Manual notes about drivers and diagnostics
│   └── raw/               # Raw data for future ingest scripts
│
├── .env                   # Configuration (do not commit to git!)
├── requirements.txt
└── README.md
```

---

## Database schema

```text
distros ──────────────────── packages
   │                            │
   └── commands            device_driver_map
                           ╱         ╲
                      devices      drivers
                                      │
sources ──── document_chunks    (+ packages, sources)
             [chunk_text + embedding vector(384)]
```

The `sources` + `document_chunks` tables are the foundation for RAG. Each chunk has text and a 384-dimensional vector. SQL tables (`distros`, `devices`, `drivers`, `packages`, `commands`) store structured facts for exact search.

---

## Installation

### 1. PostgreSQL + pgvector

```bash
sudo systemctl start postgresql

# Install pgvector (replace 16 with your version)
sudo apt install postgresql-16-pgvector

# Create database
sudo -u postgres createdb linuxai

# Enable extension
sudo -u postgres psql -d linuxai -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Create user
sudo -u postgres psql <<EOF
CREATE USER linuxai_user WITH PASSWORD 'linuxai_password';
GRANT ALL PRIVILEGES ON DATABASE linuxai TO linuxai_user;
EOF

sudo -u postgres psql -d linuxai <<EOF
GRANT ALL ON SCHEMA public TO linuxai_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO linuxai_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO linuxai_user;
EOF
```

Check PostgreSQL version:

```bash
psql --version
```

### 2. Python environment

```bash
cd ~/linuxai
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. `.env` configuration

```env
DATABASE_URL=postgresql://linuxai_user:linuxai_password@localhost:5432/linuxai
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIM=384
```

> Do not commit the `.env` file to git. Add it to `.gitignore`.

---

## Running

Run in order:

```bash
cd ~/linuxai
source .venv/bin/activate

# 1. Create tables
python scripts/init_db.py

# 2. Basic reference data
python scripts/seed_base_data.py

# 3. Manual notes + embeddings
python scripts/ingest_manual_notes.py

# 4. Vector index (after filling with data)
python scripts/create_vector_index.py

# 5. Search test
python scripts/test_vector_search.py
```

All scripts are **safe to run repeatedly** — duplicates are ignored using `ON CONFLICT DO NOTHING`.

---

## Vector index

The `ivfflat` index is created **separately after** filling the database with data — it needs real vectors to train clusters. On an empty table, the index will technically be created, but it will be useless.

The `create_vector_index.py` script automatically calculates the `lists = sqrt(number of rows)` parameter.

For manual creation after filling the database:

```sql
CREATE INDEX idx_document_chunks_embedding
ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

---

## Embedding model

The `paraphrase-multilingual-MiniLM-L12-v2` model:

- Supports Ukrainian, Russian, English, and 50+ other languages
- Vector size: 384 dimensions
- Model size: ~120 MB
- Downloads automatically on first run through sentence-transformers

On the first run of `ingest_manual_notes.py`, the model will be downloaded to `~/.cache/huggingface/`.

---

## Command safety

In the schema, the `risk_level` field has three levels:

| Level | Examples |
|---|---|
| `low` | `lspci`, `lsusb`, `uname`, `lsmod`, `ip a`, `rfkill list` |
| `medium` | `apt install`, `dnf install`, `modprobe` |
| `high` | `rm`, `dd`, `mkfs`, `chmod -R`, `chown -R`, bootloader changes |

Commands with the `high` level must always have the `rollback_command` field filled in.

---

## Next steps

- [ ] Add `ingest_sources.py` — loading from URLs (Arch Wiki, Ubuntu Docs)
- [ ] Add `sql_search.py` — exact search through `devices`, `drivers`, `packages`
- [ ] Add `vector_search.py` — semantic search with filters by `topic`
- [ ] Connect the main LLM for generating answers based on the retrieved context
- [ ] Add `system_reports` — collecting data from `lspci`/`lsusb` for a specific machine

---

## License

MIT
