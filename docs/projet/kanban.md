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

# Tableau du kanban

## À faire


## En cours


## En revue


## Terminé
T1.1
T1.2
T1.3
T1.4
T1.5
T1.6


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
