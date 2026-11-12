# Projet personalDocAgent

Ce document suit l'avancement des tâches pour l'implémentation du projet **personalDocAgent**. Il est organisé en **5 colonnes** :
- **À faire** : Tâches non commencées.
- **En cours** : Tâches en cours d'implémentation.
- **En revue** : Tâches prêtes pour une revue ou des tests.
- **Terminé** : Tâches validées.
- **Annulé** : Tâches abandonnées (remplacées par une solution existante ou rendues inutiles).


---

# EPICs

## E1 — Initialisation du socle technique
Fondations communes à tout le pipeline (cf. `docs/conception/conception.md`, §3, §3bis et §10) : structure du dépôt, base SQLite, arbre de classification, paramétrage externe et contrats d'interface entre modules.

| Tâche | Titre | Dépendances |
|---|---|---|
| T1.1 | Structure du dépôt Python | — |
| T1.2 | Schéma SQLite et index FTS5 | T1.1 |
| T1.3 | Arbre de classification (graine YAML + chargement) | T1.1, T1.2 |
| T1.4 | Configuration externe (périmètre d'accès + table de routage) | T1.1 |
| T1.5 | Contrats d'interface entre modules | T1.2, T1.3, T1.4 |
| T1.6 | Alignement standards de codage | T1.1-T1.5 |


---

## E2 — Étape 0 : acquisition multi-format
Première brique du pipeline (cf. `docs/conception/conception.md` §4 et §5, `modèleTraitement.mmd`) : conversion des documents en texte par lecture directe ou handoff OCR, avant toute analyse. Les textes extraits sont persistés dans `conversion` pour ne jamais re-payer une conversion.

| Tâche | Titre | Dépendances |
|---|---|---|
| T2.1 | Voie lecture directe (TXT, MD, HTML nettoyé, DOCX, ODT) | T1.1, T1.4, T1.5 |
| T2.2 | Voie OCR (mistral-ocr-latest) + persistance dans `conversion` | T1.1, T1.2, T1.5 |
| T2.3 | Orchestration de l'étape 0 dans `pipeline.py` (3 contrôles + découpage des documents longs) | T1.4, T2.1, T2.2 |
| T2.4 | Commande CLI `pipeline` | T2.3 |


---

## E3 — Étape 1 : description formelle et persistance en base
À partir des `AcquisitionResult` de l'étape 0 (E2), écrire en base la fiche formelle minimale de chaque document, de façon déterministe et idempotente : ligne `document` (champs techniques : `source_file` canonique, `date_added`, `status`, `dc_format`) + texte extrait dans `conversion` (FTS5 alimenté par les triggers). Le contrôle duplicata (`is_duplicate` sur `source_file`) devient actif. Les champs issus de l'analyse agentique (titre, date, classement, résumé, émetteur) relèvent de l'EPIC E4.

| Tâche | Titre | Dépendances |
|---|---|---|
| T3.1 | Persistance étape 1 : `persist()` dans `pipeline.py` (`document` + `conversion`, idempotent) | T1.2, T1.5, T2.2, T2.3 |
| T3.2 | Branchement `run(config_dir, base) -> list[WriteResult]` + rapport CLI `pipeline` (acquis / écrits / rejetés) | T2.3, T2.4, T3.1 |
| T3.3 | Tests d'intégration de bout en bout (corpus tmp, 2e run idempotent, FTS) + validation E3 | T3.1, T3.2 |


---

## E4 — Étape 2 agentique : analyse de contenu
Pour chaque texte persisté dans `conversion`, produire via une complétion Mistral (`chat.completions`, prompts versionnés dans `prompts/`) une fiche d'analyse validée (contrat `AnalysisRecord`) : catégorie choisie **parmi les entrées existantes de l'arbre** (export aplati `classification.export_flat` fourni dans le contexte, cf. `conception.md` §4), émetteur candidat, mots-clés plafonnés par `analysis_policy.yaml`, résumé, attributs JSON en `snake_case`, score de confiance. Le rapprochement émetteur et l'écriture complète des tables filles relèvent des EPIC E5/E6.

| Tâche | Titre | Dépendances |
|---|---|---|
| T4.1 | Prompts versionnés + `analyze()` dans `analysis.py` (appel Mistral injectable, parsing JSON, validations) | T1.3, T1.5 |
| T4.2 | Contexte arbre (export aplati `id: label` + politique dans le prompt) et validation de `category_id` parmi les ids fournis | T1.3, T4.1 |
| T4.3 | Branchement `pipeline --analyze` (étapes 0-2, `analyze_base` sur les textes en base) + tests d'intégration | T3.2, T4.1, T4.2 |


---

## E5 — Rapprochement émetteur (boucle de contrôle d'autorité)
Rapprocher l'`issuer_candidate` produit par l'étape 2 (E4) au référentiel `issuer` (cf. `conception.md` §4, `modèleTraitement.mmd` E3A-E3C) : recherche SQL **exacte** (label normalisé) puis **approximative** (LIKE) ; issues `known` / `ambiguous` / `unknown` (contrat `IssuerMatch`). Création d'un nouvel émetteur uniquement après validation : automatique si la confiance ≥ `auto_confidence_threshold` (`analysis_policy.yaml`), sinon file d'attente (`issuer_id` NULL, validation humaine ultérieure). Un émetteur connu renseigne `document.issuer_id`.

| Tâche | Titre | Dépendances |
|---|---|---|
| T5.1 | `match_issuer()` dans `issuers.py` : normalisation + exact puis LIKE → `IssuerMatch` (known/ambiguous/unknown) | T1.2, T1.5 |
| T5.2 | Création idempotente + règle de confiance : `create_issuer`, `resolve_issuer` (auto si confiance ≥ seuil, sinon file d'attente) | T1.2, T4.1, T5.1 |
| T5.3 | Branchement pipeline : rapprochement après étape 2 + `UPDATE document.issuer_id` si connu + rapport CLI (connus/créés/en attente) + TI | T4.3, T5.1, T5.2 |


---

# Tableau du kanban

## À faire
T5.2
T5.3

## En cours
T5.1


## En revue
T3.1
T3.2
T3.3
T4.1
T4.2
T4.3


## Terminé
T1.1
T1.2
T1.3
T1.4
T1.5
T1.6
T2.1
T2.2
T2.3
T2.4


## Annulé


---

# Description des tâches

> Tâches triées par ordre numérique d'identifiant. L'état d'avancement de chaque tâche est indiqué dans le tableau ci-dessus.


## T1.1 — Structure du dépôt Python
- **Objectif** : poser l'arborescence, le packaging et les dépendances du projet.
- **Livrables** : `pyproject.toml` (dépendances `mistralai`, `beautifulsoup4`, `python-docx`, `odfpy` ; dev `pytest`), src layout `src/personaldocagent/`, `README.md`, `tests/` avec `conftest.py`, `unit/` et `integration/`, `config/` pour les YAML externes, `data/` (déjà gitignoré) pour la base SQLite et les journaux.
- **Arborescence cible** :
  ```
  src/personaldocagent/
  ├── __init__.py
  ├── __main__.py            # point d'entrée CLI
  ├── cli.py
  ├── config.py              # chargement/validation des YAML externes
  ├── perimeter.py           # évaluation des chemins (deny by default)
  ├── routing.py             # table de routage + contrôles format/duplicata
  ├── contracts.py           # dataclasses d'interface entre modules
  ├── db/
  │   ├── __init__.py
  │   ├── schema.sql         # 8 tables + index FTS5
  │   └── connection.py
  ├── classification.py      # graine YAML -> table categorie, export aplati
  ├── acquisition/
  │   ├── __init__.py
  │   ├── direct_read.py # TXT, MD, HTML, DOCX, ODT
  │   └── ocr.py             # handoff Mistral OCR, persistance dans conversion
  ├── pipeline.py            # orchestration des étapes 0-7
  ├── analysis.py             # étape 2 agentique (prompts + function calling)
  ├── issuers.py           # rapprochement exact puis approximatif
  ├── interrogation/
  │   ├── __init__.py
  │   ├── tools.py          # 4 outils en lecture seule
  │   └── agent.py           # chat.completions, historique maintenu localement
  └── prompts/               # prompts versionnés dans le code
  ```
- **Critères d'acceptation** : installation éditable OK, `python -m pytest` s'exécute, `python -m personaldocagent --help` répond.
- **Dépendances** : aucune.

## T1.2 — Schéma SQLite et index FTS5
- **Objectif** : créer le schéma de la base (fichier unique SQLite, sans serveur) à partir de `docs/conception/modèleDonnées.mmd`.
- **Livrables** : `db/schema.sql` (tables `document`, `document_agent`, `document_subject` (`document_sujet`), `document_description`, `category` (`categorie`), `document_category` (`document_categorie`), `issuer` (`emetteur`), `conversion`, clés étrangères et index), table virtuelle FTS5 sur `conversion(texte_extrait)` pour `search_fulltext`, `db/connection.py` (`init_db`, connexion contextuelle).
- **Critères d'acceptation** : création d'une base from scratch, intégrité référentielle, requête FTS5 fonctionnelle, tests unitaires au minimum.
- **Dépendances** : T1.1.

## T1.3 — Arbre de classification (graine YAML + chargement)
- **Objectif** : rendre l'arbre de classement opérationnel avant tout traitement (cf. `conception.md` §4 : « l'arbre doit exister avant le premier traitement »).
- **Livrables** : `config/classification.yaml` (transposition de `docs/conception/classificationInitiale.md`, catégorie « Non classé » incluse), `classification.py` (chargement YAML → table `category` (`categorie`) avec `parent_id`, `depth` (`profondeur`), `active` (`actif`) ; export aplati pour le contexte de l'agent).
- **Critères d'acceptation** : arbre chargé depuis le YAML, profondeurs correctes, export aplati généré, rechargement idempotent.
- **Dépendances** : T1.1, T1.2.

## T1.4 — Configuration externe (périmètre d'accès + table de routage)
- **Objectif** : externaliser le paramétrage exigé par `conception.md` §3bis (périmètre d'accès au système de fichiers) et §5 (table de routage).
- **Livrables** : `config/perimeter_access.yaml` (racines autorisées, exclusions glob, `suivre_liens_symboliques: false`) + `perimeter.py` (résolution canonique realpath, deny by default, ordre exclusion > autorisation, journalisation des rejets) ; `config/routing.yaml` (extension/MIME → voie `lecture_directe` ou `ocr`) + contrôles format et duplicata dans `routing.py`.
- **Critères d'acceptation** : un chemin hors périmètre est rejeté et journalisé sans être lu ; une extension inconnue est rejetée ; une exclusion prime sur une autorisation.
- **Dépendances** : T1.1.

## T1.5 — Contrats d'interface entre modules
- **Objectif** : définir les entrées/sorties de chaque étape du pipeline (point 4 des « prochaines étapes de conception », `conception.md` §10).
- **Livrables** : `contracts.py` (dataclasses + type hints, sans dépendance ajoutée) décrivant les objets échangés : résultat d'acquisition, fiche d'analyse (catégorie, émetteur candidat, mots-clés, résumé, attributs JSON), résultat d'écriture.
- **Critères d'acceptation** : chaque module du socle importe ses contrats depuis `contracts.py` ; tests de sérialisation des contrats.
- **Dépendances** : T1.2, T1.3, T1.4.

## T1.6 — Alignement standards de codage
- **Objectif** : appliquer les standards à toute l'arborescence : en-tête standardisé sur chaque script, docstrings et commentaires en anglais sur tous les scripts/classes/méthodes, identifiants (modules, classes, méthodes, variables) en anglais, `README.md` en français + `README.en.md`, docs projet en français, libellés de classification en français.
- **Livrables** : renommage des modules (`perimeter.py`, `routing.py`, `issuers.py`, `analysis.py`, `db/connection.py`, `acquisition/direct_read.py`, `interrogation/tools.py`), des fonctions/classes/contrats en anglais, des clés YAML de config en anglais (`allowed_roots`, `follow_symlinks`, `label`/`children` pour la classification), en-tête standard sur tous les scripts, `README.en.md`.
- **Choix acté** : le schéma SQL (tables/colonnes) est anglicisé (`issuer`, `category`, `source_file`, `status`…) ; les équivalents français sont conservés entre parenthèses dans `docs/conception/conception.md` et `docs/conception/modèleDonnées.mmd`.
- **Critères d'acceptation** : `python -m pytest` passe intégralement après renommage.
- **Dépendances** : T1.1-T1.5.

## T2.1 — Voie lecture directe
- **Objectif** : convertir en texte les formats lisibles sans appel API (cf. `conception.md` §5 : TXT, Markdown, HTML, DOCX, ODT).
- **Livrables** : `acquisition/direct_read.py` — `read_direct(path) -> AcquisitionResult` ; dispatch par extension ; TXT/MD lus en UTF-8 ; HTML nettoyé via BeautifulSoup (texte du document, scripts et styles exclus) ; DOCX via python-docx (paragraphes et tableaux) ; ODT via odfpy ; `model=None` (pas de modèle), `source_file` en chemin canonique, `conversion_date` en ISO 8601 UTC.
- **Critères d'acceptation** : les 5 extensions produisent un `AcquisitionResult` au contrat respecté ; aucun appel réseau ; tests unitaires autonomes (fixtures `tmp_path`).
- **Dépendances** : T1.1, T1.4, T1.5.

## T2.2 — Voie OCR et persistance
- **Objectif** : convertir PDF et images via `mistral-ocr-latest` (Markdown par page avec score de confiance) et persister le texte extrait dans `conversion` (cf. `conception.md` §6 et §9.5).
- **Livrables** : `acquisition/ocr.py` — `convert(path) -> AcquisitionResult` (`model="mistral-ocr-latest"`) ; helper d'insertion dans `conversion` (clé primaire `doc_id` + `model`, insertion idempotente) appelé lors de l'écriture de la fiche document.
- **Critères d'acceptation** : appel API mocké en test ; une conversion persistée est relue sans nouvel appel ; le retraitement d'un même document ne re-déclenche pas l'OCR.
- **Dépendances** : T1.1, T1.2, T1.5.

## T2.3 — Orchestration de l'étape 0
- **Objectif** : enchaîner les trois contrôles déterministes de T1.4 puis la bonne voie de conversion, avec découpage des documents longs (cf. `conception.md` §4).
- **Livrables** : `pipeline.py` — `run(config_dir, root)` itère `iter_allowed_files`, applique `run_step0_checks` (rejets journalisés sans lecture du fichier), dispatche vers `read_direct` ou `ocr.convert` selon la route, découpe les textes dépassant la taille de chunk fixée, retourne la liste des `AcquisitionResult`.
- **Critères d'acceptation** : fichier hors périmètre / format inconnu / duplicata sauté et journalisé sans être lu ; fichier accepté produit un résultat de la bonne voie ; texte long découpé en segments.
- **Dépendances** : T1.4, T2.1, T2.2.

## T2.4 — Commande CLI `pipeline`
- **Objectif** : rendre la sous-commande `pipeline` de `cli.py` fonctionnelle.
- **Livrables** : branchement de `cli.py` sur `pipeline.run` (`--config`, `--base`) avec rapport des résultats (acceptés / rejetés et raisons).
- **Critères d'acceptation** : `python -m personaldocagent pipeline --config config --base data/personaldocagent.db` s'exécute sur un petit corpus de test.
- **Dépendances** : T2.3.

## T3.1 — Persistance étape 1 (`persist`)
- **Objectif** : écrire en base, de façon déterministe et idempotente, la fiche formelle minimale d'un document acquis.
- **Livrables** : `pipeline.py` — `persist(conn, result: AcquisitionResult) -> WriteResult` : si `source_file` déjà présent → `WriteResult(written=False, reason="duplicate")` ; sinon insertion dans `document` (`source_file` canonique, `date_added` ISO 8601 UTC, `status='active'`, `dc_format` = MIME déduit de l'extension via `_MIME_BY_EXT`, repli `application/octet-stream`), puis `save_conversion(conn, doc_id, result)` avec `model = result.model or result.route` (colonne NOT NULL), retour `WriteResult(doc_id, written=True)` ; `IntegrityError` → `written=False, reason="duplicate"`.
- **Critères d'acceptation** : TU-21 à TU-24 (champs déterministes, idempotence, FTS alimenté, mapping MIME).
- **Dépendances** : T1.2, T1.5, T2.2, T2.3.

## T3.2 — Branchement `run` + rapport CLI
- **Objectif** : enchaîner étape 0 + persistance en respectant le contrat du squelette `run(...) -> list[WriteResult]` (testé dans `test_contracts.py`).
- **Livrables** : `pipeline.py` — `run(config_dir, base) -> list[WriteResult]` (charge la config, `init_db`, boucle sur les `allowed_roots` : `acquire` puis `persist` de chaque résultat) ; `cli.py` — branche `pipeline` sur `run`, rapport : acquis, écrits, doublons, rejets journalisés.
- **Critères d'acceptation** : TU-25 à TU-27 ; un 2e run rejette les doublons à l'étape 0 (`duplicate` journalisé, rien acquis, base inchangée).
- **Dépendances** : T2.3, T2.4, T3.1.

## T3.3 — Tests d'intégration bout en bout + validation E3
- **Objectif** : valider l'EPIC E3 de bout en bout sur un corpus temporaire.
- **Livrables** : `tests/integration/test_pipeline_persist.py` — TI-05 : corpus tmp (txt, html, `.xyz`, `.docx` corrompu) → 2 documents écrits, `conversion` + FTS5 interrogeables, rejets journalisés (`unsupported_format`, `conversion_failed`), 2e run idempotent (0 écrit).
- **Critères d'acceptation** : TI-05 passe, `python -m pytest` vert, E3 déplacée « En revue ».
- **Dépendances** : T3.1, T3.2.

## T4.1 — Prompts versionnés + `analyze()` (parsing/validation)
- **Objectif** : produire une fiche d'analyse validée à partir d'un texte extrait, via une complétion Mistral (cf. `conception.md` §6 : agents éphémères, prompts versionnés dans le code).
- **Livrables** : `prompts/` (prompt système + template utilisateur, versionnés, en anglais) ; `analysis.py` — `analyze(text, categories, policy, client=None) -> AnalysisRecord` : client Mistral paresseux (`MISTRAL_API_KEY`, injectable pour les tests), appel `chat.completions` avec réponse JSON exigée, parsing + validations déterministes : catégorie présente dans l'arbre, `len(keywords) <= policy.max_keywords` (`AnalysisRecord.validate`), clés d'`attributes` en `snake_case` (`policy.json_naming_convention`), `0 <= confidence <= 1` ; toute violation → `ValueError`.
- **Critères d'acceptation** : TU-28 à TU-33 (client mocké, zéro appel réseau).
- **Dépendances** : T1.3, T1.5.

## T4.2 — Contexte arbre + validation de `category_id`
- **Objectif** : contraindre le choix de catégorie aux entrées existantes de l'arbre (« choix contraint parmi les entrées existantes, fournies dans le contexte », `conception.md` §4). L'export aplati `export_flat` est au format `id: label` indenté : le modèle renvoie le `category_id`, validé contre les ids fournis.
- **Livrables** : construction du prompt avec `classification.export_flat(conn)` + politique (`max_keywords`, `json_naming_convention`) ; parsing des ids de l'export (`category_ids_from_export`) ; id inconnu → rejet `ValueError` ; vérification `active=1` en base.
- **Critères d'acceptation** : TU-30, TU-32 (le prompt transmis contient bien l'arbre aplati et la politique).
- **Dépendances** : T1.3, T4.1.

## T4.3 — Branchement `pipeline --analyze` + tests d'intégration
- **Objectif** : enchaîner l'analyse (étape 2) après la persistance (étapes 0-1), sur les textes déjà en base.
- **Livrables** : `pipeline.py` — `analyze_base(config_dir, base, client=None) -> list[AnalysisRecord]` (jointure `document`/`conversion`, texte découpé via `chunk_text` si long, `analyze` par document) ; `cli.py` — option `--analyze` sur la sous-commande `pipeline` (rapport : N analysés).
- **Critères d'acceptation** : TI-06 ; `pipeline --analyze` sur corpus tmp avec client fake.
- **Dépendances** : T3.2, T4.1, T4.2.

## T5.1 — `match_issuer()` (exact puis approximatif)
- **Objectif** : rapprocher un candidat émetteur au référentiel `issuer` (recherche SQL exacte puis LIKE, `conception.md` §4).
- **Livrables** : `issuers.py` — `match_issuer(conn, candidate) -> IssuerMatch` : normalisation (espaces/casse) ; hit exact → `known` ; LIKE : 1 hit → `known`, plusieurs → `ambiguous` (`proposed_label=candidate`), 0 → `unknown`.
- **Critères d'acceptation** : TU-34 à TU-37.
- **Dépendances** : T1.2, T1.5.

## T5.2 — Création d'émetteur et règle de confiance
- **Objectif** : créer un émetteur proprement, sans prolifération de quasi-doublons (« EDF » / « EDF SA »), selon le réglage de confiance (`conception.md` §4 : automatique si confiance élevée, validé sinon).
- **Livrables** : `issuers.py` — `create_issuer(conn, label, linked_category=None) -> int` (idempotent, `label UNIQUE`) ; `resolve_issuer(conn, match, candidate, confidence, policy) -> IssuerMatch` : `known` → inchangé ; `unknown` + confiance ≥ `policy.auto_confidence_threshold` → création automatique puis `known` ; sinon reste `unknown` (file d'attente : `issuer_id` NULL).
- **Critères d'acceptation** : TU-38 (seuil haut/bas, idempotence).
- **Dépendances** : T1.2, T4.1, T5.1.

## T5.3 — Branchement pipeline + rapport
- **Objectif** : enchaîner le rapprochement après l'étape 2 et renseigner `document.issuer_id` quand l'émetteur est connu.
- **Livrables** : `pipeline.py` — après `analyze_base`, pour chaque couple (doc_id, AnalysisRecord) : `match_issuer` + `resolve_issuer` (confiance du record, policy) + `UPDATE document SET issuer_id` si `known` ; `cli.py` — rapport « issuers: K known, C created, P pending » ; tests TI-07.
- **Critères d'acceptation** : TI-07 (émetteur connu renseigné, inconnu en attente avec `issuer_id` NULL).
- **Dépendances** : T4.3, T5.1, T5.2.
