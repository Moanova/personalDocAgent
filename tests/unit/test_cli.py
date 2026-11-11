import pytest

from personaldocagent.cli import main


def test_aide_globale_liste_les_commandes(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    sortie = capsys.readouterr().out
    for commande in ("init-db", "charger-arbre", "pipeline", "interroger"):
        assert commande in sortie


def test_commande_inconnue_est_rejetee():
    with pytest.raises(SystemExit) as exc:
        main(["commande-inexistante"])
    assert exc.value.code != 0


def test_commande_sans_implementation_leve_not_implemented():
    with pytest.raises(NotImplementedError):
        main(["pipeline"])


def test_init_db_cree_la_base(tmp_path):
    base = tmp_path / "sous" / "test.db"
    assert main(["--base", str(base), "init-db"]) == 0
    assert base.is_file()
