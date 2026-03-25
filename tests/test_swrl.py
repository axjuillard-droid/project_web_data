"""
tests/test_swrl.py
Validation du raisonnement SWRL — Phase 5
Domaine : Sportifs & compétitions

Lancer : pytest tests/test_swrl.py -v
"""

import pytest
from pathlib import Path

PROJECT_ROOT    = Path(__file__).parent.parent
REASONING_DIR   = PROJECT_ROOT / "raisonnement"
KB_EXP_PATH     = PROJECT_ROOT / "kb" / "knowledge_base_expanded.ttl"
ONTO_OWL_PATH   = PROJECT_ROOT / "kb" / "knowledge_base_expanded.owl"


# ---------------------------------------------------------------------------
# Tests de structure
# ---------------------------------------------------------------------------

class TestStructureSWRL:

    @pytest.mark.parametrize("fichier", [
        "swrl_rules.py",
        "resultats_swrl.txt",
        "rapport_swrl.md",
    ])
    def test_fichier_existe(self, fichier):
        path = REASONING_DIR / fichier
        assert path.exists(), (
            f"Fichier manquant : raisonnement/{fichier}\n"
            "→ Créer ce fichier (Phase 5)"
        )

    def test_swrl_rules_importe_owlready2(self):
        path = REASONING_DIR / "swrl_rules.py"
        if not path.exists():
            pytest.skip("swrl_rules.py absent")
        content = path.read_text(encoding='utf-8')
        assert "owlready2" in content, (
            "swrl_rules.py n'importe pas owlready2\n"
            "→ Ajouter 'from owlready2 import ...'"
        )

    def test_pas_de_regles_family_owl_dans_projet(self):
        """Les règles family.owl (oldPerson, hasBrother) ne doivent pas être dans le code projet."""
        path = REASONING_DIR / "swrl_rules.py"
        if not path.exists():
            pytest.skip("swrl_rules.py absent")
        content = path.read_text(encoding='utf-8')
        assert "oldPerson" not in content, (
            "La règle 'oldPerson' (exercice family.owl) est présente dans swrl_rules.py\n"
            "→ Remplacer par les règles du domaine sportifs"
        )
        assert "hasBrother" not in content, (
            "La règle 'hasBrother' (exercice family.owl) est présente dans swrl_rules.py\n"
            "→ Remplacer par les règles du domaine sportifs"
        )

    def test_regles_domaine_sportifs_presentes(self):
        """Le code doit contenir au moins une règle liée au domaine sportifs."""
        path = REASONING_DIR / "swrl_rules.py"
        if not path.exists():
            pytest.skip("swrl_rules.py absent")
        content = path.read_text(encoding='utf-8')
        mots_cles_domaine = [
            "Athlete", "participatedIn", "wonMedal",
            "hasCompeted", "sameNationality", "multiMedalist",
            "represents", "Competition",
        ]
        trouve = any(m in content for m in mots_cles_domaine)
        assert trouve, (
            "Aucun terme du domaine sportifs trouvé dans swrl_rules.py\n"
            f"→ Utiliser au moins l'un de : {mots_cles_domaine}"
        )


# ---------------------------------------------------------------------------
# Tests sur les résultats SWRL
# ---------------------------------------------------------------------------

class TestResultatsSWRL:

    def test_resultats_non_vides(self):
        path = REASONING_DIR / "resultats_swrl.txt"
        if not path.exists():
            pytest.skip("resultats_swrl.txt absent")
        content = path.read_text(encoding='utf-8').strip()
        assert len(content) > 0, (
            "resultats_swrl.txt est vide — l'inférence n'a rien produit\n"
            "→ Vérifier la règle SWRL et l'ontologie chargée"
        )

    def test_resultats_contiennent_des_entites_sport(self):
        path = REASONING_DIR / "resultats_swrl.txt"
        if not path.exists():
            pytest.skip("resultats_swrl.txt absent")
        content = path.read_text(encoding='utf-8')
        # Les résultats doivent mentionner des termes liés au domaine
        assert any(
            kw in content for kw in ["Athlete", "athlete", "hasCompeted", "sameNationality",
                                      "multiMedalist", "Competition", "Medal"]
        ), (
            "Les résultats d'inférence ne semblent pas liés au domaine sportifs\n"
            "→ Vérifier que l'ontologie chargée est bien la KB du projet"
        )

    def test_rapport_swrl_documente_la_regle(self):
        path = REASONING_DIR / "rapport_swrl.md"
        if not path.exists():
            pytest.skip("rapport_swrl.md absent")
        content = path.read_text(encoding='utf-8')
        assert len(content) > 200, (
            "rapport_swrl.md trop court — documenter la règle, les prémisses et les résultats"
        )
        assert "SWRL" in content or "règle" in content.lower(), (
            "rapport_swrl.md ne mentionne pas la règle SWRL utilisée"
        )


# ---------------------------------------------------------------------------
# Tests sur la comparaison SWRL vs KGE
# ---------------------------------------------------------------------------

class TestComparaisonSWRLvsKGE:
    """Vérifie que la comparaison SWRL vs KGE a été réalisée (Phase 6.4)."""

    def test_comparaison_documentee_dans_rapport(self):
        rapport = REASONING_DIR / "rapport_swrl.md"
        if not rapport.exists():
            pytest.skip("rapport_swrl.md absent")
        content = rapport.read_text(encoding='utf-8').lower()
        mots_comparaison = ["embedding", "kge", "vecteur", "vector", "transE", "distmult"]
        trouve = any(m in content for m in mots_comparaison)
        assert trouve, (
            "Le rapport SWRL ne mentionne pas la comparaison avec les embeddings KGE\n"
            "→ Ajouter la section 'Comparaison SWRL vs KGE' (Phase 6.4)"
        )

    def test_regle_horn_identifiee_pour_comparaison(self):
        """La règle Horn utilisée pour la comparaison doit être explicitement nommée."""
        path = REASONING_DIR / "swrl_rules.py"
        if not path.exists():
            pytest.skip("swrl_rules.py absent")
        content = path.read_text(encoding='utf-8')
        # Chercher un commentaire indiquant la règle de comparaison
        assert "comparaison" in content.lower() or "comparison" in content.lower() or "kge" in content.lower(), (
            "La règle Horn à utiliser pour la comparaison SWRL vs KGE n'est pas identifiée\n"
            "→ Ajouter un commentaire '# Règle pour comparaison SWRL vs KGE' dans swrl_rules.py"
        )
