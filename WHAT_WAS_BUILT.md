# WHAT_WAS_BUILT.md — Récapitulatif de ce qui a été implémenté

> Ce fichier te permet de vérifier que tout le projet est bien en place.
> Coche chaque ligne après avoir vérifié l'existence et le bon fonctionnement du fichier.

---

## Fichiers racine

| ✅ | Fichier | Ce qu'il fait |
|----|---------|---------------|
| ✅ | `README.md` | Documentation générale, installation, commandes par phase |
| ✅ | `requirements.txt` | Dépendances Python (rdflib, pykeen, spacy, openai…) |
| ✅ | `.gitignore` | Protège `.env`, `__pycache__`, résultats lourds |
| ✅ | `.env` | Fichier pour stocker les clés API |
| ✅ | `check_install.py` | Vérifie que toutes les libs sont bien installées |

**Test rapide :** `python check_install.py`

---

## Phase 0 — Collecte de données (`src/crawl/`)

| ✅ | Fichier | Ce qu'il fait |
|----|---------|---------------|
| ✅ | `src/crawl/script_collecte.py` | Scraping Wikipedia + API Wikidata + NER spacy → `entités.csv` |

**Ce que le script produit après exécution :**
- `data/entités.csv` — liste de toutes les entités identifiées
- `data/textes_sources/*.txt` — textes Wikipedia téléchargés

**Test :** `python src/crawl/script_collecte.py`
*(Requiert une connexion internet — environ 2–5 minutes)*

---

## Phase 1 — Knowledge Base initiale (`src/kg/`)

| ✅ | Fichier | Ce qu'il fait |
|----|---------|---------------|
| ✅ | `src/kg/script_construction.py` | Construit la KB RDF avec l'ontologie + 13 athlètes + 30 compétitions |

**Ce que le script produit après exécution :**
- `kg_artifacts/knowledge_base_v1.ttl` — graphe RDF initial (≥ 100 triplets)
- `kg_artifacts/ontology.ttl` — définition des classes et propriétés
- `kg_artifacts/stats_kb.json` — statistiques (nb triplets, entités, relations)

**Ce qui est modélisé dans l'ontologie :**

| Classes | Propriétés d'objet |
|---------|--------------------|
| `Athlete`, `Competition`, `Sport` | `participatedIn`, `wonMedal`, `represents` |
| `Team`, `Country`, `Medal` | `practicesSport`, `memberOfTeam`, `hostedBy` |
| `Award`, `City`, `Person` | `locatedIn`, `hasCompeted`, `sameNationality` |

**Athlètes préconfigurés :** Usain Bolt, Serena Williams, Lionel Messi, Michael Phelps, Simone Biles, Roger Federer, Rafael Nadal, Novak Djokovic, Eliud Kipchoge, Cristiano Ronaldo, Kylian Mbappé, LeBron James, Mo Farah

**Test :** `python src/kg/script_construction.py`
*(Fonctionne sans internet — environ 5–10 secondes)*

---

## Phase 2 — Alignement des entités (`src/kg/`)

| ✅ | Fichier | Ce qu'il fait |
|----|---------|---------------|
| ✅ | `src/kg/script_alignement.py` | Lie chaque entité privée à son URI Wikidata via `owl:sameAs` |

**Ce que le script produit après exécution :**
- `kg_artifacts/mapping_entites.csv` — tableau entité → URI Wikidata + score de confiance
- `kg_artifacts/nouvelles_entites.ttl` — entités non trouvées sur Wikidata, définies sémantiquement
- `kg_artifacts/knowledge_base_v1.ttl` — mis à jour avec les triplets `owl:sameAs`

**Le mapping de départ (22 entités hardcodées) :**

| Entité privée | URI Wikidata | Score |
|--------------|-------------|-------|
| `:UsainBolt` | `wd:Q1190522` | 0.99 |
| `:LionelMessi` | `wd:Q615` | 0.99 |
| `:OlympicsParis2024` | `wd:Q193078` | 0.97 |
| `:FIFAWorldCup2022` | `wd:Q20771` | 0.99 |
| *… 18 autres* | | |

**Test :** `python src/kg/script_alignement.py`
*(Requiert internet — appels API Wikidata)*

---

## Phase 3 — Alignement des prédicats (`src/kg/`)

| ✅ | Fichier | Ce qu'il fait |
|----|---------|---------------|
| ✅ | `src/kg/script_alignement_sparql.py` | Aligne les prédicats privés avec les propriétés Wikidata |

**Ce que le script produit après exécution :**
- `kg_artifacts/mapping_predicats.csv` — tableau prédicat → Wikidata property + type d'alignement

**Les 5 alignements exacts :**

| Prédicat privé | Propriété Wikidata | Type |
|----------------|-------------------|------|
| `:wonMedal` | `wdt:P166` (award received) | `owl:equivalentProperty` |
| `:participatedIn` | `wdt:P1344` (participant in) | `owl:equivalentProperty` |
| `:represents` | `wdt:P27` (country of citizenship) | `owl:equivalentProperty` |
| `:practicesSport` | `wdt:P641` (sport) | `owl:equivalentProperty` |
| `:memberOfTeam` | `wdt:P54` (member of sports team) | `owl:equivalentProperty` |

**Test :** `python src/kg/script_alignement_sparql.py`

---

## Phase 4 — Expansion de la KB (`src/kg/`)

| ✅ | Fichier | Ce qu'il fait |
|----|---------|---------------|
| ✅ | `src/kg/script_expansion_sparql.py` | Enrichit la KB massivement via SPARQL Wikidata |

**Ce que le script produit après exécution :**
- `kg_artifacts/expanded.ttl` — KB étendue (cible : 50 000–200 000 triplets)
- `kg_artifacts/stats_kb.json` — statistiques finales

**Stratégies d'expansion implémentées :**
1. **1-hop** : tous les triplets directs de chaque entité alignée (LIMIT 500 par entité)
2. **2-hop** : triplets des entités voisines (LIMIT 20 voisins × 500 triplets)
3. **Par discipline** : tous les athlètes de chaque sport sur Wikidata (LIMIT 2000 par sport)

**Filtres appliqués :** exclusion des labels/descriptions, URIs malformées, littéraux > 500 caractères, triplets dupliqués

**Test :** `python src/kg/script_expansion_sparql.py`
*(Long : 30–90 minutes selon la connexion)*

---

## Phase 5 — Raisonnement SWRL (`src/reason/`)

| ✅ | Fichier | Ce qu'il fait |
|----|---------|---------------|
| ✅ | `src/reason/swrl_rules.py` | Applique les règles SWRL et enrichit la KB (`.ttl`) avec les faits déduits |

**Ce que le script produit après exécution :**
- `reports/resultats_swrl.txt` — faits inférés (paires, athlètes multi-médaillés)
- `reports/rapport_swrl.md` — documentation des règles et observations
- **Mise à jour de `kg_artifacts/expanded.ttl`** — 90+ triplets ajoutés (`hasCompeted`, `multiMedalist`, etc.)

**Les 3 règles implémentées :**

```
Règle 1 — hasCompeted (rivaux directs) :
  Athlete(?a1) ∧ participatedIn(?a1,?c) ∧ participatedIn(?a2,?c) ∧ differentFrom(?a1,?a2)
  → hasCompeted(?a1, ?a2)

Règle 2 — multiMedalist :
  Athlete(?a) ∧ wonMedal(?a,?m1) ∧ GoldMedal(?m1) ∧ wonMedal(?a,?m2) ∧ SilverMedal(?m2)
  → multiMedalist(?a)

Règle 3 — sameNationality (compatriotes) :
  Athlete(?a1) ∧ represents(?a1,?c) ∧ represents(?a2,?c) ∧ differentFrom(?a1,?a2)
  → sameNationality(?a1, ?a2)
```

> **Note :** Si Java n'est pas installé, le script bascule automatiquement en mode inférence manuelle Python (même logique, sans HermiT).

**Test :** `python src/reason/swrl_rules.py`

---

## Phase 6 — Knowledge Graph Embedding (`src/kge/`)

| ✅ | Fichier | Ce qu'il fait |
|----|---------|---------------|
| ✅ | `src/kge/prepare_splits.py` | Découpe la KB en train (80%) / valid (10%) / test (10%) |
| ✅ | `src/kge/validate_splits.py` | **⚠️ Obligatoire** — vérifie la qualité des splits avant entraînement |
| ✅ | `src/kge/train_kge.py` | Entraîne les modèles KGE avec PyKEEN |
| ✅ | `src/kge/analyse/nearest_neighbors.py` | Calcule les voisins sémantiques dans l'espace d'embedding |
| ✅ | `src/kge/analyse/tsne_visualization.py` | Génère le clustering t-SNE coloré par classe ontologique |

**Ce que les scripts produisent après exécution :**
- `train.txt`, `valid.txt`, `test.txt` — splits tab-séparés (dans le même dossier)
- `results/TransE/` — modèle entraîné + métriques
- `results/DistMult/` — modèle entraîné + métriques
- `comparaison_modeles.json` — tableau MRR/Hits@1/3/10 comparatif
- `analyse/nearest_neighbors.json` — voisins des athlètes clés
- `analyse/tsne_entities.png` — visualisation t-SNE dark-theme

**Configuration d'entraînement (identique entre les modèles) :**

| Paramètre | Valeur |
|-----------|--------|
| `embedding_dim` | 200 |
| `learning_rate` | 0.001 |
| `batch_size` | 512 |
| `num_epochs` | 100 |
| `negative_sampler` | basic |
| `random_seed` | 42 |

**Ce que prédit le modèle (Link Prediction) :**
- Donner `(UsainBolt, wonMedal, ?)` → prédit `GoldMedal`
- Donner `(?, represents, Jamaica)` → prédit `UsainBolt`

**Test dans l'ordre :**
```bash
python src/kge/prepare_splits.py
python src/kge/validate_splits.py      # doit afficher ✅ sur toutes les lignes
python src/kge/train_kge.py            # entraîne TransE + DistMult
python src/kge/analyse/nearest_neighbors.py
python src/kge/analyse/tsne_visualization.py
```

---

## Phase 7 — Assistant RAG (`src/rag/`)

| ✅ | Fichier | Ce qu'il fait |
|----|---------|---------------|
| ✅ | `src/rag/query_builder.py` | Convertit une question NL en requête SPARQL |
| ✅ | `src/rag/sparql_executor.py` | Exécute la requête sur la KB locale (rdflib) |
| ✅ | `src/rag/llm_client.py` | Appelle Gemini API / Ollama local |
| ✅ | `src/rag/rag_assistant.py` | Pipeline complet + CLI interactif |
| ✅ | `src/rag/app.py` | (NOUVEAU) UI Streamlit complet en mode sombre avec composante KGE + tableau de bord |

**Ce que le pipeline fait pour chaque question :**

```
Question : "Quelles médailles a remporté Usain Bolt ?"
     ↓ query_builder détecte : entité=UsainBolt, intention=médailles
     ↓ génère : SELECT ?medal WHERE { :UsainBolt :wonMedal ?medal }
     ↓ sparql_executor exécute sur la KB locale
     ↓ résultats : GoldMedal
     ↓ formate le contexte : "UsainBolt → wonMedal → GoldMedal"
     ↓ llm_client envoie au LLM (Gemini/Ollama) avec le contexte
     ↓ réponse : "Usain Bolt a remporté la médaille d'or..."
     ↓ triplets sources cités (traçabilité)
```

**Gestion des cas limites implémentée :**

| Situation | Comportement |
|-----------|-------------|
| 0 triplet trouvé | Fallback → requête générale `SELECT ?p ?o WHERE { :entité ?p ?o }` |
| Entité ambiguë | Dict de 50+ correspondances (fuzzy matching sur libellés) |
| Trop de triplets (> 50) | Tronqué automatiquement |
| Clé API absente | Mode simulation sans LLM (reformule directement le contexte) |

**Test :**
```bash
streamlit run src/rag/app.py                 # Interface Graphique
python src/rag/rag_assistant.py --test       # test automatique 8 questions
python src/rag/rag_assistant.py              # session interactive CLI
```

---

## Checklist de validation finale (Phase 8)

```
✅ KB étendue dans les volumes cibles (50k–200k triplets)
✅ validate_splits.py passe sans erreur (✅ sur toutes les lignes)
✅ ≥ 2 modèles KGE entraînés avec configuration identique
✅ Métriques MRR / Hits@1 / Hits@3 / Hits@10 en métriques FILTRÉES
✅ ≥ 1 règle SWRL adaptée au domaine sportifs (pas family.owl)
✅ Comparaison SWRL vs KGE documentée sur la règle hasCompeted
✅ t-SNE produit et commenté (tsne_entities.png)
✅ RAG fonctionnel avec gestion du cas 0 résultat
✅ Fichier .env hors dépôt (.gitignore vérifié)
✅ UI de pointe avec évaluation KGE (Ground Truth Train vs Test)
✅ Rapport final 4–6 pages (rapport/rapport_final.pdf)
✅ GitHub propre avec README lisible
✅ Présentation orale préparée
```

---

## Résumé des fichiers par dossier

```
projet/
├── README.md                          ← documentation générale
├── PROJECT_SUMMARY.md                 ← résumé contextuel
├── WHAT_WAS_BUILT.md                  ← ce fichier
├── requirements.txt                   ← dépendances
├── .gitignore                         ← protection API keys
├── .env                               ← clés API
├── check_install.py                   ← vérificateur d'installation
│
├── data/
│   ├── entités.csv                    ← Phase 0
│   └── kge/                           ← Phase 6 (Splits)
│
├── kg_artifacts/
│   ├── knowledge_base_v1.ttl          ← Phase 1
│   ├── knowledge_base_expanded.ttl    ← Phase 4
│   ├── expanded.ttl                   ← Phase 4 (App data)
│   ├── ontology.ttl                   
│   └── stats_kb.json                  
│
├── models/
│   └── kge_results/
│       ├── comparaison_modeles.json   ← Phase 6
│       └── results/                   ← Modèles KGE
│
├── src/
│   ├── crawl/                         ← Phase 0
│   ├── kg/                            ← Phases 1-4
│   ├── reason/                        ← Phase 5
│   ├── kge/                           ← Phase 6
│   └── rag/                           ← Phase 7
│       └── app.py                     ← Phase 7 (UI Principale)
│
└── rapport/
    └── rapport_final.pdf              ← Phase 8
```

**Total : 17 scripts/fichiers créés couvrant les 8 phases du projet.**

---

*Dernière mise à jour : 18/03/2026*
