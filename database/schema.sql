-- LinuxAI Database Schema
-- PostgreSQL + pgvector

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS distros (
    id                      BIGSERIAL PRIMARY KEY,
    name                    TEXT NOT NULL UNIQUE,
    family                  TEXT,
    package_manager         TEXT,
    install_command_template TEXT
);

CREATE TABLE IF NOT EXISTS devices (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    vendor      TEXT,
    device_type TEXT,
    pci_id      TEXT,
    usb_id      TEXT,
    notes       TEXT,
    CONSTRAINT devices_name_vendor_unique UNIQUE (name, vendor)
);

CREATE TABLE IF NOT EXISTS drivers (
    id            BIGSERIAL PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    kernel_module TEXT,
    driver_type   TEXT,
    notes         TEXT
);

CREATE TABLE IF NOT EXISTS packages (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    distro_id       BIGINT REFERENCES distros(id) ON DELETE CASCADE,
    purpose         TEXT,
    install_command TEXT,
    CONSTRAINT packages_name_distro_unique UNIQUE (name, distro_id)
);

CREATE TABLE IF NOT EXISTS commands (
    id               BIGSERIAL PRIMARY KEY,
    distro_id        BIGINT REFERENCES distros(id) ON DELETE SET NULL,
    title            TEXT NOT NULL,
    command          TEXT NOT NULL,
    risk_level       TEXT DEFAULT 'low'
                     CHECK (risk_level IN ('low', 'medium', 'high')),
    purpose          TEXT,
    rollback_command TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    id            BIGSERIAL PRIMARY KEY,
    title         TEXT NOT NULL,
    url           TEXT UNIQUE,
    source_type   TEXT,
    topic         TEXT,
    trust_level   TEXT DEFAULT 'medium'
                  CHECK (trust_level IN ('high', 'medium', 'low')),
    last_checked  TIMESTAMPTZ,
    content_hash  TEXT,
    notes         TEXT,
    CONSTRAINT sources_title_type_unique UNIQUE (title, source_type)
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id          BIGSERIAL PRIMARY KEY,
    source_id   BIGINT REFERENCES sources(id) ON DELETE CASCADE,
    title       TEXT,
    chunk_text  TEXT NOT NULL,
    chunk_hash  TEXT UNIQUE,
    topic       TEXT,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    embedding   vector(384)
);

CREATE TABLE IF NOT EXISTS device_driver_map (
    id         BIGSERIAL PRIMARY KEY,
    device_id  BIGINT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    driver_id  BIGINT NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    package_id BIGINT REFERENCES packages(id) ON DELETE SET NULL,
    confidence TEXT DEFAULT 'medium'
               CHECK (confidence IN ('high', 'medium', 'low')),
    source_id  BIGINT REFERENCES sources(id) ON DELETE SET NULL,
    notes      TEXT,
    CONSTRAINT device_driver_unique UNIQUE (device_id, driver_id)
);

CREATE TABLE IF NOT EXISTS system_reports (
    id             BIGSERIAL PRIMARY KEY,
    report_text    TEXT NOT NULL,
    distro_name    TEXT,
    kernel_version TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS training_examples (
    id                BIGSERIAL PRIMARY KEY,
    user_question     TEXT,
    sql_context       TEXT,
    vector_context    TEXT,
    final_answer      TEXT,
    quality_score     INTEGER CHECK (quality_score BETWEEN 1 AND 5),
    reviewed_by_human BOOLEAN DEFAULT FALSE,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_devices_name    ON devices(name);
CREATE INDEX IF NOT EXISTS idx_devices_vendor  ON devices(vendor);
CREATE INDEX IF NOT EXISTS idx_devices_pci_id  ON devices(pci_id);
CREATE INDEX IF NOT EXISTS idx_devices_usb_id  ON devices(usb_id);

CREATE INDEX IF NOT EXISTS idx_drivers_name    ON drivers(name);
CREATE INDEX IF NOT EXISTS idx_packages_name   ON packages(name);
CREATE INDEX IF NOT EXISTS idx_sources_topic   ON sources(topic);
CREATE INDEX IF NOT EXISTS idx_chunks_topic    ON document_chunks(topic);
CREATE INDEX IF NOT EXISTS idx_chunks_active   ON document_chunks(is_active);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops);
