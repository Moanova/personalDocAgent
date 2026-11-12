-- -------------------------------------------------------------------
-- Application  : personalDocAgent
-- Script       : db/schema.sql
-- Version      : 0.1.0
-- Date         : 2026-11-11
-- Design       : TSC + Mistral Vibe
-- Build        : Mistral Vibe
-- -------------------------------------------------------------------
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS issuer (
    issuer_id INTEGER PRIMARY KEY,
    label TEXT NOT NULL UNIQUE,
    linked_category TEXT
);

CREATE TABLE IF NOT EXISTS document (
    doc_id INTEGER PRIMARY KEY,
    dc_title TEXT,
    dc_date TEXT,
    dc_type TEXT,
    dc_format TEXT,
    dc_identifier TEXT,
    dc_language TEXT,
    dc_rights TEXT,
    issuer_id INTEGER REFERENCES issuer(issuer_id),
    source_file TEXT NOT NULL UNIQUE,
    date_added TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'to_archive', 'to_destroy')),
    reference TEXT,
    attributes TEXT,
    confidence REAL
);

CREATE TABLE IF NOT EXISTS document_agent (
    doc_id INTEGER NOT NULL REFERENCES document(doc_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (doc_id, role, value)
);

CREATE TABLE IF NOT EXISTS document_subject (
    doc_id INTEGER NOT NULL REFERENCES document(doc_id) ON DELETE CASCADE,
    value TEXT NOT NULL,
    PRIMARY KEY (doc_id, value)
);

CREATE TABLE IF NOT EXISTS document_description (
    doc_id INTEGER NOT NULL REFERENCES document(doc_id) ON DELETE CASCADE,
    value TEXT NOT NULL,
    PRIMARY KEY (doc_id, value)
);

CREATE TABLE IF NOT EXISTS category (
    category_id INTEGER PRIMARY KEY,
    parent_id INTEGER REFERENCES category(category_id),
    label TEXT NOT NULL,
    depth INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS document_category (
    doc_id INTEGER NOT NULL REFERENCES document(doc_id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES category(category_id),
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    classification_date TEXT NOT NULL,
    PRIMARY KEY (doc_id, category_id)
);

CREATE TABLE IF NOT EXISTS conversion (
    doc_id INTEGER NOT NULL REFERENCES document(doc_id) ON DELETE CASCADE,
    extracted_text TEXT NOT NULL,
    model TEXT NOT NULL,
    conversion_date TEXT NOT NULL,
    PRIMARY KEY (doc_id, model)
);

CREATE VIRTUAL TABLE IF NOT EXISTS conversion_fts USING fts5(
    extracted_text,
    content='conversion',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS conversion_fts_ai AFTER INSERT ON conversion BEGIN
    INSERT INTO conversion_fts(rowid, extracted_text) VALUES (new.rowid, new.extracted_text);
END;

CREATE TRIGGER IF NOT EXISTS conversion_fts_ad AFTER DELETE ON conversion BEGIN
    INSERT INTO conversion_fts(conversion_fts, rowid, extracted_text) VALUES ('delete', old.rowid, old.extracted_text);
END;

CREATE TRIGGER IF NOT EXISTS conversion_fts_au AFTER UPDATE ON conversion BEGIN
    INSERT INTO conversion_fts(conversion_fts, rowid, extracted_text) VALUES ('delete', old.rowid, old.extracted_text);
    INSERT INTO conversion_fts(rowid, extracted_text) VALUES (new.rowid, new.extracted_text);
END;

CREATE INDEX IF NOT EXISTS idx_document_issuer ON document(issuer_id);
CREATE INDEX IF NOT EXISTS idx_document_status ON document(status);
CREATE INDEX IF NOT EXISTS idx_category_parent ON category(parent_id);
CREATE INDEX IF NOT EXISTS idx_document_category_category ON document_category(category_id);
