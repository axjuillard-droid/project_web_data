"""
Phase 6 — Entraînement des modèles KGE avec PyKEEN
====================================================
Ce script :
  1. Charge les splits train/valid/test via TriplesFactory (chemins absolus)
  2. Entraîne au minimum 2 modèles avec une configuration identique
  3. Évalue en métriques filtrées (MRR, Hits@1/3/10 — head + tail)
  4. Exporte les résultats dans kge/results/<modèle>/
  5. Génère un tableau de comparaison des modèles

Usage :
    python kge/train_kge.py [--model TransE] [--model DistMult]
    (sans arguments : entraîne tous les modèles configurés)

Prérequis :
    - kge/validate_splits.py doit passer sans erreur
    - pip install pykeen torch
"""

import json
import argparse
import time
from pathlib import Path

# ─── Chemins ────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent.parent
BASE_DIR    = ROOT / "data" / "kge"
TRAIN_FILE  = BASE_DIR / "train.txt"
VALID_FILE  = BASE_DIR / "valid.txt"
TEST_FILE   = BASE_DIR / "test.txt"
RESULTS_DIR = ROOT / "models" / "kge_results" / "results"
COMPARE_OUT = RESULTS_DIR.parent / "comparaison_modeles.json"

# ─── Configuration commune (identique pour tous les modèles) ─────────────────
CONFIG_COMMUNE = dict(
    embedding_dim  = 200,
    learning_rate  = 0.001,
    batch_size     = 512,
    num_epochs     = 100,
    negative_sampler = "basic",
    random_seed    = 42,
)

# ─── Modèles à entraîner ─────────────────────────────────────────────────────
MODELES = ["TransE", "DistMult", "ComplEx", "RotatE"]

# ─── Tailles de sous-ensembles pour l'analyse de sensibilité ─────────────────
TAILLES_ANALYSE = [20_000, 50_000, None]  # None = dataset complet


def verifier_pykeen():
    """Vérifie que PyKEEN est installé."""
    try:
        import pykeen
        return True
    except ImportError:
        print("❌ PyKEEN non installé. Exécuter : pip install pykeen")
        return False


def charger_triples_factory(train_path: Path, valid_path: Path, test_path: Path):
    """
    Charge les splits via TriplesFactory avec chemins absolus.
    Partage les index entités/relations pour garantir la cohérence.
    """
    from pykeen.triples import TriplesFactory

    print(f"  Chargement de {train_path.name}...")
    tf_train = TriplesFactory.from_path(
        train_path,
        create_inverse_triples=False,
    )
    print(f"    → {tf_train.num_triples:,} triplets / {tf_train.num_entities:,} entités / {tf_train.num_relations:,} relations")

    print(f"  Chargement de {valid_path.name} (index partagé)...")
    tf_valid = TriplesFactory.from_path(
        valid_path,
        entity_to_id=tf_train.entity_to_id,
        relation_to_id=tf_train.relation_to_id,
    )

    print(f"  Chargement de {test_path.name} (index partagé)...")
    tf_test = TriplesFactory.from_path(
        test_path,
        entity_to_id=tf_train.entity_to_id,
        relation_to_id=tf_train.relation_to_id,
    )

    return tf_train, tf_valid, tf_test


def entrainer_modele(nom_modele: str, tf_train, tf_valid, tf_test,
                     output_dir: Path) -> dict:
    """
    Entraîne un modèle KGE avec PyKEEN et retourne les métriques.
    """
    from pykeen.pipeline import pipeline

    print(f"\n  → Entraînement {nom_modele}...")
    output_dir.mkdir(parents=True, exist_ok=True)

    t_debut = time.time()
    try:
        result = pipeline(
            training   = tf_train,
            validation = tf_valid,
            testing    = tf_test,
            model      = nom_modele,
            model_kwargs = dict(
                embedding_dim = CONFIG_COMMUNE["embedding_dim"],
            ),
            training_kwargs = dict(
                num_epochs = CONFIG_COMMUNE["num_epochs"],
                batch_size = CONFIG_COMMUNE["batch_size"],
            ),
            optimizer_kwargs = dict(
                lr = CONFIG_COMMUNE["learning_rate"],
            ),
            negative_sampler = CONFIG_COMMUNE["negative_sampler"],
            random_seed      = CONFIG_COMMUNE["random_seed"],
            evaluator_kwargs = dict(
                filtered=True,  # métriques filtrées uniquement
            ),
        )
        result.save_to_directory(str(output_dir))
        t_fin = time.time()

        # Extraire les métriques
        metriques = extraire_metriques(result, nom_modele, t_fin - t_debut)
        print(f"    ✅ {nom_modele} terminé en {t_fin - t_debut:.0f}s")
        return metriques

    except Exception as e:
        print(f"    ❌ Erreur lors de l'entraînement de {nom_modele} : {e}")
        return {"modele": nom_modele, "erreur": str(e)}


def extraire_metriques(result, nom_modele: str, duree_s: float) -> dict:
    """Extrait les métriques filtrées (MRR, Hits@1/3/10) depuis le résultat PyKEEN."""
    metriques = {
        "modele":           nom_modele,
        "embedding_dim":    CONFIG_COMMUNE["embedding_dim"],
        "learning_rate":    CONFIG_COMMUNE["learning_rate"],
        "batch_size":       CONFIG_COMMUNE["batch_size"],
        "num_epochs":       CONFIG_COMMUNE["num_epochs"],
        "duree_secondes":   round(duree_s),
    }
    try:
        met = result.metric_results.to_dict()
        # Double index : on cherche les métriques filtrées (both head + tail)
        for key, val in met.items():
            k_lower = key.lower()
            if "mrr" in k_lower and "filtered" in k_lower:
                metriques["MRR_filtered"] = round(float(val), 4)
            elif "hits_at_1" in k_lower and "filtered" in k_lower:
                metriques["Hits@1_filtered"] = round(float(val), 4)
            elif "hits_at_3" in k_lower and "filtered" in k_lower:
                metriques["Hits@3_filtered"] = round(float(val), 4)
            elif "hits_at_10" in k_lower and "filtered" in k_lower:
                metriques["Hits@10_filtered"] = round(float(val), 4)
    except Exception as e:
        print(f"    ⚠️  Erreur lors de l'extraction des métriques : {e}")
        # Fallback : essayer l'attribut .metric_results directement
        try:
            metriques["MRR_filtered"]    = round(result.metric_results.get_metric("both.realistic.inverse_harmonic_mean_rank"), 4)
            metriques["Hits@1_filtered"] = round(result.metric_results.get_metric("both.realistic.hits_at_1"), 4)
            metriques["Hits@3_filtered"] = round(result.metric_results.get_metric("both.realistic.hits_at_3"), 4)
            metriques["Hits@10_filtered"] = round(result.metric_results.get_metric("both.realistic.hits_at_10"), 4)
        except Exception:
            pass
    return metriques


def afficher_tableau_comparaison(tous_resultats: list) -> None:
    """Affiche un tableau ASCII de comparaison des modèles."""
    if not tous_resultats:
        return
    print("\n" + "=" * 80)
    print("COMPARAISON DES MODÈLES KGE (métriques filtrées)")
    print("=" * 80)
    header = f"{'Modèle':<12} {'MRR':>8} {'Hits@1':>8} {'Hits@3':>8} {'Hits@10':>8} {'Durée':>8}"
    print(header)
    print("-" * 80)
    for r in tous_resultats:
        if "erreur" in r:
            print(f"  {r['modele']:<12} ERREUR : {r['erreur'][:50]}")
            continue
        mrr    = r.get("MRR_filtered",    "—")
        h1     = r.get("Hits@1_filtered", "—")
        h3     = r.get("Hits@3_filtered", "—")
        h10    = r.get("Hits@10_filtered","—")
        duree  = r.get("duree_secondes",  "—")
        mrr_s  = f"{mrr:.4f}" if isinstance(mrr, float) else str(mrr)
        h1_s   = f"{h1:.4f}"  if isinstance(h1, float)  else str(h1)
        h3_s   = f"{h3:.4f}"  if isinstance(h3, float)  else str(h3)
        h10_s  = f"{h10:.4f}" if isinstance(h10, float) else str(h10)
        dur_s  = f"{duree}s"  if isinstance(duree, int)  else str(duree)
        print(f"  {r['modele']:<12} {mrr_s:>8} {h1_s:>8} {h3_s:>8} {h10_s:>8} {dur_s:>8}")
    print("=" * 80)


def main():
    print("=" * 60)
    print("Phase 6 — Entraînement des modèles KGE")
    print("=" * 60)

    parser = argparse.ArgumentParser(description="Entraînement KGE PyKEEN")
    parser.add_argument("--model", action="append", dest="models",
                        help="Modèle(s) à entraîner (ex: --model TransE --model DistMult)")
    parser.add_argument("--epochs", type=int, default=CONFIG_COMMUNE["num_epochs"],
                        help=f"Nombre d'époques (défaut: {CONFIG_COMMUNE['num_epochs']})")
    args = parser.parse_args()

    if not verifier_pykeen():
        return

    # Vérifier les fichiers de splits
    for f in [TRAIN_FILE, VALID_FILE, TEST_FILE]:
        if not f.exists():
            print(f"❌ {f} non trouvé — exécuter d'abord :")
            print("   python kge/prepare_splits.py")
            print("   python kge/validate_splits.py")
            return

    modeles_a_entrainer = args.models if args.models else MODELES[:2]  # par défaut : TransE + DistMult
    CONFIG_COMMUNE["num_epochs"] = args.epochs

    print(f"\nModèles : {modeles_a_entrainer}")
    print(f"Config  : embedding_dim={CONFIG_COMMUNE['embedding_dim']}, "
          f"lr={CONFIG_COMMUNE['learning_rate']}, "
          f"batch={CONFIG_COMMUNE['batch_size']}, "
          f"epochs={CONFIG_COMMUNE['num_epochs']}")

    print("\n[1/3] Chargement des splits...")
    tf_train, tf_valid, tf_test = charger_triples_factory(TRAIN_FILE, VALID_FILE, TEST_FILE)

    print("\n[2/3] Entraînement des modèles...")
    RESULTS_DIR.mkdir(exist_ok=True)
    tous_resultats = []

    for nom_modele in modeles_a_entrainer:
        output_dir = RESULTS_DIR / nom_modele
        metriques = entrainer_modele(nom_modele, tf_train, tf_valid, tf_test, output_dir)
        tous_resultats.append(metriques)

    print("\n[3/3] Export de la comparaison...")
    with open(COMPARE_OUT, "w", encoding="utf-8") as f:
        json.dump({
            "configuration": CONFIG_COMMUNE,
            "resultats": tous_resultats,
        }, f, indent=2, ensure_ascii=False)
    print(f"  ✅ {COMPARE_OUT}")

    afficher_tableau_comparaison(tous_resultats)

    print("\n✅ Phase 6 (entraînement) terminée")
    print("   → Analyses : python kge/analyse/nearest_neighbors.py")
    print("   → Analyse : python kge/analyse/tsne_visualization.py")


if __name__ == "__main__":
    main()
