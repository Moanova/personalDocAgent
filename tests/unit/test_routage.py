from pathlib import Path

import pytest

from personaldocagent.config import Config, PerimetreAcces, PolitiqueAnalyse, Routage
from personaldocagent.db.connexion import connecter, init_db
from personaldocagent.routage import controles_etape0, est_duplicata, voie_de


def _config(racine: Path, exclusions=()) -> Config:
    return Config(
        perimetre=PerimetreAcces(racines_autorisees=[str(racine)], exclusions=list(exclusions)),
        routage=Routage(
            voie_par_defaut="rejeter",
            formats={"lecture_directe": [".txt", ".md"], "ocr": [".pdf"]},
        ),
        politique=PolitiqueAnalyse(),
    )


@pytest.fixture
def conn(tmp_path):
    init_db(tmp_path / "test.db")
    c = connecter(tmp_path / "test.db")
    yield c
    c.close()


@pytest.fixture
def racine(tmp_path):
    r = tmp_path / "fonds"
    r.mkdir()
    return r


def test_voie_par_extension_insensible_a_la_casse(racine):
    routage = _config(racine).routage
    assert voie_de(Path("a.pdf"), routage) == "ocr"
    assert voie_de(Path("B.PDF"), routage) == "ocr"
    assert voie_de(Path("notes.MD"), routage) == "lecture_directe"
    assert voie_de(Path("a.xyz"), routage) == "rejeter"


def test_est_duplicata_selon_fichier_source_canonique(conn, racine):
    cible = racine / "a.pdf"
    cible.write_text("x", encoding="utf-8")
    assert est_duplicata(cible, conn) is False
    conn.execute(
        "INSERT INTO document (fichier_source, date_ajout) VALUES (?, '2026-11-01')",
        (str(cible.resolve()),),
    )
    conn.commit()
    assert est_duplicata(cible, conn) is True


def test_controles_hors_perimetre(conn, racine, tmp_path):
    cible = tmp_path / "dehors.pdf"
    cible.write_text("x", encoding="utf-8")
    journal = tmp_path / "rejets.log"
    res = controles_etape0(cible, _config(racine), conn, journal)
    assert res.accepte is False and res.raison == "hors_perimetre"
    assert "hors_perimetre" in journal.read_text(encoding="utf-8")


def test_controles_format_non_supporte(conn, racine, tmp_path):
    cible = racine / "a.xyz"
    cible.write_text("x", encoding="utf-8")
    journal = tmp_path / "rejets.log"
    res = controles_etape0(cible, _config(racine), conn, journal)
    assert res.accepte is False and res.raison == "format_non_supporte"
    assert "format_non_supporte" in journal.read_text(encoding="utf-8")


def test_controles_duplicata(conn, racine, tmp_path):
    cible = racine / "a.pdf"
    cible.write_text("x", encoding="utf-8")
    conn.execute(
        "INSERT INTO document (fichier_source, date_ajout) VALUES (?, '2026-11-01')",
        (str(cible.resolve()),),
    )
    conn.commit()
    journal = tmp_path / "rejets.log"
    res = controles_etape0(cible, _config(racine), conn, journal)
    assert res.accepte is False and res.raison == "duplicata" and res.voie == "ocr"
    assert "duplicata" in journal.read_text(encoding="utf-8")


def test_controles_ok_voie_ocr_aucun_rejet(conn, racine, tmp_path):
    cible = racine / "a.pdf"
    cible.write_text("x", encoding="utf-8")
    journal = tmp_path / "rejets.log"
    res = controles_etape0(cible, _config(racine), conn, journal)
    assert res.accepte is True and res.voie == "ocr" and res.raison is None
    assert not journal.exists()
