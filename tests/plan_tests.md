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

| ID | Tâche | Description | Fichier de test |
|---|---|---|---|
| TU-21 | T3.1 | `persist` : ligne `document` déterministe (`source_file` canonique, `date_added` ISO 8601 UTC, `status='active'`, `dc_format`) + ligne `conversion` (`model = result.model or result.route`) + `WriteResult(written=True)` | `tests/unit/test_persist.py` |
| TU-22 | T3.1 | Idempotence : 2e `persist` sur le même `source_file` → `written=False, reason="duplicate"`, aucune ligne ajoutée | `tests/unit/test_persist.py` |
| TU-23 | T3.1 | FTS : après `persist`, le texte extrait est retrouvé dans `conversion_fts` | `tests/unit/test_persist.py` |
| TU-24 | T3.1 | Mapping MIME : `.pdf`→`application/pdf`, `.txt`→`text/plain`, extension inconnue→`application/octet-stream` | `tests/unit/test_persist.py` |
| TU-25 | T3.2 | `run(config_dir, base)` retourne des `WriteResult(written=True)` et écrit `document` + `conversion` | `tests/unit/test_run_persist.py` |
| TU-26 | T3.2 | 2e `run` : doublons rejetés à l'étape 0 (`duplicate` journalisé, rien acquis), base inchangée | `tests/unit/test_run_persist.py` |
| TU-27 | T3.2 | CLI `pipeline` : rapport acquis/écrits, rc 0, base remplie | `tests/unit/test_cli_pipeline.py` |
| TI-05 | T3.3 | Bout en bout : corpus tmp (txt, html, `.xyz`, `.docx` corrompu) → 2 écrits, FTS OK, rejets journalisés, 2e run idempotent (doublons rejetés à l'étape 0) | `tests/integration/test_pipeline_persist.py` |

| ID | Tâche | Description | Fichier de test |
|---|---|---|---|
| TU-28 | T4.1 | `analyze` avec client mocké, JSON valide → `AnalysisRecord` complet (catégorie résolue, champs remplis) | `tests/unit/test_analysis.py` |
| TU-29 | T4.1 | `keywords` > `policy.max_keywords` → `ValueError` (`AnalysisRecord.validate`) | `tests/unit/test_analysis.py` |
| TU-30 | T4.2 | catégorie absente de l'arbre → `ValueError` (choix contraint) | `tests/unit/test_analysis.py` |
| TU-31 | T4.1 | clé d'`attributes` non `snake_case` → `ValueError` | `tests/unit/test_analysis.py` |
| TU-32 | T4.2 | le prompt transmis contient l'export aplati de l'arbre + `max_keywords` + convention (appel mocké inspecté) | `tests/unit/test_analysis.py` |
| TU-33 | T4.1 | confiance hors [0,1] ou réponse JSON invalide → `ValueError` (avec aperçu du contenu brut) | `tests/unit/test_analysis.py` |
| TU-39 | T4.1 (fix) | `content` du modèle en liste de chunks (forme SDK 3.x : dicts ou TextChunk) normalisé avant `json.loads` | `tests/unit/test_analysis.py` |
| TI-06 | T4.3 | `pipeline --analyze` de bout en bout : corpus tmp + client fake → un `AnalysisRecord` par document persisté | `tests/integration/test_pipeline_analyze.py` |

| ID | Tâche | Description | Fichier de test |
|---|---|---|---|
| TU-34 | T5.1 | `match_issuer` : hit exact (label normalisé, casse/espaces) → `known` avec le bon `issuer_id` | `tests/unit/test_issuers.py` |
| TU-35 | T5.1 | LIKE approximatif à 1 hit → `known` ; TU-36 : plusieurs hits → `ambiguous` (`proposed_label`) ; TU-37 : 0 hit → `unknown` | `tests/unit/test_issuers.py` |
| TU-38 | T5.2 | `resolve_issuer` : confiance ≥ seuil → création auto (`known`) ; < seuil → `unknown` (file d'attente) ; `create_issuer` idempotent | `tests/unit/test_issuers.py` |
| TI-07 | T5.3 | Bout en bout : émetteur connu → `document.issuer_id` renseigné ; candidat inconnu + confiance faible → `issuer_id` NULL | `tests/integration/test_pipeline_issuers.py` |

| ID | Tâche | Description | Fichier de test |
|---|---|---|---|
| TU-42 | T6.1 | `write_record` : `attributes` JSON + `confidence` + `dc_title` (repli nom de fichier) + lignes filles subject/description/category (`is_primary=1`) | `tests/unit/test_write_record.py` |
| TU-43 | T6.1 | Idempotence : 2e `write_record` sur le même record → aucune ligne fille dupliquée | `tests/unit/test_write_record.py` |
| TU-44 | T6.1 | Migration : `init_db` ajoute la colonne `confidence` sur une base existante (PRAGMA) | `tests/unit/test_write_record.py` |
| TU-45 | T6.3 | `quality_report` / `pending_review` : totaux, par statut/catégorie, émetteurs en attente, confiance < seuil | `tests/unit/test_write_record.py` |
| TI-08 | T6.2/T6.3 | Bout en bout : `analyze_base(persist=True, with_issuers=True)` → fiches complètes en base, 2e run sans doublon, rapport CLI « Quality: » | `tests/integration/test_pipeline_write.py` |

| ID | Tâche | Description | Fichier de test |
|---|---|---|---|
| TU-46 | T7.1 | `search_documents` : filtres SearchFilters (catégorie, émetteur, dates, type, statut, mot-clé) | `tests/unit/test_query_tools.py` |
| TU-47 | T7.1 | `search_fulltext` : FTS5 MATCH sur `conversion_fts` → doc_id + extrait | `tests/unit/test_query_tools.py` |
| TU-48 | T7.1 | `read_document` : texte + description, troncature des textes longs (extrait autour des occurrences) | `tests/unit/test_query_tools.py` |
| TU-49 | T7.1 | `aggregate` : somme via `json_extract(attributes)`, champ non whitelisté → rejet | `tests/unit/test_query_tools.py` |
| TU-50 | T7.2 | `ask` avec client fake : tool_call → dispatch → réponse finale ancrée (doc_id + titre) | `tests/unit/test_query_agent.py` |
| TU-51 | T7.2 | Historique persisté/rechargé (JSON) + journal des requêtes | `tests/unit/test_query_agent.py` |
| TU-52 | T7.2 | tool inconnu / arguments invalides → erreur gérée, boucle interrompue proprement | `tests/unit/test_query_agent.py` |
| TI-09 | T7.3 | CLI `query --question` avec client fake sur base seedée → réponse ancrée ; REPL hors scope test | `tests/integration/test_query_cli.py` |
