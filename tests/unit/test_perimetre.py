from pathlib import Path

import pytest

from personaldocagent.config import PerimetreAcces
from personaldocagent.perimetre import est_autorise, journaliser_rejet, parcourir


@pytest.fixture
def arborescence(tmp_path):
    racine = tmp_path / "fonds"
    (racine / "releves" / "2026").mkdir(parents=True)
    (racine / "releves" / "2026" / "janv.pdf").write_text("x", encoding="utf-8")
    (racine / "releves" / "brouillon.txt").write_text("x", encoding="utf-8")
    (racine / "archive").mkdir()
    (racine / "archive" / "vieux.pdf").write_text("x", encoding="utf-8")
    (racine / "notes.md").write_text("x", encoding="utf-8")
    exterieur = tmp_path / "secret.pdf"
    exterieur.write_text("x", encoding="utf-8")
    (racine / "lien_interne.pdf").symlink_to(racine / "notes.md")
    (racine / "lien_externe.pdf").symlink_to(exterieur)
    return racine, exterieur


def perimetre(racine: Path, exclusions=(), suivre=False) -> PerimetreAcces:
    return PerimetreAcces(
        racines_autorisees=[str(racine)],
        exclusions=list(exclusions),
        suivre_liens_symboliques=suivre,
    )


def test_deny_by_default_racines_vides(arborescence):
    racine, fichier = arborescence
    p = PerimetreAcces()
    assert est_autorise(racine / "notes.md", p) is False
    assert est_autorise(fichier, p) is False


def test_fichier_dans_racine_autorise(arborescence):
    racine, _ = arborescence
    assert est_autorise(racine / "notes.md", perimetre(racine)) is True
    assert est_autorise(racine / "releves" / "2026" / "janv.pdf", perimetre(racine)) is True


def test_hors_racine_interdit(arborescence):
    racine, exterieur = arborescence
    assert est_autorise(exterieur, perimetre(racine)) is False


def test_exclusion_prioritaire_sur_autorisation(arborescence):
    racine, _ = arborescence
    p = perimetre(racine, exclusions=[f"{racine}/archive/**"])
    assert est_autorise(racine / "archive" / "vieux.pdf", p) is False
    assert est_autorise(racine / "notes.md", p) is True


def test_exclusion_glob_etoile_segment(arborescence):
    racine, _ = arborescence
    p = perimetre(racine, exclusions=[f"{racine}/*.md"])
    assert est_autorise(racine / "notes.md", p) is False
    assert est_autorise(racine / "releves" / "brouillon.txt", p) is True


def test_realpath_lien_interne_autorise_lien_externe_interdit(arborescence):
    racine, _ = arborescence
    p = perimetre(racine)
    assert est_autorise(racine / "lien_interne.pdf", p) is True
    assert est_autorise(racine / "lien_externe.pdf", p) is False


def test_parcourir_s_arrette_dans_repertoire_exclu(arborescence):
    racine, _ = arborescence
    p = perimetre(racine, exclusions=[f"{racine}/archive/**"])
    trouves = {f.name for f in parcourir(racine, p)}
    assert trouves == {"janv.pdf", "brouillon.txt", "notes.md", "lien_interne.pdf"}


def test_parcourir_racine_non_autorisee_ne_renvoie_rien(arborescence):
    racine, exterieur = arborescence
    assert list(parcourir(exterieur, perimetre(racine))) == []


def test_journaliser_rejet_ecrit_ligne_horodatee(arborescence, tmp_path):
    racine, exterieur = arborescence
    journal = tmp_path / "data" / "rejets.log"
    journaliser_rejet(exterieur, "hors_perimetre", journal)
    contenu = journal.read_text(encoding="utf-8")
    assert "hors_perimetre" in contenu
    assert str(exterieur.resolve()) in contenu
