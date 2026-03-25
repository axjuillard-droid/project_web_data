# PROJECT_SUMMARY.md — Contexte du projet pour assistant IA

> Ce fichier est conçu pour être lu par un assistant IA (Copilot, Cursor, Claude, ChatGPT…).  
> Il fournit le contexte complet du projet afin que l'IA soit correctement cadrée dans ses réponses et suggestions de code.  
> **Maintenir ce fichier à jour.** C'est la source de vérité pour tout assistant IA travaillant sur ce codebase.

---

## Identité du projet

| Champ | Valeur |
|-------|--------|
| **Nom** | Knowledge Graph & RAG Assistant |
| **Cours** | Web Mining & Machine Learning — ESILV (Paris) |
| **Niveau** | Ingénieur / Master (Bac+4/5) |
| **Évaluation** | 80% Projet + 20% Labs |
| **Rendu final** | Rapport (4–6 pages) + GitHub + Présentation orale |
| **Deadline** | Juin 2026 |
| **Équipe** | 1 ou 2 personnes |

---

## Domaine du projet — Verrouillé ✅

**Domaine choisi : `Sportifs & compétitions`**

**Entités principales** : athlètes, compétitions sportives (Jeux Olympiques, Coupe du Monde, Grand Chelem…), disciplines, équipes, pays représentés, palmarès, médailles.

**Couverture Wikidata** : excellente — des milliers d'athlètes et événements sportifs indexés avec palmarès, disciplines, nationalités et relations inter-entités.

**Exemples d'entités de départ** : Usain Bolt, Serena Williams, Lionel Messi, Simone Biles, JO Paris 2024, Coupe du Monde 2022, Tour de France…

**Impact sur le projet** :
- Classes ontologie : `Athlete`, `Competition`, `Sport`, `Team`, `Country`, `Medal`, `Award`
- Prédicats principaux : `participatedIn`, `wonMedal`, `represents`, `practicesSport`, `memberOfTeam`, `hostedBy`, `locatedIn`
- Règles SWRL : inférence de rivaux directs, compatriotes, multi-médaillés
- Templates RAG : questions sur palmarès, participations, rivalités, nationalités

---

## État d'avancement du projet

> Mettre à jour ce tableau à chaque phase complétée.

| Phase | Titre | État |
|-------|-------|------|
| 0 | Choix domaine & collecte web | 🟢 Terminé |
| 1 | Construction KB initiale (RDF) | 🟢 Terminé |
| 2 | Alignement entités Wikidata | 🟢 Terminé |
| 3 | Alignement prédicats SPARQL | 🟢 Terminé |
| 4 | Expansion KB | 🟢 Terminé |
| 5 | Raisonnement SWRL | 🟢 Terminé |
| 6 | Knowledge Graph Embedding | 🟢 Terminé |
| 7 | Assistant RAG (UI Streamlit & Ollama) | 🟢 Terminé |
| 8 | Rendu final | 🟡 En cours |

> **Légende** : 🔴 Non démarré · 🟡 En cours · 🟢 Terminé · ⬜ Bloqué

---

## Problème à résoudre

Les LLMs génèrent des réponses fluides mais peuvent halluciner des faits. L'objectif est de construire un système qui **ancre les réponses d'un LLM dans des faits vérifiables**, extraits d'un Knowledge Graph construit à partir de données web réelles.

**En une phrase** : transformer des données web brutes sur les sportifs et compétitions en un Knowledge Graph structuré (RDF/OWL), enrichi via Wikidata, pour alimenter un assistant RAG capable de répondre à des questions sur les palmarès, rivalités et parcours d'athlètes — avec traçabilité complète des faits sources.

---

## Architecture globale

```
[Données web brutes]
        │
        ▼ NLP (extraction d'entités nommées)
[Knowledge Base privée — RDF/Turtle]
        │
        ▼ Alignement SPARQL (owl:sameAs, owl:equivalentProperty)
[KB alignée avec Wikidata/DBpedia]
        │
        ▼ Expansion SPARQL (1-hop, 2-hop)
[KB étendue : 50k–200k triplets]
        │
   ┌────┴────┐
   ▼         ▼
[SWRL]    [KGE — PyKEEN]
Raisonnement  Embeddings vectoriels
symbolique    (TransE, DistMult, ComplEx, RotatE)
   │              │
   └────────┬─────┘
            ▼
      [Analyse & Rapport]
            │
            ▼
      [Assistant RAG]
   SPARQL → contexte → LLM → réponse citée
```

---

## Stack technique

### Langage principal

- **Python 3.10+**

### Bibliothèques

| Bibliothèque | Usage |
|-------------|-------|
| `rdflib` | Création, lecture, manipulation de graphes RDF |
| `owlready2` | Chargement d'ontologies OWL et raisonnement SWRL |
| `SPARQLWrapper` | Requêtes SPARQL sur Wikidata/DBpedia |
| `pykeen` | Entraînement de modèles KGE |
| `torch` | Backend PyTorch pour PyKEEN |
| `scikit-learn` | t-SNE, métriques |
| `matplotlib` | Visualisations |
| `pandas` | Tableaux de mapping |
| `requests` + `beautifulsoup4` | Scraping web |
| `spacy` | NLP, extraction d'entités nommées |
| `python-dotenv` | Gestion des variables d'environnement (clés API) |
| `openai` ou `anthropic` | API LLM pour le module RAG |

### Formats de fichiers

| Format | Usage |
|--------|-------|
| `.ttl` (Turtle) | Graphes RDF |
| `.owl` | Ontologies |
| `.txt` (tab-séparé) | Splits train/valid/test pour PyKEEN |
| `.csv` | Tableaux de mapping entités/prédicats |
| `.json` | Statistiques KB, résultats d'évaluation |
| `.env` | Clés API — ne jamais committer |
| `.ipynb` | Notebooks de démonstration |

---

## Structure du dépôt

> Les répertoires marqués `[à créer]` n'existent pas encore — structure cible.

projet/
├── README.md
├── ROADMAP.md                       # Feuille de route détaillée
├── PROJECT_SUMMARY.md               # Ce fichier
├── WHAT_WAS_BUILT.md                # Récapitulatif technique
├── requirements.txt
├── .env                             # Clés API locales (Gemini, etc.)
├── .gitignore                       # Ignore __pycache__, logs, .env
│
├── data/                            # Données brutes et splits KGE
│   ├── entités.csv
│   ├── kge/                         # train.txt, valid.txt, test.txt
│   └── textes_sources/
│
├── kg_artifacts/                    # Graphes RDF et statistiques générés
│   ├── knowledge_base_v1.ttl        
│   ├── knowledge_base_expanded.ttl  
│   ├── expanded.ttl                 
│   ├── ontology.ttl
│   ├── alignment.ttl
│   └── stats_kb.json
│
├── models/                          # Modèles entraînés et métriques
│   └── kge_results/
│       ├── comparaison_modeles.json
│       └── results/                 # Modèles PyKEEN (DistMult, TransE)
│
├── src/                             # Code source Python exclusif
│   ├── crawl/                       # Phase 0
│   ├── kg/                          # Phases 1-4 (KB et Alignements)
│   ├── reason/                      # Phase 5 (SWRL)
│   ├── kge/                         # Phase 6 (PyKEEN KGE)
│   └── rag/                         # Phase 7 (Assistant RAG & UI)
│       ├── app.py                   # Interface Web Streamlit 
│       └── llm_client.py            # Client API (Gemini + Ollama)
│
└── rapport/                         # Phase 8 — Rendu
    └── rapport_final.pdf
```

---

## Exemple de triplets — domaine Sportifs & compétitions

Ces triplets illustrent la structure attendue de la KB. À utiliser comme référence lors de la construction de l'ontologie et des scripts.

```turtle
@prefix : <http://monprojet.org/sports/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# -- Entités athlètes --
:UsainBolt rdf:type :Athlete .
:UsainBolt :practicesSport :Athletics .
:UsainBolt :participatedIn :OlympicsBeijing2008 .
:UsainBolt :participatedIn :OlympicsLondon2012 .
:UsainBolt :wonMedal :GoldMedal .
:UsainBolt :represents :Jamaica .

:SerenaWilliams rdf:type :Athlete .
:SerenaWilliams :practicesSport :Tennis .
:SerenaWilliams :participatedIn :Wimbledon2012 .
:SerenaWilliams :wonMedal :GoldMedal .
:SerenaWilliams :represents :UnitedStates .

# -- Entités compétitions --
:OlympicsBeijing2008 rdf:type :Competition .
:OlympicsBeijing2008 :year "2008"^^xsd:integer .
:OlympicsBeijing2008 :locatedIn :Beijing .
:OlympicsBeijing2008 :hostedBy :China .

# -- Alignements Wikidata --
:UsainBolt owl:sameAs wd:Q1190522 .
:OlympicsBeijing2008 owl:sameAs wd:Q8567 .

# -- Ontologie --
:Athlete rdfs:subClassOf :Person .
:participatedIn rdfs:domain :Athlete ; rdfs:range :Competition .
:wonMedal rdfs:domain :Athlete ; rdfs:range :Medal .
:represents rdfs:domain :Athlete ; rdfs:range :Country .
```

> Les documents pédagogiques utilisent des chercheurs scientifiques (Marie Curie…) comme exemple fil rouge — c'est uniquement pour les labs. Le domaine réel du projet est **Sportifs & compétitions**.

---

## Contraintes techniques — règles absolues

### KB

- Toutes les entités identifiées par des **URIs** (jamais de strings brutes)
- Prédicats nommés en **camelCase**
- Pas de triplets dupliqués
- Entités et littéraux clairement séparés
- **KB initiale** : ≥ 100 triplets, ≥ 50 entités
- **KB étendue** : 50k–200k triplets / 5k–30k entités / 50–200 relations

### KGE

- Entraîner **au minimum 2 modèles**
- **Configuration identique** entre les modèles (embedding dim, LR, batch size, epochs)
- Évaluer en **métriques filtrées uniquement**
- Exécuter `validate_splits.py` avant tout entraînement
- Utiliser `TriplesFactory.from_path()` avec des **chemins absolus** (pas de strings relatives)

### RAG

- Clés API dans `.env` — **ne jamais committer**
- L'assistant doit **citer les triplets sources** utilisés pour chaque réponse
- Gérer explicitement le cas **0 résultat SPARQL** (ne pas planter, ne pas halluciner)
- Répondre uniquement à partir des faits du KG — indiquer clairement si l'information est absente

### Rapport

- 4 à 6 pages
- Inclure : méthodologie, hyperparamètres KGE, tableau de résultats, analyse, conclusions
- Intégrer au rapport final du projet

---

## Glossaire — termes clés

| Terme | Définition |
|-------|-----------|
| **Knowledge Base (KB)** | Base de connaissances structurée en triplets (sujet, prédicat, objet) |
| **Knowledge Graph (KG)** | Représentation graphique d'une KB — nœuds = entités, arêtes = relations |
| **RDF** | Resource Description Framework — standard W3C pour les triplets |
| **OWL** | Web Ontology Language — classes, propriétés, axiomes |
| **SWRL** | Semantic Web Rule Language — règles Horn pour l'inférence logique |
| **SPARQL** | Langage de requête pour graphes RDF |
| **Wikidata** | KB ouverte Wikimedia, accessible via SPARQL endpoint |
| **DBpedia** | KB extraite de Wikipedia, accessible via SPARQL |
| **owl:sameAs** | Deux URIs désignent la même entité réelle |
| **owl:equivalentProperty** | Deux prédicats sont sémantiquement équivalents |
| **KGE** | Knowledge Graph Embedding — représentation vectorielle d'entités et relations |
| **TransE** | Modèle KGE translationnel : h + r ≈ t |
| **DistMult** | Modèle KGE bilinéaire symétrique |
| **ComplEx** | Modèle KGE bilinéaire dans l'espace complexe — gère l'asymétrie |
| **RotatE** | Modèle KGE rotationnel dans l'espace complexe |
| **PyKEEN** | Bibliothèque Python pour entraîner et évaluer des modèles KGE |
| **Link Prediction** | Prédire le triplet manquant (h, r, ?) ou (?, r, t) |
| **MRR** | Mean Reciprocal Rank — métrique de link prediction |
| **Hits@k** | Proportion de bonnes prédictions dans les k premiers résultats |
| **Métriques filtrées** | Métriques qui excluent les vrais triplets des candidats négatifs |
| **RAG** | Retrieval-Augmented Generation — recherche dans une KB + génération LLM |
| **OWLReady2** | Bibliothèque Python pour ontologies OWL et raisonneurs SWRL |
| **t-SNE** | Réduction de dimensionnalité pour visualiser des embeddings en 2D |
| **1-hop / 2-hop** | Expansion à 1 ou 2 niveaux de voisinage dans le graphe |
| **Negative sampling** | Génération de triplets faux pour l'entraînement KGE |
| **Entity Linking** | Résolution d'une mention textuelle vers une URI dans la KB |
| **TriplesFactory** | Objet PyKEEN encapsulant un dataset de triplets avec index entités/relations |

---

## Règles de comportement pour l'assistant IA

> Ces règles s'appliquent à tout assistant IA (Copilot, Cursor, Claude…) travaillant sur ce projet.

1. **Python uniquement** sauf indication contraire.
2. **RDFLib** pour toute manipulation de graphes RDF — ne pas proposer d'autres bibliothèques sans demande explicite.
3. **PyKEEN** pour les modèles KGE — ne pas implémenter from scratch en PyTorch sauf si demandé.
4. **Chemins absolus via `Path(__file__).parent`** pour tous les accès aux fichiers — jamais de chaînes relatives comme `'train.txt'`.
5. **Respecter la structure du dépôt** définie dans ce fichier.
6. **Respecter les contraintes de volume** de la KB.
7. **URIs pour toutes les entités RDF** — jamais de strings brutes comme identifiants.
8. **Ne pas générer de résultats KGE fictifs** — indiquer qu'ils dépendent des données réelles.
9. **Maintenir la cohérence des splits** — le script `validate_splits.py` doit passer sans erreur.
10. **Sécurité API** : toujours utiliser `python-dotenv` et `.env`, ne jamais hardcoder de clés.
11. **Commenter le code en français** sauf conventions techniques (noms de variables, fonctions, termes de bibliothèque).
12. **Ne pas proposer de fichiers qui n'existent pas encore** comme s'ils existaient — vérifier l'état d'avancement dans ce fichier.
13. **Toujours utiliser des entités du domaine sportifs** dans les exemples de code et de requêtes — ne jamais utiliser Marie Curie, Einstein ou d'autres chercheurs comme entités d'exemple (ce sont des références de lab, pas du projet).

---

## Points d'attention critiques

> Mentionnés explicitement dans les documents pédagogiques comme facteurs de réussite ou d'échec.

- ⚠️ **Le domaine doit être verrouillé en premier** — tout le reste en dépend.
- ⚠️ **La qualité de la KB est la fondation du projet.** Alignements incorrects → mauvais embeddings → mauvais RAG.
- ⚠️ **L'alignement des prédicats est l'étape la plus délicate.** Une mauvaise correspondance biaisera toute l'expansion.
- ⚠️ **TransE échoue sur les relations complexes** (N-to-N, antisymétriques). Adapter le choix de modèle au domaine.
- ⚠️ **DistMult ne modélise pas les relations antisymétriques.**
- ⚠️ **Les résultats t-SNE peuvent être contre-intuitifs** — l'absence de clustering clair est une observation valide à documenter.
- ⚠️ **Le module RAG doit citer ses sources** — c'est la valeur ajoutée principale par rapport à un LLM seul.
- ⚠️ **Les règles SWRL de la Phase 5 sont celles du domaine sportifs** — `hasCompeted`, `multiMedalist`, `sameNationality`. Les règles `family.owl` (oldPerson, hasBrother) sont des exercices de lab à ne pas intégrer au projet.
- ⚠️ **Exécuter `validate_splits.py` avant tout entraînement KGE** — une entité absente du train produit des métriques trompeuses.

---

*Dernière mise à jour : 25/03/2026 — Domaine verrouillé : Sportifs & compétitions*
