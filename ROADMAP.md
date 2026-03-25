# ROADMAP.md — Feuille de route du projet

> **Projet** : Knowledge Graph & RAG Assistant  
> **Cours** : Web Mining & Machine Learning — ESILV  
> **Équipe** : max 2 personnes | **Deadline rendu final : juin 2026**  
> **Évaluation** : 80% Projet / 20% Labs — Rapport + GitHub + Présentation orale

---

## Domaine du projet — Verrouillé ✅

**Domaine retenu : `Sportifs & compétitions`**

Entités principales : athlètes, compétitions sportives, disciplines, équipes, palmarès, nations.  
Couverture Wikidata : excellente — des milliers d'athlètes et événements indexés avec palmarès complets.  
Exemples d'entités de départ : athlètes olympiques, champions du monde, Jeux Olympiques, Coupe du Monde FIFA, Tour de France…

---

## Planning & état d'avancement

| Phase | Titre | Deadline cible | État |
|-------|-------|---------------|------|
| 0 | Choix domaine & collecte web | Semaine 1 | 🟡 En cours |
| 1 | Construction KB initiale (RDF) | Semaine 2 | 🔴 Non démarré |
| 2 | Alignement entités (Wikidata) | Semaine 3 | 🔴 Non démarré |
| 3 | Alignement prédicats (SPARQL) | Semaine 3 | 🔴 Non démarré |
| 4 | Expansion KB via SPARQL | Semaine 4 | 🔴 Non démarré |
| 5 | Raisonnement SWRL | Semaine 5 | 🟡 En cours |
| 6 | Knowledge Graph Embedding | Semaines 5–7 | 🟡 En cours |
| 7 | Assistant RAG | Semaines 7–9 | 🟢 Terminé |
| 8 | Rendu final | Juin 2026 | 🔴 Non démarré |

> **Légende** : 🔴 Non démarré · 🟡 En cours · 🟢 Terminé · ⬜ Bloqué par phase précédente  
> *Mettre à jour ce tableau à chaque fin de phase.*

---

## Phase 0 — Choix du domaine & collecte web

**Deadline** : Semaine 1 | **État** : 🟡 En cours

### Tâches

- [x] Verrouiller le domaine : **Sportifs & compétitions** ✅
- [ ] Vérifier la couverture Wikidata : lancer une requête SPARQL test et estimer le nombre d'entités disponibles
- [ ] Scraper des pages HTML — extraire texte brut (Wikipedia sport, Transfermarkt, Olympedia…)
- [ ] Identifier les entités nommées via NLP (spacy recommandé)
- [ ] Collecter via API complémentaire (Wikipedia API, DBpedia Lookup, Wikidata API…)

### Critère de validation

```
≥ 50 entités identifiées avec : nom + type + au moins 1 relation chacune
```

### Livrable

```
data/
├── entités.csv              # colonnes : id, nom, type, source_url
├── textes_sources/
└── script_collecte.py
```

---

## Phase 1 — Construction de la KB initiale (RDF)

**Source** : KB_Lab_Session_KB_Construction_and_Expansion.pdf — Step 1  
**Deadline** : Semaine 2 | **État** : 🔴 Non démarré

### Volume cible

| Métrique | Minimum |
|----------|---------|
| Triplets | ≥ 100 |
| Entités | ≥ 50 |

### Tâches

- [ ] Définir les classes de l'ontologie : `Athlete`, `Competition`, `Sport`, `Team`, `Country`, `Medal`, `Award`
- [ ] Définir les propriétés avec rdfs:domain et rdfs:range
- [ ] Modéliser les données en triplets RDF — URIs uniquement, nommage camelCase
- [ ] Exporter en Turtle (.ttl) via RDFLib
- [ ] Vérifier : pas d'URI malformée, pas de doublon, entités séparées des littéraux

### Exemple — domaine Sportifs & compétitions

```turtle
:UsainBolt rdf:type :Athlete .
:UsainBolt :practicesSport :Athletics .
:UsainBolt :participatedIn :OlympicsBeijing2008 .
:UsainBolt :wonMedal :GoldMedal .
:UsainBolt :represents :Jamaica .

:OlympicsBeijing2008 rdf:type :Competition .
:OlympicsBeijing2008 :year "2008"^^xsd:integer .
:OlympicsBeijing2008 :locatedIn :Beijing .

:participatedIn rdfs:domain :Athlete ;
               rdfs:range :Competition .
:wonMedal rdfs:domain :Athlete ;
         rdfs:range :Medal .
```

### Livrable

```
kb/
├── knowledge_base_v1.ttl
├── ontologie.owl
└── script_construction.py
```

---

## Phase 2 — Alignement des entités avec Wikidata

**Source** : Step 2 | **Deadline** : Semaine 3 | **État** : 🔴 Non démarré

### Tâches

- [ ] Pour chaque entité : chercher son URI Wikidata (API wbsearchentities)
- [ ] Si trouvée : ajouter owl:sameAs + enregistrer le score de confiance
- [ ] Si non trouvée : définir sémantiquement (classe + propriétés RDFS)
- [ ] Produire le tableau de mapping

### Format du tableau de mapping

| Entité privée | URI Wikidata | Confiance | Statut |
|--------------|-------------|-----------|--------|
| `:UsainBolt` | `wd:Q1190522` | 0.99 | ✅ alignée |
| `:OlympicsBeijing2008` | `wd:Q8567` | 0.97 | ✅ alignée |
| `:CompetitionInconnue` | — | — | 🆕 nouvelle entité |

### Livrable

```
alignement/
├── mapping_entites.csv
├── nouvelles_entites.ttl
└── script_alignement.py
```

---

## Phase 3 — Alignement des prédicats via SPARQL

**Source** : Step 3 | **Deadline** : Semaine 3 | **État** : 🔴 Non démarré

### Tâches

- [ ] Pour chaque prédicat privé : interroger Wikidata pour trouver une propriété équivalente
- [ ] Classer chaque alignement : owl:equivalentProperty (exact) ou rdfs:subPropertyOf (hiérarchique)
- [ ] Documenter les prédicats sans équivalent trouvé

### Requête SPARQL de référence (exemple sur `:wonMedal`)

```sparql
SELECT ?property ?propertyLabel WHERE {
  ?property a wikibase:Property .
  ?property rdfs:label ?propertyLabel .
  FILTER(CONTAINS(LCASE(?propertyLabel), "medal"))
  FILTER(LANG(?propertyLabel) = "en")
}
LIMIT 50
-- Candidat attendu : wdt:P166 "award received" ou propriété médaille spécifique
```

### Prédicats du domaine sportifs à aligner (non exhaustif)

| Prédicat privé | Candidat Wikidata | Type |
|---------------|------------------|------|
| `:wonMedal` | `wdt:P166` (award received) | owl:equivalentProperty |
| `:participatedIn` | `wdt:P1344` (participant in) | owl:equivalentProperty |
| `:represents` | `wdt:P27` (country of citizenship) | owl:equivalentProperty |
| `:practicesSport` | `wdt:P641` (sport) | owl:equivalentProperty |
| `:memberOfTeam` | `wdt:P54` (member of sports team) | owl:equivalentProperty |

### Livrable

```
alignement/
├── mapping_predicats.csv
└── script_alignement_sparql.py
```

---

## Phase 4 — Expansion de la KB via SPARQL

**Source** : Step 4 | **Deadline** : Semaine 4 | **État** : 🔴 Non démarré

### Volume cible

| Métrique | Minimum | Maximum |
|----------|---------|---------|
| Triplets | 50 000 | 200 000 |
| Entités | 5 000 | 30 000 |
| Relations | 50 | 200 |

> ⚠️ KB trop petite → embeddings sans signal. KB trop grande → entraînement impossible sur laptop.

### Expansion SPARQL (partir uniquement des entités alignées avec haute confiance)

```sparql
-- 1-hop depuis Usain Bolt (wd:Q1190522)
SELECT ?p ?o WHERE { wd:Q1190522 ?p ?o . } LIMIT 1000

-- 2-hop : entités liées aux entités d'Usain Bolt
SELECT ?e2 ?p2 ?o2 WHERE {
  wd:Q1190522 ?p1 ?e2 .
  ?e2 ?p2 ?o2 .
} LIMIT 5000

-- Expansion par discipline : tous les athlètes pratiquant l'athlétisme
SELECT ?athlete ?p ?o WHERE {
  ?athlete wdt:P641 wd:Q542 .   -- sport = athletics
  ?athlete ?p ?o .
} LIMIT 10000
```

### Nettoyage post-expansion

- [ ] Supprimer les triplets en double
- [ ] Supprimer les URIs malformées
- [ ] Supprimer les prédicats à forte charge littérale (descriptions longues)
- [ ] Vérifier les stats finales (triplets, entités, relations)

### Livrable

```
kb/
├── knowledge_base_expanded.ttl
├── stats_kb.json
└── script_expansion_sparql.py
```

---

## Phase 5 — Raisonnement symbolique SWRL

**Source** : KB_Lab_Knowledge_reasoning.pdf — Part 1  
**Deadline** : Semaine 5 | **État** : 🔴 Non démarré

> ⚠️ Les règles SWRL de la section "Exercice lab" (oldPerson, hasBrother) viennent de `family.owl` — c'est un exercice pédagogique sans lien avec le projet. Les règles projet sont dans la section "Règles domaine sportifs" ci-dessous.

### Tâches

- [ ] Installer OWLReady2 : `pip install owlready2`
- [ ] Exercice lab : charger `family.owl` et valider la mécanique SWRL (requis par le lab)
- [ ] Écrire les règles SWRL du domaine sportifs (voir ci-dessous)
- [ ] Lancer l'inférence avec HermiT
- [ ] Documenter les faits inférés + les comparer avec les résultats KGE (Phase 6.4)

### Règles lab — exercice uniquement (family.owl)

```
Person(?p) ∧ hasAge(?p, ?a) ∧ swrlb:greaterThan(?a, 60) → oldPerson(?p)
Person(?p) ∧ hasSibling(?p, ?s) ∧ Man(?s) → hasBrother(?p, ?s)
```

### Règles SWRL — domaine Sportifs & compétitions (règles projet)

**Règle 1 — Rivaux directs** (deux athlètes ayant participé à la même compétition) :
```
Athlete(?a1) ∧ participatedIn(?a1, ?c) ∧ participatedIn(?a2, ?c)
  ∧ Athlete(?a2) ∧ differentFrom(?a1, ?a2)
  → hasCompeted(?a1, ?a2)
```

**Règle 2 — Athlète multi-médaillé** (athlète ayant gagné une médaille d'or ET d'argent) :
```
Athlete(?a) ∧ wonMedal(?a, ?m1) ∧ GoldMedal(?m1)
  ∧ wonMedal(?a, ?m2) ∧ SilverMedal(?m2)
  → multiMedalist(?a)
```

**Règle 3 — Compatriotes** (deux athlètes représentant le même pays) :
```
Athlete(?a1) ∧ represents(?a1, ?c) ∧ represents(?a2, ?c)
  ∧ Athlete(?a2) ∧ differentFrom(?a1, ?a2)
  → sameNationality(?a1, ?a2)
```

**Règle à utiliser pour la comparaison SWRL vs KGE (Phase 6.4)** — choisir la Règle 1 :
```
Vérifier si : vector(participatedIn) + vector(Competition) ≈ vector(hasCompeted)
```

### Code Python

```python
from owlready2 import get_ontology, Imp, sync_reasoner_pellet
from pathlib import Path

onto = get_ontology(str(Path(__file__).parent.parent / "kb/knowledge_base_expanded.owl")).load()

with onto:
    rule = Imp()
    rule.set_as_rule("""
        Athlete(?a1), participatedIn(?a1, ?c), participatedIn(?a2, ?c),
        Athlete(?a2), differentFrom(?a1, ?a2)
        -> hasCompeted(?a1, ?a2)
    """)

sync_reasoner_pellet()

print("Paires d'athlètes ayant concouru ensemble :")
for a1, a2 in onto.hasCompeted.get_relations():
    print(f"  {a1} ↔ {a2}")
```

### Livrable

```
raisonnement/
├── swrl_rules.py
├── resultats_swrl.txt
└── rapport_swrl.md
```

---

## Phase 6 — Knowledge Graph Embedding (KGE)

**Source** : KB_Lab_Knowledge_reasoning.pdf — Part 2  
**Deadline** : Semaines 5–7 | **État** : 🟡 En cours

### Étape 6.1 — Préparation des splits

- [x] Nettoyer la KB étendue ✅
- [x] Diviser en train (80%) / valid (10%) / test (10%) ✅
- [x] Exécuter le script de validation `validate_splits.py` ✅

#### Script de validation obligatoire

```python
# kge/validate_splits.py
from pathlib import Path

def load_entities(filepath: Path) -> set:
    entities = set()
    with open(filepath) as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) == 3:
                entities.add(parts[0])  # head
                entities.add(parts[2])  # tail
    return entities

base = Path(__file__).parent
train_e = load_entities(base / "train.txt")
valid_e = load_entities(base / "valid.txt")
test_e  = load_entities(base / "test.txt")

only_valid = valid_e - train_e
only_test  = test_e  - train_e

if only_valid:
    print(f"⚠️  {len(only_valid)} entité(s) uniquement dans valid.txt — corriger le split")
else:
    print("✅ valid.txt OK")

if only_test:
    print(f"⚠️  {len(only_test)} entité(s) uniquement dans test.txt — corriger le split")
else:
    print("✅ test.txt OK")
```

### Étape 6.2 — Entraînement PyKEEN

```python
# kge/train_kge.py
from pathlib import Path
from pykeen.pipeline import pipeline
from pykeen.triples import TriplesFactory

base = Path(__file__).parent

# TriplesFactory avec chemins absolus — évite les erreurs de répertoire courant
tf_train = TriplesFactory.from_path(base / "train.txt")
tf_valid = TriplesFactory.from_path(
    base / "valid.txt",
    entity_to_id=tf_train.entity_to_id,
    relation_to_id=tf_train.relation_to_id,
)
tf_test = TriplesFactory.from_path(
    base / "test.txt",
    entity_to_id=tf_train.entity_to_id,
    relation_to_id=tf_train.relation_to_id,
)

result = pipeline(
    training=tf_train,
    validation=tf_valid,
    testing=tf_test,
    model='TransE',               # Changer ici pour tester d'autres modèles
    model_kwargs=dict(embedding_dim=200),
    training_kwargs=dict(num_epochs=100, batch_size=512),
    optimizer_kwargs=dict(lr=0.001),
    negative_sampler='basic',
    random_seed=42,
)
result.save_to_directory(f'kge/results/TransE')
```

**Modèles à comparer (≥ 2, config identique) :**

| Modèle | Points forts | Limites connues |
|--------|-------------|-----------------|
| TransE | Simple, 1-to-1 | Échoue N-to-N, antisymétrique |
| DistMult | Relations symétriques | Pas d'antisymétrie |
| ComplEx | Asymétrie | Plus lent |
| RotatE | Symétrie + composition | Le plus complexe |

### Étape 6.3 — Évaluation (métriques filtrées)

Rapporter : MRR, Hits@1, Hits@3, Hits@10 — head + tail prediction.

### Étape 6.4 — Analyses

- [ ] Voisins les plus proches — cohérence sémantique
- [ ] Clustering t-SNE — entités colorées par classe ontologique
- [ ] Sensibilité à la taille : 20k / 50k / dataset complet
- [ ] Comportement des relations (symétrique, inverse, composition)
- [ ] Comparaison SWRL vs KGE sur la règle Horn de la Phase 5

### Livrable

```
kge/
├── validate_splits.py
├── train_kge.py
├── train.txt / valid.txt / test.txt
├── results/ TransE/ DistMult/
└── analyse/ nearest_neighbors.py / tsne_visualization.py
```

---

## Phase 7 — Assistant RAG alimenté par le KG

**Deadline** : Semaines 7–9 | **État** : 🟢 Terminé

### Architecture validée ✅

```
[Question NL]
     │
     ▼ 1. Entity Linking (spacy NER + fuzzy match sur la KB)
[Entité détectée → URI interne]
     │
     ▼ 2. NL → SPARQL (voir stratégies ci-dessous)
[Requête SPARQL]
     │
     ▼ 3. Exécution sur le graphe local (rdflib)
     │
  ┌──┴──────────────────────────┐
  │ Résultats trouvés            │ 0 résultat → fallback
  ▼                              ▼
[Triplets → contexte]      [Élargir requête ou signaler]
  │
  ▼ 4. Appel LLM (API OpenAI / Anthropic / Mistral)
[Réponse + triplets sources cités]
```

### Stratégie NL → SPARQL

**Option A — Templates (à implémenter en premier)**

```python
# rag/query_builder.py
TEMPLATES = {
    "medals": "SELECT ?o WHERE {{ :{e} :wonMedal ?o . }}",
    "competitions": "SELECT ?o WHERE {{ :{e} :participatedIn ?o . }}",
    "sport": "SELECT ?o WHERE {{ :{e} :practicesSport ?o . }}",
    "country": "SELECT ?o WHERE {{ :{e} :represents ?o . }}",
    "teammates": """
        SELECT ?p WHERE {{
            :{e} :memberOfTeam ?team .
            ?p :memberOfTeam ?team .
            FILTER(?p != :{e})
        }}
    """,
    "rivals": """
        SELECT ?p WHERE {{
            :{e} :participatedIn ?c .
            ?p :participatedIn ?c .
            FILTER(?p != :{e})
        }}
    """,
}

def build_query(intent: str, entity: str) -> str | None:
    return TEMPLATES.get(intent, "").format(e=entity) or None
```

**Option B — Few-shot prompting LLM → SPARQL**

```python
FEW_SHOT = """Génère une requête SPARQL. PREFIX : <http://monprojet.org/>

Q: Quelles médailles a remporté Usain Bolt ?
A: SELECT ?o WHERE { :UsainBolt :wonMedal ?o . }

Q: À quelles compétitions a participé Serena Williams ?
A: SELECT ?o WHERE { :SerenaWilliams :participatedIn ?o . }

Q: Quels athlètes représentent la France ?
A: SELECT ?a WHERE { ?a :represents :France . }

Q: {question}
A:"""
```

**Option C — Fallback si 0 résultat**

```python
# rag/sparql_executor.py
def query_with_fallback(query: str, graph) -> list:
    results = list(graph.query(query))
    if not results:
        entity = extract_entity(query)
        fallback = f"SELECT ?p ?o WHERE {{ :{entity} ?p ?o . }} LIMIT 20"
        results = list(graph.query(fallback))
    return results
```

### Prompt système LLM

```python
SYSTEM_PROMPT = """
Tu es un assistant expert en sports et compétitions sportives.
Tu disposes de faits extraits d'un Knowledge Graph structuré sur les athlètes,
les compétitions, les palmarès et les disciplines sportives.

RÈGLES :
1. Réponds UNIQUEMENT à partir des faits fournis.
2. Si les faits ne contiennent pas la réponse, dis-le explicitement.
3. Cite chaque fait utilisé : [sujet → prédicat → objet].
4. Ne génère aucun fait absent du contexte.

FAITS :
{context_triplets}

QUESTION : {question}
"""
```

### Gestion des API et sécurité

```
# .env  (ne JAMAIS committer — ajouter au .gitignore)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Coût estimé : ~$0.002 / requête GPT-3.5-turbo
# Alternative gratuite : Mistral 7B via HuggingFace Inference API
```

### Gestion des cas limites

| Situation | Comportement |
|-----------|-------------|
| 0 triplet trouvé | Signaler explicitement + proposer entités proches |
| Entité ambiguë | Proposer les candidats ou demander clarification |
| Trop de triplets (> 50) | Tronquer, prioriser les triplets directs |
| Erreur SPARQL | Logger l'erreur, message générique à l'utilisateur |
| Clé API invalide | Lever une exception claire, ne pas continuer |

### Livrable

```
rag/
├── .env.example               # Template sans valeurs réelles
├── query_builder.py
├── sparql_executor.py
├── llm_client.py
├── rag_assistant.py
├── demo.ipynb
└── exemples_questions.md      # Questions de test avec réponses attendues
```

---

## Phase 8 — Rendu final

**Deadline** : Juin 2026

### Checklist finale

- [x] Domaine verrouillé : **Sportifs & compétitions** ✅
- [ ] KB étendue dans les volumes cibles (50k–200k triplets)
- [x] `validate_splits.py` exécuté sans erreur avant l'entraînement KGE ✅
- [ ] ≥ 2 modèles KGE entraînés avec configuration identique
- [ ] Métriques MRR/Hits@1/3/10 en métriques filtrées
- [x] ≥ 1 règle SWRL adaptée au domaine (pas family.owl) ✅
- [ ] Comparaison SWRL vs KGE sur une même règle Horn
- [ ] Clustering t-SNE produit et commenté
- [x] RAG fonctionnel avec gestion du cas 0 résultat ✅
- [x] Fichier .env hors dépôt (.gitignore) ✅
- [x] Toute la structure de Phase 7 validée par pytest ✅
- [ ] Rapport 4–6 pages
- [ ] GitHub propre avec README
- [ ] Présentation orale préparée

---

## Observations attendues (issues des labs)

| Observation | Explication |
|-------------|------------|
| Petites KB → embeddings instables | Pas assez de signal pour apprendre |
| TransE échoue sur relations N-to-N | Modèle trop simple |
| DistMult échoue sur relations antisymétriques | Symétrique par construction |
| ComplEx gère mieux l'asymétrie | Espace complexe |
| Grandes KB → meilleure stabilité | Plus de contexte |
| KB mal construite → mauvais RAG | Qualité KB = fondation du projet |

---

*Dernière mise à jour : 18/03/2026 — Architecture Phase 7 validée à 100%.*
