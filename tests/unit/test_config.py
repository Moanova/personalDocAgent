import pytest

from personaldocagent.config import charger_config


def test_charge_la_config_du_depot(repertoire_config):
    config = charger_config(repertoire_config)
    assert config.perimetre.suivre_liens_symboliques is False
    assert ".pdf" in config.routage.formats["ocr"]
    assert ".docx" in config.routage.formats["lecture_directe"]
    assert config.routage.voie_par_defaut == "rejeter"
    assert config.politique.nb_max_mots_cles > 0


def test_repertoire_sans_fichiers_leve_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        charger_config(tmp_path)


def test_champ_inconnu_est_rejete(tmp_path):
    (tmp_path / "perimetre_acces.yaml").write_text("champ_inconnu: 1\n", encoding="utf-8")
    (tmp_path / "routage.yaml").write_text("{}\n", encoding="utf-8")
    (tmp_path / "politique_analyse.yaml").write_text("{}\n", encoding="utf-8")
    with pytest.raises(TypeError):
        charger_config(tmp_path)
