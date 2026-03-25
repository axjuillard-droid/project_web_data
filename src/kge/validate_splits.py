"""
Phase 6 — Validation des splits train/valid/test
=================================================
Ce script vérifie que :
  1. Toutes les entités de valid.txt et test.txt apparaissent aussi dans train.txt
  2. Il n'y a pas de fuite (triplets identiques entre splits)
  3. Les proportions sont respectables (≈ 80/10/10)

À exécuter OBLIGATOIREMENT avant tout entraînement KGE.

Usage :
    python kge/validate_splits.py
"""

from pathlib import Path
import sys


BASE_DIR = Path(__file__).parent.parent.parent / "data" / "kge"
TRAIN_FILE = BASE_DIR / "train.txt"
VALID_FILE = BASE_DIR / "valid.txt"
TEST_FILE  = BASE_DIR / "test.txt"


def charger_entites(filepath: Path) -> tuple[set, set]:
    """
    Charge un fichier de triplets (tab-séparé : head\\trelation\\ttail).
    Retourne (ensemble_entites, ensemble_triplets).
    """
    entites = set()
    triplets = set()
    if not filepath.exists():
        return entites, triplets
    with open(filepath, encoding="utf-8") as f:
        for ligne_num, ligne in enumerate(f, 1):
            ligne = ligne.strip()
            if not ligne:
                continue
            parts = ligne.split("\t")
            if len(parts) != 3:
                print(f"  ⚠️  {filepath.name} ligne {ligne_num} : format invalide → '{ligne[:80]}'")
                continue
            head, relation, tail = parts
            entites.add(head)
            entites.add(tail)
            triplets.add((head, relation, tail))
    return entites, triplets


def main():
    print("=" * 60)
    print("Validation des splits KGE")
    print("=" * 60)

    erreurs = 0

    # Vérifier existence des fichiers
    for f in [TRAIN_FILE, VALID_FILE, TEST_FILE]:
        if not f.exists():
            print(f"  ❌ Fichier manquant : {f}")
            print(f"     → Exécuter d'abord : python kge/prepare_splits.py")
            erreurs += 1

    if erreurs > 0:
        print(f"\n❌ {erreurs} erreur(s) critique(s) — arrêt")
        sys.exit(1)

    print("\n[1/4] Chargement des splits...")
    train_e, train_t = charger_entites(TRAIN_FILE)
    valid_e, valid_t = charger_entites(VALID_FILE)
    test_e,  test_t  = charger_entites(TEST_FILE)

    print(f"  train.txt : {len(train_t):>8,} triplets | {len(train_e):>6,} entités")
    print(f"  valid.txt : {len(valid_t):>8,} triplets | {len(valid_e):>6,} entités")
    print(f"  test.txt  : {len(test_t):>8,} triplets | {len(test_e):>6,} entités")
    total = len(train_t) + len(valid_t) + len(test_t)
    print(f"  Total     : {total:>8,} triplets")

    print("\n[2/4] Vérification de la couverture des entités...")
    only_valid = valid_e - train_e
    only_test  = test_e  - train_e
    if only_valid:
        print(f"  ❌ {len(only_valid)} entité(s) dans valid.txt mais PAS dans train.txt :")
        for e in list(only_valid)[:10]:
            print(f"     - {e}")
        erreurs += 1
    else:
        print(f"  ✅ valid.txt : toutes les entités présentes dans train.txt")

    if only_test:
        print(f"  ❌ {len(only_test)} entité(s) dans test.txt mais PAS dans train.txt :")
        for e in list(only_test)[:10]:
            print(f"     - {e}")
        erreurs += 1
    else:
        print(f"  ✅ test.txt  : toutes les entités présentes dans train.txt")

    print("\n[3/4] Vérification des fuites (triplets en commun entre splits)...")
    fuite_train_valid = train_t & valid_t
    fuite_train_test  = train_t & test_t
    fuite_valid_test  = valid_t & test_t

    if fuite_train_valid:
        print(f"  ⚠️  {len(fuite_train_valid)} triplet(s) en commun entre train et valid")
        erreurs += 1
    else:
        print(f"  ✅ Aucun triplet en commun entre train et valid")

    if fuite_train_test:
        print(f"  ⚠️  {len(fuite_train_test)} triplet(s) en commun entre train et test")
        erreurs += 1
    else:
        print(f"  ✅ Aucun triplet en commun entre train et test")

    if fuite_valid_test:
        print(f"  ⚠️  {len(fuite_valid_test)} triplet(s) en commun entre valid et test")
        erreurs += 1
    else:
        print(f"  ✅ Aucun triplet en commun entre valid et test")

    print("\n[4/4] Vérification des proportions...")
    if total > 0:
        pct_train = len(train_t) / total * 100
        pct_valid = len(valid_t) / total * 100
        pct_test  = len(test_t)  / total * 100
        print(f"  train : {pct_train:.1f}% (cible : ~80%)")
        print(f"  valid : {pct_valid:.1f}% (cible : ~10%)")
        print(f"  test  : {pct_test:.1f}%  (cible : ~10%)")
        if not (70 <= pct_train <= 90):
            print(f"  ⚠️  Proportion train hors de la plage recommandée (70–90%)")
    else:
        print("  ⚠️  Total de triplets = 0 — les fichiers sont vides")
        erreurs += 1

    # Bilan final
    print("\n" + "=" * 60)
    if erreurs == 0:
        print(f"✅ VALIDATION PASSÉE — Les splits sont corrects")
        print("   → Vous pouvez procéder à l'entraînement : python kge/train_kge.py")
    else:
        print(f"❌ VALIDATION ÉCHOUÉE — {erreurs} problème(s) détecté(s)")
        print("   → Corriger les erreurs avant d'entraîner les modèles")
        sys.exit(1)


if __name__ == "__main__":
    main()
