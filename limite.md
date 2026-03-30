Rapport sur les Limites et Difficultés du Projet
Ce document synthétise les obstacles rencontrés lors du développement et les limitations actuelles du système.

1. Collecte et Qualité des Données (Phases 0 & 1)
Protection anti-bots : L'extraction multi-sources (Transfermarkt, Olympedia) a été limitée par des mécanismes de blocage. Le projet s'est donc recentré sur Wikipedia et l'API Wikidata.
Noyau initial réduit : La base de départ ne comptait que 13 athlètes et 30 compétitions, créant une forte dépendance à l'étape d'expansion pour obtenir de la diversité.
2. Expansion de la Knowledge Base (Phase 4)
Arbitrage Temps/Profondeur : L'expansion "2-hop" (voisins des voisins) s'est avérée extrêmement chronophage. Elle a été limitée à 15 entités (au lieu de 120+) pour stabiliser les temps de traitement.
Bruit Sémantique : L'expansion par discipline (88% du graphe, soit ~110k triplets) a été favorisée pour atteindre les volumes cibles. Cependant, sans script de filtrage qualitatif (hormis les doublons), de nombreux prédicats Wikidata peu pertinents ont été importés.
Statistiques Finales : 125 105 triplets pour seulement 3 182 entités, indiquant un graphe très dense autour de quelques pivots, mais potentiellement "bruyant" en relations.
3. Raisonnement Symbolique SWRL (Phase 5)
Sparsité des Faits (Sparsity) : Certaines règles n'infèrent pas les résultats attendus. Exemple : Usain Bolt n'est pas détecté comme "multiMedalist" car ses médailles ne sont pas liées par les prédicats exacts attendus par la règle dans la version extraite.
Approximations Logiques : La règle 
hasCompeted
 lie tout athlète ayant participé à une même compétition. Or, pour des événements globaux comme les JO de Pékin 2008, cela crée des liens entre sportifs de disciplines totalement différentes (Ex: Judo vs Athlétisme).
Échelle : Seulement 96 nouveaux triplets ont été ajoutés par SWRL, un impact faible par rapport aux 125k triplets de la KB.
4. Knowledge Graph Embedding (Phase 6)
Contraintes Matérielles : L'entraînement local étant trop lent, il a été déporté sur Google Colab pour bénéficier d'accélérateurs.
Performance des Modèles :
DistMult (MRR ~0.32) : Meilleures performances, mieux adapté aux relations complexes/symétriques de Wikidata.
TransE (MRR ~0.11) : Résultats décevants, confirmant sa difficulté sur les graphes hautement connectés et les relations N-to-N.
5. Assistant RAG & Entity Linking (Phase 7)
Fragilité du Mapping : La conversion Question → SPARQL repose sur du fuzzy matching et des templates. Le système peine sur des questions à intentions multiples ou des noms d'athlètes ambigus.
*   Dépendance au LLM : En cas d'échec de la requête SPARQL (0 résultat), le fallback vers une requête générique augmente le risque d'hallucination si le contexte est trop large.
*   **Approche "Pure Graph-RAG"** : Le système n'exploite que les triplets structurés. Les fichiers textes sources (Wikipedia), pourtant riches en anecdotes et détails narratifs (ex: blessures, rivalités historiques), n'ont été utilisés que pour l'extraction NER initiale et non comme source de contexte direct pour le LLM, limitant la profondeur des réponses.

---

## 6. Perspectives et Améliorations Futures

Pour dépasser ces limites, plusieurs pistes de développement sont envisageables :

*   **Implémentation d'un RAG Hybride** : Combiner le Knowledge Graph (pour les faits précis) avec une base de données vectorielle indexant les textes bruts de `data/textes_sources` pour enrichir les réponses avec du contexte narratif.
*   **Hybridation SWRL & RAG** : Utiliser les règles logiques pour pré-filtrer ou enrichir le contexte envoyé au LLM, améliorant ainsi la précision des réponses sur les relations complexes.
*   **Enrichissement des règles SWRL** : Ajouter des règles plus fines (ex: détection automatique de la discipline si non spécifiée, règles de hiérarchie entre compétitions) pour augmenter le nombre de faits déduits.
*   **Expansion qualitative** : Viser l'objectif de **5 000 entités uniques** en affinant les filtres d'expansion SPARQL pour ne garder que les prédicats sportifs essentiels et réduire le bruit.
*   **Filtrage sémantique des triplets** : Développer un script de nettoyage basé sur une ontologie de référence pour supprimer les triplets Wikidata sans valeur ajoutée pour les embeddings.
*   **Amélioration de l'Entity Linking** : Remplacer le fuzzy matching par un modèle de NER plus robuste ou une API de réconciliation (OpenRefine/Wikidata API) pour mieux gérer les homonymes.
*   **Scaling KGE** : Tester des modèles plus complexes (RotatE, ComplEx) sur des infrastructures plus puissantes pour mieux modéliser l'asymétrie des relations sportives (ex: "est l'entraîneur de").
*   **Contournement des protections anti-bots** : Utiliser des outils plus avancés (Selenium, Playwright ou Proxies) pour enfin intégrer les données de **Transfermarkt** ou **Olympedia**, augmentant la diversité des sources.