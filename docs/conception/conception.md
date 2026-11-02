# Synthèse de conception — Agent documentaire personnel

Document d'entrée pour le développement sous Vibe Code Web. Complète le modèle de données (schéma entité-relation, canvas dédié) et le modèle de traitement (chaîne de traitement). Chaque section mentionne les choix opérés et les remarques associées.

---

## 1. Objet du projet

Applicatif Python indexant les documents stockés sur l'espace privé d'un particulier ou d'un foyer : documents administratifs (factures, relevés, courriers, comptes-rendus de syndic), documents intellectuels (bibliographie universitaire), documents courants. Objectif : retrouver, décrire et organiser n'importe quel type de document. Usage personnel ou de ménage ; priorités : sobriété des installations, déterminisme du pipeline, traçabilité, exploitabilité SQL.

## 2. Fondements documentaires retenus

- Trois niveaux de l'analyse documentaire : classification, condensation, indexation. Tous trois sont conservés mais réinterprétés pour un fonds personnel.
- Description formelle : Dublin Core (ISO 15836) — vocabulaire de 15 éléments facultatifs et répétables ; implémentation libre, adaptée (éléments inutiles écartés, colonnes techniques ajoutées).
- Classement : plan de classement personnel en arbre (thème, sous-thème...), méthode libre — aucune norme ne s'impose ; règle unique : progression du général au particulier, profondeur libre (3 niveaux recommandés). L'arbre est une table, non un répertoire.
- Records management : les métadonnées de l'ISO 15489/23081 (statut, date d'ajout, durée de conservation) alimentent les colonnes techniques.
- Fiches sérielles : les documents récurrents d'un même émetteur (factures mensuelles, etc.) sont traités comme des publications en série — l'émetteur joue le rôle de la collection, le document celui du numéro. Recherches du type « facture EDF de mars » = émetteur + intervalle de dates.
- Rameau et la matrice de co-occurrence, retenus dans la version antérieure du projet (indexation généraliste), sont écartés : le besoin a été réorienté ; l'indexation par mots-clés libres (dc:subject) suffit au besoin décrit.

## 3. Modèle de données

SQLite, fichier unique, sans serveur. Tables :

1. `document` — description Dublin Core (titre, date, type, format, identifiant externe, langue, droits) + colonnes techniques (fichier_source, date_ajout, statut) + clé étrangère emetteur_id (nullable : certains documents n'ont pas d'émetteur identifié) + colonne reference (identifiant de rattachement du document : numéro de facture, période) + colonne attributs (JSON libre, convention de nommage imposée par le prompt ; y loger, si nécessaire, les montants et toute valeur d'intérêt non transversale).
2. `document_agent` — éléments répétables creator / contributor ; conservée pour les rôles autres que l'émission (destinataire, tiers mentionnés), l'émission étant portée par emetteur_id.
3. `document_sujet` — mots-clés libres (dc:subject), répétables.
4. `document_description` — résumés (condensation), répétables.
5. `categorie` — arbre de classement : categorie_id, parent_id (nul aux racines), libellé, profondeur, indicateur actif (fusion ou renommage sans perte d'historique). Une catégorie « Non classé » est prévue ; le reclassement en masse est une opération courante attendue. Forme physique : table unique (source de vérité), graine YAML d'initialisation (fichier d'amorçage des dix à quinze premiers niveaux, servant aussi d'outil d'amendement massif), et export aplati généré à la volée pour le contexte de l'agent (quelques centaines de catégories maximum ; au-delà, mécanisme de filtrage par branches plausibles).
6. `document_categorie` — classement d'un document dans l'arbre (un document, une ou plusieurs catégories, une principale).
7. `emetteur` — référentiel des émetteurs (rôle de collection sérielle et liste d'autorité) : emetteur_id, libellé, catégorie liée éventuelle. Version explicite choisie (jointures SQL lisibles) plutôt qu'une colonne texte libre.
8. `conversion` — texte extrait persisté (sortie OCR ou lecture directe) avec modèle et date, pour ne jamais re-payer une conversion.

## 3bis. Périmètre d'accès au système de fichiers

Politique d'inclusion contrôlée, entièrement déterministe — aucune décision d'accès n'est déléguée à l'agent, qui ne reçoit jamais de chemin mais uniquement du contenu déjà extrait.

1. Configuration externe (même rang que la table de routage et l'arbre) : liste de racines autorisées, liste d'exclusions (chemins ou motifs glob) et réglage suivre_liens_symboliques (faux par défaut).
2. Sémantique : tout ce qui n'est pas explicitement autorisé est interdit (deny by default) ; l'ordre d'évaluation est : exclusion explicite > autorisation explicite > reste interdit. Les exclusions permettent d'interdire un sous-dossier dans une racine autorisée (ex. un dossier archive dans un dossier de relevés) ; le parcours récursif s'y arrête.
3. Point d'insertion : évaluation à l'étape 0, avant toute lecture de contenu ; trois contrôles déterministes successifs — chemin autorisé, format accepté, duplicata — avant conversion. Les fichiers hors périmètre sont journalisés sans être lus.
4. Garde-fous : résolution canonique des chemins (realpath) avant évaluation ; applicatif en lecture seule sur le système de fichiers (le tri annuel produit une liste, jamais une suppression) ; journalisation des rejets d'accès pour détecter les erreurs de configuration.

Détail des colonnes techniques et d'intérêt de `document` : fichier_source (chemin d'accès au fichier original, lien entre fiche logique et fichier physique, donnée interne jamais exposée dans les prompts de l'agent) ; date_ajout (date d'intégration au fonds, distincte de dc_date qui est la date du document) ; statut (cycle de vie : actif, a_archiver, a_detruire — alimente le tri et les purges) ; reference (millésime du numéro dans le modèle sériel : numéro de facture, période d'un relevé) ; attributs (JSON libre à convention de nommage, héberge notamment les montants).

Remarques :
- La persistance du référentiel utilisé n'est plus nécessaire (plus de Rameau figé) ; le référentiel émetteurs se construit dynamiquement.
- L'évolution P2 (couche 3 : extraction typée par schéma JSON) se brancherait sans refonte : table spécialisée par type (ex. document_facture) liée à document, ou exploitation de la colonne attributs.

## 4. Chaîne de traitement

Étapes déterministes (Python) :

- Étape 0 — acquisition : évaluation du périmètre d'accès (cf. section 3bis), contrôle du format, table de routage (paramètre externe), découpage des documents longs ; deux voies : lecture directe (TXT, MD, HTML nettoyé, DOCX, ODT) et handoff OCR (PDF, JPG, PNG, TIFF, WebP).
- Étape 1 — description formelle : alimentation de `document`, détection des duplicatas.
- Rapprochement émetteur : recherche SQL exacte puis approximative dans `emetteur` ; issues : connu, proche ambigu (arbitrage agentique), inconnu (file d'attente puis création, après validation humaine ou automatique selon réglage de confiance).
- Écriture : description, classement, sujets, résumé, émetteur (clé étrangère résolue), attributs JSON ; avec date, source et score de confiance.
- Reprise ciblée : documents à faible confiance ou en attente (équivalent de l'ancienne réindexation).
- Contrôle qualité : cohérence du classement, statistiques.

Étapes agentiques (modèles Mistral) :

- OCR (mistral-ocr-latest) : conversion en Markdown par page avec scores de confiance ; persistance dans `conversion`.
- Étape 2 — analyse de contenu : catégorie dans l'arbre (choix contraint parmi les entrées existantes, fournies dans le contexte ; les catégories habituelles de l'émetteur reconnu peuvent y être ajoutées — transposition du mécanisme de cohérence), mots-clés, résumé, émetteur candidat, attributs d'intérêt.
- Arbitrage d'ambiguïté : catégories ou émetteurs proches.

Contrôle humain (optionnel, réglable) : validation de la fiche proposée ; validation des nouveaux émetteurs. Réglage intermédiaire recommandé pour la création d'émetteur : automatique si confiance élevée, validée sinon (évite la prolifération de quasi-doublons type « EDF » / « EDF SA »).

Paramétrage externe : politique d'analyse (nombre max de mots-clés, convention de nommage JSON), arbre de classification, table de routage, réglage de confiance.

Conséquences des choix sur l'enchaînement : le rapprochement porte désormais sur l'émetteur (boucle de contrôle d'autorité), l'étape 2 concentre les deux décisions contraignantes (catégorie, émetteur), et l'arbre doit exister avant le premier traitement tandis que le référentiel émetteurs se remplit dynamiquement.

## 5. Formats pris en charge

Retenus : PDF, JPG, PNG, TIFF, WebP (voie OCR) ; HTML, DOCX, ODT, TXT, Markdown (voie lecture directe).
Exclusions assumées : audio, vidéo, courriels, BMP, HEIC, SVG, GIF, EPUB (ajout possible).
La table de routage (extension ou type MIME vers voie) est un paramètre de configuration, facilitant les ajouts ultérieurs.

## 6. Choix techniques

- Conversion document-texte : tout PDF et toute image sont confiés à l'API OCR de Mistral (mistral-ocr-latest), sortie Markdown structurée avec scores de confiance ; pas de détection natif/scanné nécessaire. Supprime PyMuPDF (AGPL), pytesseract, Tesseract.
- Option B (repoussée) : extraction locale des PDF natifs (pypdf, BSD) pour optimiser les coûts si le corpus natif devient volumineux.
- Dépendances initiales : mistralai, BeautifulSoup, python-docx, odfpy ; SQLite natif.
- Agents « éphémères » au sens fonctionnel : complétions standard (chat.completions) avec function calling, prompts versionnés dans le code source ; pas d'agent persistant côté plateforme. Rationale : les outils sont déclarables directement dans l'appel ; le contexte persistant entre documents serait une contamination ; la persistance utile est celle de la tâche en cours (liste de messages maintenue par le code).
- Évolutivité : agent persistant et mode conversationnel (interrogation du fonds) restent des extensions possibles, indépendantes du pipeline.

## 7. Mode interrogation

Fonctionnalité de recherche et de question-réponse conversationnelle sur le fonds, distincte du pipeline par lots. L'agent d'interrogation ne sait rien : il orchestre des outils de lecture sur la base, puis rédige la réponse à partir des résultats.

Brique de données : index plein-texte SQLite FTS5 sur la table conversion (module intégré, sans dépendance ; structure inversée mot-documents, pertinence bm25, recherche quasi instantanée). Les références exactes (numéros, noms, dates) — dominantes dans les documents administratifs — y sont excellentes ; les reformulations ne le sont pas (recherche lexicale, non sémantique).

Outils exposés à l'agent (lecture seule stricte, jamais de chemins de fichiers) :

1. `rechercher_documents(filtres)` — recherche sur métadonnées (catégorie, émetteur, dates, type, statut, mots-clés).
2. `rechercher_plein_texte(expression)` — recherche FTS5 dans les textes extraits.
3. `lire_document(doc_id)` — texte extrait et description d'un document, avec troncation des textes très longs (extrait autour des occurrences).
4. `agreger(requete_restreinte)` — sommes et comptages sur champs whitelistés uniquement ; les montants passent par json_extract sur la colonne attributs, tributaire de la convention de nommage.

Architecture conversationnelle : chat.completions avec function calling (même mécanique que le pipeline) ; l'historique des messages, résultats d'outils compris, est maintenu dans une liste Python gérée par le code (persistable en JSON pour reprendre une session). Arbitrage documenté : la variante « agent éphémère côté serveur » (beta.agents, contexte conservé par le serveur) dispenserait de maintenir la liste mais imposerait un cycle de vie d'objet externe (création, identifiant, destruction non automatique — risque d'agents orphelins), la perte du contrôle du contexte (troncation, résumé des anciens tours) et de l'inspectabilité ; la liste locale est recommandée, l'alternative restant acceptable et migrable sans refonte.

Règles de conception : fin de session décidée par l'utilisateur ; ancrage obligatoire des réponses (chaîner doc_id et titre des documents sur lesquels la réponse se fonde — indispensable pour des données financières) ; journalisation des requêtes.

## 8. Priorisation

- P1 (périmètre du premier jet) : acquisition multi-format, description Dublin Core, classement arborescent, mots-clés et résumé, référentiel émetteurs avec version explicite, reprise ciblée, validations réglables, périmètre d'accès au système de fichiers, index FTS5 et mode interrogation à quatre outils.
- P2 (écarté pour l'instant, charge de maintenance récurrente : un schéma JSON par type de document) : extraction typée par catégorie (factures : numéros, montants, TVA ; syndic : résolutions ; bibliographie : références). Points d'ancrage déjà prévus : colonne attributs JSON, table emetteur. Mesure d'atténuation P1 : le résumé doit contenir en texte libre les valeurs essentielles (montant, dates, parties) pour approcher l'interrogation fine par recherche plein-texte.
- P2 (parallèle, non acté) : recherche sémantique par embeddings (encodage des documents par un modèle d'embedding — mistral-embed ; table de vecteurs doc_id/vecteur ; similarité cosinus calculée en Python, SQLite n'ayant pas de recherche vectorielle native — raisonnable jusqu'à quelques dizaines de milliers de documents). Coût : un appel d'encodage par fragment à l'indexation. Bénéfice : retrouver des sens par reformulation (« réfection du toit » trouve « travaux sur la toiture »). Perspective hybride : fusion des résultats FTS5 et sémantiques — les outils distincts de l'agent d'interrogation rendent cette fusion triviale. L'ordre des deux chantiers P2 (extraction typée ou embeddings) n'est pas arbitré.
- P3 (perspectives non spécifiées) : recherche hybride industrialisée, moteurs vectoriels dédiés si la volumétrie l'exigeait.

## 9. Points de vigilance transversaux

1. Données personnelles et financières sensibles : confidentialité des appels API et choix de l'hébergement plus critiques que dans la version généraliste.
2. Documents déjà structurés en entrée (factures Factur-X contenant un XML, relevés camt.053) : tenter l'extraction directe du XML embarqué avant tout appel au modèle — la table de routage de l'étape 0 est l'emplacement naturel de cette discrimination.
3. Convention de nommage des clés JSON : sans schéma, rien ne garantit l'homogénéité ; à imposer dans le prompt de l'agent.
4. Homogénéité de l'arbre : catégories « pas trop larges », ordre chronologique au sein d'une catégorie ; prévoir le reclassement massif.
5. Coûts API : OCR facturé à la page ; persistance systématique des conversions.
6. Démarrage à froid : référentiel émetteurs vide, arbre imparfait — les premières dizaines de documents servent d'étalonnage.

## 10. Prochaines étapes de conception

1. Esquisse de l'arbre de classification initial (catégories de premier niveau).
2. Rédaction des instructions de l'agent d'analyse (rôle, format de sortie JSON : catégorie, émetteur candidat, mots-clés, résumé, attributs ; contraintes de nommage).
3. Déclaration des outils exposés au modèle (recherche d'émetteurs, consultation des catégories).
4. Contrats d'interface entre modules Python (entrées/sorties de chaque étape).