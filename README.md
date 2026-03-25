# Knowledge Graph & RAG Assistant — Sportifs & Compétitions

> Projet académique — Web Mining & Machine Learning — ESILV  
> Niveau Ingénieur / Master (Bac+4/5)  
> Évaluation : 80% Projet + 20% Labs | Deadline : Juin 2026

---

## Objectif

Transformer des données web brutes sur les **sportifs et compétitions** en un **Knowledge Graph structuré** (RDF/OWL), enrichi via Wikidata, pour alimenter un **assistant RAG** capable de répondre à des questions sur les palmarès, rivalités et parcours d'athlètes — avec traçabilité complète des faits sources.

---

## Architecture du système

```
[Données web brutes]
        │
        ▼ NLP (spacy — extraction d'entités nommées)
[Knowledge Base privée — RDF/Turtle]
        │
        ▼ Alignement SPARQL (owl:sameAs, owl:equivalentProperty)
[KB alignée avec Wikidata]
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
      [Assistant RAG]
   SPARQL → contexte → LLM → réponse citée
```

---

## Prérequis Matériels

- **Mémoire RAM** : 8 Go minimum (16 Go recommandés pour l'entraînement KGE rapide).
- **Processeur** : CPU multi-coeur basique (Le GPU est optionnel mais recommandé pour accélérer l'entraînement PyKEEN).
- **Stockage** : ~500 Mo d'espace disque disponible pour le Graphe expansé et les modèles.

---

## Installation

```bash
# 1. Cloner le dépôt
git clone <url-du-repo>
cd projet

# 2. Créer un environnement virtuel
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Télécharger le modèle spacy
python -m spacy download en_core_web_sm

# 5. Configurer les clés API (Gemini / Anthropic / OpenAI)
cp .env.example .env
# Éditer .env avec vos clés API (ex: GEMINI_API_KEY) pour utiliser le RAG via le cloud.

# 6. Installation Ollama (Optionnel, pour le RAG local)
# Téléchargez et installez Ollama (https://ollama.com/)
# Puis lancez le modèle de votre choix, par exemple :
# ollama pull llama3
```

---

## Structure du dépôt

```
projet/
├── README.md
├── ROADMAP.md                       # Feuille de route détaillée
├── PROJECT_SUMMARY.md               # Contexte pour IA
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
│       ├── app.py                   # Interface Web Streamlit Principale
│       └── llm_client.py            # Client API (Gemini + Ollama)
│
└── rapport/                         # Phase 8 — Rendu
    └── rapport_final.pdf
```

---

## Utilisation rapide

### Phase 0 — Collecte de données
```bash
python src/crawl/script_collecte.py
```

### Phase 1 — Construction de la KB
```bash
python src/kg/script_construction.py
```

### Phases 2 & 3 — Alignement
```bash
python src/kg/script_alignement.py
python src/kg/script_alignement_sparql.py
```

### Phase 4 — Expansion
```bash
python src/kg/script_expansion_sparql.py
```

### Phase 5 — Raisonnement SWRL
```bash
python src/reason/swrl_rules.py
```

### Phase 6 — KGE
```bash
python src/kge/prepare_splits.py        # Toujours valider avant d'entraîner
python src/kge/validate_splits.py
python src/kge/train_kge.py
python src/kge/analyse/nearest_neighbors.py
python src/kge/analyse/tsne_visualization.py
```

### Phase 7 — Assistant RAG & Interface Web (UI)
L'assistant interactif et modulaire est interrogeable via une **interface visuelle Streamlit de qualité professionnelle (Dark Mode)** proposant 3 onglets principaux :
- **Assistant RAG Sémantique** (avec choix entre API Cloud Gemini ou modèle local 100% privé **Ollama Llama3**)
- **Prédiction de Liens KGE** visuelle basée sur PyKEEN (incluant Ground-Truth via datasets natifs inédits)
- **Dashboard Dynamique** avec analyse des Embeddings de TransE/DistMult et des métadonnées du Graphe.

Lancez simplement le Web Serveur localement pour lancer l'interface :
```bash
streamlit run src/rag/app.py
```
*(Vous pouvez aussi utiliser l'ancien CLI de test en exécutant `python src/rag/rag_assistant.py --test`)*

---

## Domaine

**Sportifs & compétitions** — athlètes olympiques, champions du monde, Jeux Olympiques, Coupe du Monde FIFA, Tour de France et autres grandes compétitions sportives internationales.

---

*Dernière mise à jour : 25/03/2026*
