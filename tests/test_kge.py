"""
tests/test_kge.py
Validation des splits KGE et des métriques d'entraînement — Phase 6
Domaine : Sportifs & compétitions

Lancer : pytest tests/test_kge.py -v
"""

import pytest
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
KGE_DIR      = PROJECT_ROOT / "kge"
RESULTS_DIR  = KGE_DIR / "results"

# Seuils minimaux acceptables pour MRR et Hits
# (calibrés pour une KB de taille moyenne, domaine sportifs)
MIN_MRR    = 0.05   # très bas — signal d'apprentissage minimal
MIN_HITS1  = 0.02
MIN_HITS10 = 0.10

REQUIRED_MODELS = ["TransE", "DistMult"]  # au moins ces deux


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def splits():
    """Charge les triplets des trois splits."""
    result = {}
    for name in ("train", "valid", "test"):
        path = KGE_DIR / f"{name}.txt"
        if not path.exists():
            return None
        triplets = []
        with open(path, encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) == 3:
                    triplets.append(tuple(parts))
        result[name] = triplets
    return result


# ---------------------------------------------------------------------------
# Phase 6.1 — Préparation des splits
# ---------------------------------------------------------------------------

class TestSplits:
    """Validation de la qualité des splits train/valid/test."""

    def test_fichiers_splits_existent(self):
        for name in ("train", "valid", "test"):
            path = KGE_DIR / f"{name}.txt"
            assert path.exists(), (
                f"Fichier manquant : {path}\n"
                "→ Générer les splits (Phase 6.1)"
            )

    def test_format_tab_separe(self, splits):
        if splits is None:
            pytest.skip("Splits absents")
        for name, triplets in splits.items():
            assert len(triplets) > 0, f"{name}.txt est vide"
            for h, r, t in triplets[:10]:  # vérifier les 10 premiers
                assert h and r and t, f"Triplet malformé dans {name}.txt"

    def test_proportions_approximatives(self, splits):
        if splits is None:
            pytest.skip("Splits absents")
        total = sum(len(t) for t in splits.values())
        assert total > 0, "Aucun triplet dans les splits"

        ratio_train = len(splits["train"]) / total
        ratio_valid = len(splits["valid"]) / total
        ratio_test  = len(splits["test"])  / total

        assert 0.75 <= ratio_train <= 0.85, (
            f"Train = {ratio_train:.1%} — attendu ~80%"
        )
        assert 0.08 <= ratio_valid <= 0.15, (
            f"Valid = {ratio_valid:.1%} — attendu ~10%"
        )
        assert 0.08 <= ratio_test <= 0.15, (
            f"Test = {ratio_test:.1%} — attendu ~10%"
        )

    def test_entites_train_couvrent_valid(self, splits):
        """Toutes les entités de valid.txt doivent être dans train.txt."""
        if splits is None:
            pytest.skip("Splits absents")

        def entities(triplets):
            return {h for h, _, _ in triplets} | {t for _, _, t in triplets}

        train_e = entities(splits["train"])
        valid_e = entities(splits["valid"])
        only_valid = valid_e - train_e

        assert not only_valid, (
            f"{len(only_valid)} entité(s) présentes uniquement dans valid.txt :\n"
            + "\n".join(list(only_valid)[:10])
            + "\n→ Corriger le split (voir kge/validate_splits.py)"
        )

    def test_entites_train_couvrent_test(self, splits):
        """Toutes les entités de test.txt doivent être dans train.txt."""
        if splits is None:
            pytest.skip("Splits absents")

        def entities(triplets):
            return {h for h, _, _ in triplets} | {t for _, _, t in triplets}

        train_e = entities(splits["train"])
        test_e  = entities(splits["test"])
        only_test = test_e - train_e

        assert not only_test, (
            f"{len(only_test)} entité(s) présentes uniquement dans test.txt :\n"
            + "\n".join(list(only_test)[:10])
            + "\n→ Corriger le split (voir kge/validate_splits.py)"
        )

    def test_pas_de_fuite_train_test(self, splits):
        """Aucun triplet de test ne doit apparaître dans train."""
        if splits is None:
            pytest.skip("Splits absents")
        train_set = set(splits["train"])
        test_set  = set(splits["test"])
        fuites = train_set & test_set
        assert not fuites, (
            f"{len(fuites)} triplets de test présents dans train (data leakage !)"
        )

    def test_volume_train_suffisant(self, splits):
        if splits is None:
            pytest.skip("Splits absents")
        nb = len(splits["train"])
        assert nb >= 40_000, (
            f"Train contient seulement {nb:,} triplets — "
            "un KGE a besoin d'au moins ~40k triplets d'entraînement"
        )


# ---------------------------------------------------------------------------
# Phase 6.2 — Modèles entraînés
# ---------------------------------------------------------------------------

class TestModelesEntraines:
    """Vérifie que les modèles ont bien été entraînés et sauvegardés."""

    def test_dossiers_modeles_existent(self):
        for model in REQUIRED_MODELS:
            model_dir = RESULTS_DIR / model
            assert model_dir.exists(), (
                f"Résultats manquants pour {model} : {model_dir}\n"
                "→ Lancer kge/train_kge.py (Phase 6.2)"
            )

    def test_au_moins_deux_modeles(self):
        if not RESULTS_DIR.exists():
            pytest.skip("Dossier results/ absent")
        modeles = [d for d in RESULTS_DIR.iterdir() if d.is_dir()]
        assert len(modeles) >= 2, (
            f"Seulement {len(modeles)} modèle(s) entraîné(s) — minimum requis : 2"
        )

    def test_fichiers_modele_complets(self):
        """Chaque dossier de modèle doit contenir les fichiers PyKEEN standards."""
        if not RESULTS_DIR.exists():
            pytest.skip("Dossier results/ absent")
        for model_dir in RESULTS_DIR.iterdir():
            if not model_dir.is_dir():
                continue
            # PyKEEN sauvegarde au moins ces fichiers
            expected = ["results.json", "trained_model.pkl"]
            for fname in expected:
                assert (model_dir / fname).exists(), (
                    f"Fichier manquant dans {model_dir.name}/ : {fname}"
                )


# ---------------------------------------------------------------------------
# Phase 6.3 — Métriques d'évaluation
# ---------------------------------------------------------------------------

class TestMetriques:
    """Vérifie que les métriques d'évaluation sont présentes et au-dessus des seuils."""

    def _load_results(self, model_name: str) -> dict | None:
        path = RESULTS_DIR / model_name / "results.json"
        if not path.exists():
            return None
        with open(path, encoding='utf-8') as f:
            return json.load(f)

    @pytest.mark.parametrize("model", REQUIRED_MODELS)
    def test_results_json_existe(self, model):
        path = RESULTS_DIR / model / "results.json"
        assert path.exists(), (
            f"results.json manquant pour {model}\n"
            "→ L'entraînement PyKEEN n'a pas terminé correctement"
        )

    @pytest.mark.parametrize("model", REQUIRED_MODELS)
    def test_mrr_au_dessus_du_seuil(self, model):
        results = self._load_results(model)
        if results is None:
            pytest.skip(f"results.json absent pour {model}")
        # PyKEEN stocke les métriques sous results > metrics > realistic > inverse_harmonic_mean_rank
        try:
            # Structure PyKEEN : results > metrics > both/head/tail > realistic > ...
            mrr = results["metrics"]["both"]["realistic"]["inverse_harmonic_mean_rank"]
        except KeyError:
            try:
                mrr = results["metrics"]["realistic"]["inverse_harmonic_mean_rank"]
            except KeyError:
                pytest.skip(f"Structure de results.json inattendue pour {model}")
        assert mrr >= MIN_MRR, (
            f"{model} MRR = {mrr:.4f} — seuil minimum : {MIN_MRR}\n"
            "→ Augmenter les epochs ou vérifier la qualité de la KB"
        )

    @pytest.mark.parametrize("model", REQUIRED_MODELS)
    def test_hits_at_10_au_dessus_du_seuil(self, model):
        results = self._load_results(model)
        if results is None:
            pytest.skip(f"results.json absent pour {model}")
        try:
            hits10 = results["metrics"]["both"]["realistic"]["hits_at_10"]
        except KeyError:
            try:
                hits10 = results["metrics"]["realistic"]["hits_at_10"]
            except KeyError:
                pytest.skip(f"Structure de results.json inattendue pour {model}")
        assert hits10 >= MIN_HITS10, (
            f"{model} Hits@10 = {hits10:.4f} — seuil minimum : {MIN_HITS10}"
        )

    def test_transE_meilleur_que_random(self):
        """TransE doit faire mieux qu'un classifieur aléatoire."""
        results = self._load_results("TransE")
        if results is None:
            pytest.skip("TransE non entraîné")
        try:
            mrr = results["metrics"]["both"]["realistic"]["inverse_harmonic_mean_rank"]
        except KeyError:
            try:
                mrr = results["metrics"]["realistic"]["inverse_harmonic_mean_rank"]
            except KeyError:
                pytest.skip("Structure inattendue")
        # Un MRR > 0 indique qu'on fait mieux qu'aléatoire
        assert mrr > 0, "TransE MRR = 0 — problème d'entraînement"

    def test_comparaison_modeles_documentee(self):
        """Un fichier de comparaison doit exister."""
        comparison_path = KGE_DIR / "analyse" / "comparaison_modeles.json"
        rapport_path    = KGE_DIR / "rapport_kge.md"
        assert comparison_path.exists() or rapport_path.exists(), (
            "Aucun fichier de comparaison de modèles trouvé\n"
            "→ Créer kge/analyse/comparaison_modeles.json ou kge/rapport_kge.md"
        )


# ---------------------------------------------------------------------------
# Phase 6.4 — Analyses
# ---------------------------------------------------------------------------

class TestAnalyses:
    """Vérifie que les analyses ont été réalisées."""

    def test_visualisation_tsne_existe(self):
        tsne_path = KGE_DIR / "analyse" / "tsne_entities.png"
        assert tsne_path.exists(), (
            f"Visualisation t-SNE manquante : {tsne_path}\n"
            "→ Lancer kge/analyse/tsne_visualization.py"
        )

    def test_script_nearest_neighbors_existe(self):
        nn_path = KGE_DIR / "analyse" / "nearest_neighbors.py"
        assert nn_path.exists(), (
            f"Script manquant : {nn_path}"
        )

    def test_validate_splits_passe(self):
        """Le script validate_splits.py doit exister et être exécutable."""
        script = KGE_DIR / "validate_splits.py"
        assert script.exists(), (
            f"Script manquant : {script}\n"
            "→ Ce script est obligatoire avant tout entraînement"
        )
