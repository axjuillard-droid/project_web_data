"""
Phase 6 — Préparation des splits train/valid/test
==================================================
Ce script :
  1. Charge la KB étendue (knowledge_base_expanded.ttl)
  2. Extrait tous les triplets (h, r, t) en format texte tab-séparé
  3. Filtre les triplets pour ne garder que les URIs locales ou Wikidata utilisables
  4. S'assure que toutes les entités de valid/test sont dans train (stratified split)
  5. Exporte kge/train.txt, kge/valid.txt, kge/test.txt

Usage :
    python kge/prepare_splits.py

Prérequis :
    - kb/knowledge_base_expanded.ttl doit exister (Phase 4)
"""

import random
import json
from pathlib import Path
from collections import defaultdict
from rdflib import Graph, URIRef, Literal, RDF

# ─── Chemins ────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent.parent.parent / "data" / "kge"
KB_DIR    = Path(__file__).parent.parent.parent / "kg_artifacts"
KB_EXP    = Path(__file__).parent.parent.parent / "kg_artifacts" / "expanded.ttl"
KB_V1     = Path(__file__).parent.parent.parent / "kg_artifacts" / "knowledge_base_v1.ttl"
TRAIN_OUT = BASE_DIR / "train.txt"
VALID_OUT = BASE_DIR / "valid.txt"
TEST_OUT  = BASE_DIR / "test.txt"
STATS_OUT = BASE_DIR / "splits_stats.json"

# Proportions du split
RATIO_TRAIN = 0.80
RATIO_VALID = 0.10
RATIO_TEST  = 0.10

# URIs à exclure (méta-prédicats RDF/RDFS/OWL)
PREDICATS_EXCLUS = {
    str(RDF.type),
    "http://www.w3.org/2000/01/rdf-schema#label",
    "http://www.w3.org/2000/01/rdf-schema#comment",
    "http://www.w3.org/2000/01/rdf-schema#subClassOf",
    "http://www.w3.org/2000/01/rdf-schema#subPropertyOf",
    "http://www.w3.org/2000/01/rdf-schema#domain",
    "http://www.w3.org/2000/01/rdf-schema#range",
    "http://www.w3.org/2002/07/owl#sameAs",
    "http://www.w3.org/2002/07/owl#equivalentProperty",
    "http://www.w3.org/2002/07/owl#equivalentClass",
    "http://www.w3.org/2002/07/owl#ObjectProperty",
    "http://www.w3.org/2002/07/owl#DatatypeProperty",
    "http://www.w3.org/2002/07/owl#Class",
    "http://wikiba.se/ontology#",
}


def uri_acceptable(uri_str: str) -> bool:
    """Filtre les URIs acceptables pour les triplets KGE."""
    if uri_str.startswith("http://monprojet.org/sports/"):
        return True
    if uri_str.startswith("http://www.wikidata.org/entity/Q"):
        return True
    if uri_str.startswith("http://www.wikidata.org/prop/direct/"):
        return True
    return False


def predicat_exclus(pred_str: str) -> bool:
    """Retourne True si le prédicat doit être exclu."""
    for exclu in PREDICATS_EXCLUS:
        if pred_str.startswith(exclu):
            return True
    return False


def extraire_triplets(g: Graph) -> list:
    """
    Extrait tous les triplets (h, r, t) utilisables pour KGE.
    Retourne une liste de tuples (head_str, relation_str, tail_str).
    """
    triplets = []
    seen = set()
    for s, p, o in g:
        if not isinstance(s, URIRef) or not isinstance(p, URIRef):
            continue
        if not isinstance(o, URIRef):  # exclure les littéraux
            continue
        s_str = str(s)
        p_str = str(p)
        o_str = str(o)
        # Filtre sur les URIs
        if not uri_acceptable(s_str) or not uri_acceptable(o_str):
            continue
        if predicat_exclus(p_str):
            continue
        triplet = (s_str, p_str, o_str)
        if triplet not in seen:
            seen.add(triplet)
            triplets.append(triplet)
    return triplets


def split_stratifie(triplets: list, ratio_train: float, ratio_valid: float,
                    seed: int = 42) -> tuple[list, list, list]:
    """
    Split stratifié : garantit que toutes les entités de valid/test
    apparaissent au moins une fois dans train.
    Algorithme :
      1. Pour chaque entité, garder au moins 1 triplet dans train
      2. Mélanger le reste et distribuer selon les ratios
    """
    random.seed(seed)
    random.shuffle(triplets)

    # Index : entité → liste d'indices de triplets où elle apparaît
    entite_to_triplets = defaultdict(set)
    for i, (h, r, t) in enumerate(triplets):
        entite_to_triplets[h].add(i)
        entite_to_triplets[t].add(i)

    # Phase 1 : garantir couverture de toutes les entités dans train
    indices_train_garantis = set()
    for entite, indices in entite_to_triplets.items():
        # Choisir le triplet avec le moins de couverture (pour maximiser la diversité)
        idx = min(indices, key=lambda i: len(entite_to_triplets[triplets[i][0]]) +
                                        len(entite_to_triplets[triplets[i][2]]))
        indices_train_garantis.add(idx)

    # Phase 2 : distribuer le reste selon les ratios
    indices_restants = [i for i in range(len(triplets)) if i not in indices_train_garantis]
    random.shuffle(indices_restants)

    n_restants = len(indices_restants)
    # On compte les triplets déjà dans train pour ajuster
    n_train_objectif = int(len(triplets) * ratio_train)
    n_valid_objectif = int(len(triplets) * ratio_valid)

    n_train_restant = max(0, n_train_objectif - len(indices_train_garantis))
    n_valid_restant = n_valid_objectif

    idx_train_reste = indices_restants[:n_train_restant]
    idx_valid       = indices_restants[n_train_restant:n_train_restant + n_valid_restant]
    idx_test        = indices_restants[n_train_restant + n_valid_restant:]

    # Assembler les sets finaux
    tous_train_idx = indices_train_garantis | set(idx_train_reste)
    train = [triplets[i] for i in sorted(tous_train_idx)]
    valid = [triplets[i] for i in idx_valid]
    test  = [triplets[i] for i in idx_test]

    return train, valid, test


def ecrire_fichier(triplets: list, chemin: Path) -> None:
    """Écrit les triplets dans un fichier tab-séparé."""
    with open(chemin, "w", encoding="utf-8") as f:
        for h, r, t in triplets:
            f.write(f"{h}\t{r}\t{t}\n")


def main():
    print("=" * 60)
    print("Phase 6 — Préparation des splits train/valid/test")
    print("=" * 60)

    # Charger la KB (étendue si disponible, sinon initiale)
    kb_file = KB_EXP if KB_EXP.exists() else KB_V1
    if not kb_file.exists():
        print(f"❌ Aucune KB disponible (ni expanded ni v1).")
        print("   → Exécuter d'abord : python src/kg/script_construction.py")
        return

    print(f"\n[1/5] Chargement de {kb_file.name}...")
    g = Graph()
    g.parse(str(kb_file), format="turtle")
    print(f"  → {len(g)} triplets RDF chargés")

    print("\n[2/5] Extraction des triplets utilisables pour KGE...")
    triplets = extraire_triplets(g)
    print(f"  → {len(triplets):,} triplets retenus")

    if len(triplets) < 100:
        print("  ⚠️  Très peu de triplets — vérifier la KB étendue (Phase 4)")

    print("\n[3/5] Split stratifié (80/10/10)...")
    train, valid, test = split_stratifie(triplets, RATIO_TRAIN, RATIO_VALID)
    total = len(train) + len(valid) + len(test)
    print(f"  train : {len(train):>8,} ({len(train)/total*100:.1f}%)")
    print(f"  valid : {len(valid):>8,} ({len(valid)/total*100:.1f}%)")
    print(f"  test  : {len(test):>8,}  ({len(test)/total*100:.1f}%)")

    print("\n[4/5] Écriture des fichiers...")
    BASE_DIR.mkdir(exist_ok=True)
    ecrire_fichier(train, TRAIN_OUT)
    ecrire_fichier(valid, VALID_OUT)
    ecrire_fichier(test,  TEST_OUT)
    print(f"  ✅ {TRAIN_OUT}")
    print(f"  ✅ {VALID_OUT}")
    print(f"  ✅ {TEST_OUT}")

    print("\n[5/5] Statistiques et export...")
    # Entités uniques par split
    train_e = set(h for h, r, t in train) | set(t for h, r, t in train)
    valid_e = set(h for h, r, t in valid) | set(t for h, r, t in valid)
    test_e  = set(h for h, r, t in test)  | set(t for h, r, t in test)
    relations = set(r for h, r, t in triplets)

    stats = {
        "kb_source":       kb_file.name,
        "total_triplets":  total,
        "train_triplets":  len(train),
        "valid_triplets":  len(valid),
        "test_triplets":   len(test),
        "total_entites":   len(train_e | valid_e | test_e),
        "train_entites":   len(train_e),
        "valid_entites":   len(valid_e),
        "test_entites":    len(test_e),
        "total_relations": len(relations),
        "entites_only_valid": len(valid_e - train_e),
        "entites_only_test":  len(test_e - train_e),
    }
    with open(STATS_OUT, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"  ✅ {STATS_OUT}")

    print("\n📊 Résumé :")
    for k, v in stats.items():
        print(f"   {k:<25} : {v}")

    jeux_ok = stats["entites_only_valid"] == 0 and stats["entites_only_test"] == 0
    if jeux_ok:
        print("\n✅ Split correct — Lancer la validation : python kge/validate_splits.py")
    else:
        print(f"\n⚠️  Entités sans couverture train : valid={stats['entites_only_valid']}, test={stats['entites_only_test']}")
        print("   → Cela devrait être 0 avec le split stratifié — vérifier le code")


if __name__ == "__main__":
    main()
