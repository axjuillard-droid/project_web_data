# Tests — Knowledge Graph & RAG Assistant

Suite de tests automatisés couvrant les 4 phases principales du projet.  
Domaine : **Sportifs & compétitions**

---

## Lancement rapide

```bash
# Installer les dépendances
pip install pytest rdflib owlready2 pykeen python-dotenv

# Lancer tous les tests (hors LLM)
pytest -v

# Lancer une phase spécifique
pytest tests/test_kb_validation.py -v    # Phases 1–4 : KB RDF
pytest tests/test_kge.py -v              # Phase 6 : KGE
pytest tests/test_swrl.py -v             # Phase 5 : SWRL
pytest tests/test_rag.py -v              # Phase 7 : RAG

# Lancer uniquement les tests rapides (sans charger la KB étendue)
pytest -v -m "not slow"

# Lancer les tests LLM (nécessite une clé API dans .env)
pytest tests/test_rag.py -v -m llm
```

---

## Structure des tests

```
tests/
├── conftest.py              # Configuration et marqueurs pytest
├── test_kb_validation.py    # Phases 1–4 : structure et volume de la KB
├── test_kge.py              # Phase 6 : splits, entraînement, métriques
├── test_swrl.py             # Phase 5 : règles SWRL, résultats, comparaison
└── test_rag.py              # Phase 7 : query builder, executor, pipeline LLM
```

---

## Ce que chaque fichier valide

### `test_kb_validation.py` — Phases 1 à 4

| Classe | Ce qui est testé |
|--------|-----------------|
| `TestKBInitiale` | ≥ 100 triplets, ≥ 50 entités, pas de doublons, URIs valides, camelCase, athletes typés |
| `TestAlignementEntites` | Présence owl:sameAs, URIs Wikidata/DBpedia, taux de couverture ≥ 50% |
| `TestAlignementPredicats` | Présence owl:equivalentProperty, prédicats clés alignés |
| `TestKBEtendue` | Volume 50k–200k triplets, 5k–30k entités, 50–200 relations, connectivité, stats_kb.json |
| `TestOntologie` | Classes requises (Athlete, Competition…), propriétés avec domain+range |

### `test_kge.py` — Phase 6

| Classe | Ce qui est testé |
|--------|-----------------|
| `TestSplits` | Format TSV, proportions 80/10/10, couverture entités, pas de leakage |
| `TestModelesEntraines` | ≥ 2 modèles présents, fichiers PyKEEN complets |
| `TestMetriques` | MRR ≥ 0.05, Hits@10 ≥ 0.10, comparaison documentée |
| `TestAnalyses` | t-SNE présent, nearest_neighbors.py présent, validate_splits.py présent |

### `test_swrl.py` — Phase 5

| Classe | Ce qui est testé |
|--------|-----------------|
| `TestStructureSWRL` | Fichiers présents, import owlready2, pas de règles family.owl, termes sportifs |
| `TestResultatsSWRL` | Fichier résultats non vide, termes domaine sportifs, rapport documenté |
| `TestComparaisonSWRLvsKGE` | Mention KGE dans le rapport, règle Horn identifiée pour comparaison |

### `test_rag.py` — Phase 7

| Classe | Ce qui est testé |
|--------|-----------------|
| `TestStructureRAG` | Tous les fichiers requis, .env.example sans vraie clé, .env dans .gitignore |
| `TestQueryBuilder` | build_query() retourne SPARQL valide, intents domaine couverts |
| `TestSparqlExecutor` | Requête valide → résultats, entité inconnue → [] sans exception, triplets existent dans le graphe |
| `TestPipelineRAG` | rag_assistant importable, prompt cite les sources, fallback 0-résultat géré |
| `TestLLM` *(nécessite clé API)* | Réponse non vide, citation de triplets, aveu d'ignorance sur entité inconnue |

---

## Interprétation des résultats

| Statut | Signification |
|--------|--------------|
| ✅ PASSED | La phase est correctement implémentée |
| ❌ FAILED | Erreur à corriger — lire le message d'assertion pour le détail |
| ⏭ SKIPPED | Fichier absent — la phase n'a pas encore démarré |
| ⚠️ XFAIL | Comportement attendu défaillant (à documenter) |

Les tests `SKIPPED` ne sont pas des échecs : ils indiquent simplement que la phase correspondante n'a pas encore été réalisée. Au fil de l'avancement du projet, le nombre de SKIPPED doit diminuer et le nombre de PASSED augmenter.

---

## Seuils de métriques KGE

Ces seuils sont volontairement bas — ils représentent le signal minimal d'apprentissage, pas un objectif de performance.

| Métrique | Seuil minimum |
|----------|--------------|
| MRR | 0.05 |
| Hits@1 | 0.02 |
| Hits@10 | 0.10 |

Pour un bon modèle sur ce domaine, les valeurs attendues sont plutôt MRR > 0.15 et Hits@10 > 0.30.

---

## Avancement projet — indicateur rapide

En lançant `pytest --tb=no -q`, le résumé final donne une vue rapide :

```
# Début de projet (tout skippé sauf domaine)
47 skipped in 0.12s

# Milieu de projet (KB construite, KGE en cours)
18 passed, 22 skipped, 7 failed in 4.31s

# Fin de projet (tout doit passer)
47 passed in 12.44s
```
