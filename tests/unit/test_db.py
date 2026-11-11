import sqlite3

import pytest

from personaldocagent.db.connexion import connecter, init_db

TABLES = {
    "document",
    "document_agent",
    "document_sujet",
    "document_description",
    "categorie",
    "document_categorie",
    "emetteur",
    "conversion",
}


def _tables(conn) -> set:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


@pytest.fixture
def base(tmp_path):
    chemin = tmp_path / "test.db"
    init_db(chemin)
    return chemin


@pytest.fixture
def conn(base):
    c = connecter(base)
    yield c
    c.close()


def _inserer_document(conn, fichier="doc.pdf", texte="Facture EDF de mars, montant 87,40 EUR"):
    conn.execute(
        "INSERT INTO document (fichier_source, date_ajout) VALUES (?, '2026-11-01')",
        (fichier,),
    )
    doc_id = conn.execute(
        "SELECT doc_id FROM document WHERE fichier_source = ?", (fichier,)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO conversion (doc_id, texte_extrait, modele, date_conversion) "
        "VALUES (?, ?, 'mistral-ocr-latest', '2026-11-01')",
        (doc_id, texte),
    )
    conn.commit()
    return doc_id


def test_init_db_cree_les_huit_tables_plus_fts(conn):
    tables = _tables(conn)
    assert TABLES <= tables
    assert "conversion_fts" in tables


def test_init_db_cree_les_triggers_fts(conn):
    triggers = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
    assert {"conversion_fts_ai", "conversion_fts_ad", "conversion_fts_au"} <= triggers


def test_init_db_est_idempotent(tmp_path):
    chemin = tmp_path / "test.db"
    init_db(chemin)
    init_db(chemin)
    conn = connecter(chemin)
    try:
        assert TABLES <= _tables(conn)
    finally:
        conn.close()


def test_cle_etrangere_activee(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO document (fichier_source, date_ajout, emetteur_id) "
            "VALUES ('a.pdf', '2026-11-01', 999)"
        )


def test_statut_hors_liste_rejete(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO document (fichier_source, date_ajout, statut) "
            "VALUES ('a.pdf', '2026-11-01', 'archive')"
        )


def test_fichier_source_unique(conn):
    conn.execute("INSERT INTO document (fichier_source, date_ajout) VALUES ('a.pdf', '2026-11-01')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO document (fichier_source, date_ajout) VALUES ('a.pdf', '2026-11-02')")


def test_emetteur_libelle_unique(conn):
    conn.execute("INSERT INTO emetteur (libelle) VALUES ('EDF')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO emetteur (libelle) VALUES ('EDF')")


def test_emetteur_id_nullable(conn):
    conn.execute("INSERT INTO document (fichier_source, date_ajout) VALUES ('a.pdf', '2026-11-01')")
    row = conn.execute("SELECT emetteur_id FROM document WHERE fichier_source = 'a.pdf'").fetchone()
    assert row["emetteur_id"] is None


def test_fts5_recherche_plein_texte(conn):
    _inserer_document(conn, "a.pdf", "Facture EDF de mars, montant 87,40 EUR")
    _inserer_document(conn, "b.pdf", "Compte-rendu de syndic du 12 avril")
    rows = conn.execute("SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'facture'").fetchall()
    assert len(rows) == 1


def test_fts5_suit_update_et_delete(conn):
    doc_id = _inserer_document(conn, "a.pdf", "Facture EDF de mars")
    conn.execute("UPDATE conversion SET texte_extrait = 'Releve bancaire' WHERE doc_id = ?", (doc_id,))
    conn.commit()
    assert conn.execute("SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'facture'").fetchall() == []
    assert len(conn.execute("SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'releve'").fetchall()) == 1
    conn.execute("DELETE FROM conversion WHERE doc_id = ?", (doc_id,))
    conn.commit()
    assert conn.execute("SELECT rowid FROM conversion_fts WHERE conversion_fts MATCH 'releve'").fetchall() == []


def test_suppression_document_en_cascade_suit_dans_fts(conn):
    doc_id = _inserer_document(conn)
    conn.execute("DELETE FROM document WHERE doc_id = ?", (doc_id,))
    conn.commit()
    assert conn.execute("SELECT count(*) FROM conversion WHERE doc_id = ?", (doc_id,)).fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM conversion_fts WHERE conversion_fts MATCH 'facture'").fetchone()[0] == 0
