PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS emetteur (
    emetteur_id INTEGER PRIMARY KEY,
    libelle TEXT NOT NULL UNIQUE,
    categorie_liee TEXT
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
    emetteur_id INTEGER REFERENCES emetteur(emetteur_id),
    fichier_source TEXT NOT NULL UNIQUE,
    date_ajout TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'actif' CHECK (statut IN ('actif', 'a_archiver', 'a_detruire')),
    reference TEXT,
    attributs TEXT
);

CREATE TABLE IF NOT EXISTS document_agent (
    doc_id INTEGER NOT NULL REFERENCES document(doc_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    valeur TEXT NOT NULL,
    PRIMARY KEY (doc_id, role, valeur)
);

CREATE TABLE IF NOT EXISTS document_sujet (
    doc_id INTEGER NOT NULL REFERENCES document(doc_id) ON DELETE CASCADE,
    valeur TEXT NOT NULL,
    PRIMARY KEY (doc_id, valeur)
);

CREATE TABLE IF NOT EXISTS document_description (
    doc_id INTEGER NOT NULL REFERENCES document(doc_id) ON DELETE CASCADE,
    valeur TEXT NOT NULL,
    PRIMARY KEY (doc_id, valeur)
);

CREATE TABLE IF NOT EXISTS categorie (
    categorie_id INTEGER PRIMARY KEY,
    parent_id INTEGER REFERENCES categorie(categorie_id),
    libelle TEXT NOT NULL,
    profondeur INTEGER NOT NULL,
    actif INTEGER NOT NULL DEFAULT 1 CHECK (actif IN (0, 1))
);

CREATE TABLE IF NOT EXISTS document_categorie (
    doc_id INTEGER NOT NULL REFERENCES document(doc_id) ON DELETE CASCADE,
    categorie_id INTEGER NOT NULL REFERENCES categorie(categorie_id),
    principal INTEGER NOT NULL DEFAULT 0 CHECK (principal IN (0, 1)),
    date_classement TEXT NOT NULL,
    PRIMARY KEY (doc_id, categorie_id)
);

CREATE TABLE IF NOT EXISTS conversion (
    doc_id INTEGER NOT NULL REFERENCES document(doc_id) ON DELETE CASCADE,
    texte_extrait TEXT NOT NULL,
    modele TEXT NOT NULL,
    date_conversion TEXT NOT NULL,
    PRIMARY KEY (doc_id, modele)
);

CREATE VIRTUAL TABLE IF NOT EXISTS conversion_fts USING fts5(
    texte_extrait,
    content='conversion',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS conversion_fts_ai AFTER INSERT ON conversion BEGIN
    INSERT INTO conversion_fts(rowid, texte_extrait) VALUES (new.rowid, new.texte_extrait);
END;

CREATE TRIGGER IF NOT EXISTS conversion_fts_ad AFTER DELETE ON conversion BEGIN
    INSERT INTO conversion_fts(conversion_fts, rowid, texte_extrait) VALUES ('delete', old.rowid, old.texte_extrait);
END;

CREATE TRIGGER IF NOT EXISTS conversion_fts_au AFTER UPDATE ON conversion BEGIN
    INSERT INTO conversion_fts(conversion_fts, rowid, texte_extrait) VALUES ('delete', old.rowid, old.texte_extrait);
    INSERT INTO conversion_fts(rowid, texte_extrait) VALUES (new.rowid, new.texte_extrait);
END;

CREATE INDEX IF NOT EXISTS idx_document_emetteur ON document(emetteur_id);
CREATE INDEX IF NOT EXISTS idx_document_statut ON document(statut);
CREATE INDEX IF NOT EXISTS idx_categorie_parent ON categorie(parent_id);
CREATE INDEX IF NOT EXISTS idx_document_categorie_categorie ON document_categorie(categorie_id);
