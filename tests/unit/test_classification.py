import pytest

from personaldocagent.classification import charger_arbre, exporter_aplati
from personaldocagent.db.connexion import connecter, init_db

GRAINE_MINIMALE = """
- libelle: Finances
  enfants:
    - libelle: Banque
      enfants:
        - libelle: Relevés de compte
- libelle: Non classé
"""


@pytest.fixture
def conn(tmp_path):
    init_db(tmp_path / "test.db")
    c = connecter(tmp_path / "test.db")
    yield c
    c.close()


@pytest.fixture
def graine(tmp_path):
    g = tmp_path / "graine.yaml"
    g.write_text(GRAINE_MINIMALE, encoding="utf-8")
    return g


def test_charge_l_arbre_avec_profondeurs_et_parents(conn, graine):
    n = charger_arbre(conn, graine)
    assert n == 4
    rows = {r["libelle"]: r for r in conn.execute("SELECT * FROM categorie")}
    assert rows["Finances"]["profondeur"] == 1
    assert rows["Finances"]["parent_id"] is None
    assert rows["Banque"]["profondeur"] == 2
    assert rows["Banque"]["parent_id"] == rows["Finances"]["categorie_id"]
    assert rows["Relevés de compte"]["profondeur"] == 3
    assert rows["Banque"]["parent_id"] == rows["Finances"]["categorie_id"]
    assert rows["Non classé"]["profondeur"] == 1
    assert all(r["actif"] == 1 for r in rows.values())


def test_rechargement_est_idempotent(conn, graine):
    charger_arbre(conn, graine)
    n = charger_arbre(conn, graine)
    assert n == 4
    assert conn.execute("SELECT count(*) FROM categorie").fetchone()[0] == 4


def test_charge_la_graine_du_depot(conn, repertoire_config):
    n = charger_arbre(conn, repertoire_config / "classification.yaml")
    assert n >= 50
    row = conn.execute(
        "SELECT profondeur FROM categorie WHERE parent_id IS NULL AND libelle = 'Non classé'"
    ).fetchone()
    assert row is not None and row["profondeur"] == 1
    max_p = conn.execute("SELECT max(profondeur) FROM categorie").fetchone()[0]
    assert max_p == 3


def test_graine_invalide_leve_value_error(conn, tmp_path):
    g = tmp_path / "graine.yaml"
    g.write_text("juste_une_chaine\n", encoding="utf-8")
    with pytest.raises(ValueError):
        charger_arbre(conn, g)


def test_export_aplati_indente_et_filtre_inactifs(conn, graine):
    charger_arbre(conn, graine)
    conn.execute("UPDATE categorie SET actif = 0 WHERE libelle = 'Non classé'")
    conn.commit()
    export = exporter_aplati(conn)
    lignes = export.splitlines()
    assert any(l.endswith(": Finances") and not l.startswith(" ") for l in lignes)
    assert any(l.startswith("  ") and l.endswith(": Banque") for l in lignes)
    assert any(l.startswith("    ") and l.endswith(": Relevés de compte") for l in lignes)
    assert "Non classé" not in export
    for l in lignes:
        categorie_id = int(l.strip().split(":")[0])
        assert str(categorie_id) in l
