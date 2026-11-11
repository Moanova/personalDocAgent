import inspect
import json
from dataclasses import asdict

import pytest

from personaldocagent import analyse, emetteurs, pipeline
from personaldocagent.acquisition import lecture_directe, ocr
from personaldocagent.contracts import (
    FicheAnalyse,
    FicheDocument,
    FiltresRecherche,
    ResultatAcquisition,
    ResultatEcriture,
    ResultatRapprochement,
)
from personaldocagent.interrogation import outils


def test_resultat_acquisition_serialisable_en_json():
    r = ResultatAcquisition(
        fichier_source="/fonds/a.pdf",
        voie="ocr",
        texte="# Facture",
        modele="mistral-ocr-latest",
        date_conversion="2026-11-11",
    )
    d = asdict(r)
    assert json.loads(json.dumps(d)) == d
    assert d["voie"] == "ocr"


def test_fiche_analyse_valider_limite_mots_cles():
    fiche = FicheAnalyse(
        categorie_id=15,
        emetteur_candidat="EDF",
        mots_cles=["mot"] * 11,
        resume="résumé",
        attributs={"montant_eur": 87.4},
        confiance=0.95,
    )
    with pytest.raises(ValueError):
        fiche.valider(nb_max_mots_cles=10)
    fiche.mots_cles = fiche.mots_cles[:10]
    fiche.valider(nb_max_mots_cles=10)


def test_fiche_analyse_attributs_json_roundtrip():
    fiche = FicheAnalyse(1, None, [], "r", {"montant_eur": 87.4}, 0.9)
    assert json.loads(json.dumps(asdict(fiche)["attributs"])) == {"montant_eur": 87.4}


def test_fiche_document_valeurs_par_defaut_et_json():
    f = FicheDocument(fichier_source="/x.pdf", date_ajout="2026-11-11")
    assert f.statut == "actif"
    assert f.attributs == "{}"
    assert f.agents == [] and f.sujets == [] and f.categories == []
    json.dumps(asdict(f))


def test_resultats_rapprochement_et_ecriture():
    r = ResultatRapprochement(statut="connu", emetteur_id=3)
    assert asdict(r)["statut"] == "connu"
    e = ResultatEcriture(doc_id=1, ecrit=True)
    assert e.raison is None


def test_filtres_recherche_tous_optionnels():
    f = FiltresRecherche(statut="actif", mot_cle="facture")
    assert f.categorie_id is None and f.emetteur_id is None
    json.dumps(asdict(f))


def test_signatures_des_stubs_referencent_les_contrats():
    assert "ResultatAcquisition" in str(inspect.signature(lecture_directe.lire).return_annotation)
    assert "ResultatAcquisition" in str(inspect.signature(ocr.convertir).return_annotation)
    assert "FicheAnalyse" in str(inspect.signature(analyse.analyser).return_annotation)
    assert "ResultatRapprochement" in str(inspect.signature(emetteurs.rapprocher).return_annotation)
    assert "ResultatEcriture" in str(inspect.signature(pipeline.executer).return_annotation)
    param = inspect.signature(outils.rechercher_documents).parameters["filtres"]
    assert "FiltresRecherche" in str(param.annotation)
