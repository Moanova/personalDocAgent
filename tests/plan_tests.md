# Plan de tests — personalDocAgent

Conventions : **TU** = test unitaire (`tests/unit/`), **TI** = test d'intégration (`tests/integration/`), **TB** = test de bout en bout (à définir avec les EPIC suivantes). Chaque test est rattaché à une tâche du kanban (`docs/projet/kanban.md`) et couvre un critère d'acceptation.

Les tests de l'EPIC E1 (49 tests) ont été écrits avant ce plan et ne portent pas d'identifiant ; ils restent exécutés par `python -m pytest`.

---

## EPIC E2 — étape 0 acquisition

| ID | Tâche | Description | Fichier de test |
|---|---|---|---|
| TU-01 | T2.1 | TXT lu en UTF-8, accents conservés | `tests/unit/test_direct_read.py` |
| TU-02 | T2.1 | Markdown lu tel quel | `tests/unit/test_direct_read.py` |
| TU-03 | T2.1 | HTML nettoyé : texte du document, balises `script`/`style` exclues | `tests/unit/test_direct_read.py` |
| TU-04 | T2.1 | DOCX : paragraphes et tableaux extraits (document créé via python-docx) | `tests/unit/test_direct_read.py` |
| TU-05 | T2.1 | ODT : texte extrait via odfpy (document créé via odfpy) | `tests/unit/test_direct_read.py` |
| TU-06 | T2.1 | Contrat `AcquisitionResult` : `route="direct_read"`, `model=None`, `source_file` canonique, `conversion_date` ISO 8601 UTC | `tests/unit/test_direct_read.py` |
| TU-07 | T2.1 | Extension hors voie `direct_read` ou fichier corrompu : rejet explicite (`ValueError` avec le chemin en contexte) | `tests/unit/test_direct_read.py` |
| TU-08 | T2.1 | Dispatch de `read_direct` : chaque extension `direct_read` routée vers le bon lecteur | `tests/unit/test_direct_read.py` |
| TI-01 | T2.1 | Branchement étape 0 en lecture seule : `run_step0_checks` accepte un fichier `direct_read` dans le périmètre, `read_direct` produit le texte ; un `.xyz` est rejeté et journalisé sans être lu | `tests/integration/test_step0_direct_read.py` |

| ID | Tâche | Description | Fichier de test |
|---|---|---|---|
| TU-09 | T2.2 | `convert` avec client mocké : contrat complet (route `ocr`, model `mistral-ocr-latest`, texte = `markdown` des pages joint par `index`, `source_file` canonique, `conversion_date` ISO 8601 UTC) | `tests/unit/test_ocr.py` |
| TU-10 | T2.2 | `convert` upload le fichier local (`files.upload`, `purpose="ocr"`) puis appelle `ocr.process` avec le `file_id` et le modèle (appels vérifiés sur le mock) | `tests/unit/test_ocr.py` |
| TU-11 | T2.2 | Erreur de l'API OCR enveloppée en `ValueError` contextualisé (chemin + cause) | `tests/unit/test_ocr.py` |
| TU-12 | T2.2 | `save_conversion` idempotent (`INSERT OR IGNORE`, PK `doc_id`+`model`) + `load_conversion` (roundtrip) | `tests/unit/test_ocr.py` |
| TU-13 | T2.2 | Trigger FTS : après `save_conversion`, le texte est retrouvé dans `conversion_fts` | `tests/unit/test_ocr.py` |
| TU-14 | T2.2 | `MISTRAL_API_KEY` absent → `RuntimeError` explicite, aucun appel réseau | `tests/unit/test_ocr.py` |
| TI-02 | T2.2 | Flux persistance complet sur base `init_db` : ligne `document` + `save_conversion` + `load_conversion` + requête FTS5 dans `conversion_fts` | `tests/integration/test_ocr_conversion.py` |

| ID | Tâche | Description | Fichier de test |
|---|---|---|---|
| TU-15 | T2.3 | `chunk_text` : texte court → 1 segment ; découpage sur frontières de paragraphes en respectant `max_chars` ; paragraphe trop long découpé « en dur » | `tests/unit/test_pipeline.py` |
| TU-16 | T2.3 | `acquire` dispatch voie `direct_read` : un `.txt` dans le périmètre produit un `AcquisitionResult` (route, texte) | `tests/unit/test_pipeline.py` |
| TU-17 | T2.3 | `acquire` : rejets journalisés et parcours poursuivi (`.xyz` = `unsupported_format`, doublon = `duplicate` après insertion d'une ligne `document`) | `tests/unit/test_pipeline.py` |
| TU-18 | T2.3 | `acquire` : échec de conversion (`.docx` corrompu) journalisé `conversion_failed`, aucune exception propagée, les autres fichiers sont traités | `tests/unit/test_pipeline.py` |
| TU-19 | T2.3 | `acquire` dispatch voie `ocr` via `ocr_convert` injecté (fake) : un `.pdf` produit un résultat `route="ocr"`, aucun appel réseau | `tests/unit/test_pipeline.py` |
| TI-03 | T2.3 | `acquire` sur arborescence complète : txt + html acceptés, sous-dossier exclu non parcouru, `.xyz` rejeté et journalisé | `tests/integration/test_step0_pipeline.py` |

| ID | Tâche | Description | Fichier de test |
|---|---|---|---|
| TU-20 | T2.4 | `main(["--config", cfg, "--base", db, "pipeline"])` sur corpus tmp (`monkeypatch.chdir` pour isoler le journal) : rc 0, base créée, rapport affiché | `tests/unit/test_cli_pipeline.py` |
| TI-04 | T2.4 | CLI `pipeline` de bout en bout : `.txt` acquis, `.xyz` rejeté et journalisé dans le répertoire de travail tmp, aucun appel réseau | `tests/integration/test_cli_run.py` |
