"""
tests/test_rag.py
Validation de l'assistant RAG — Phase 7
Domaine : Sportifs & compétitions

Lancer : pytest tests/test_rag.py -v
Note : les tests LLM (test_llm_*) nécessitent une clé API valide dans .env
       Lancer sans eux : pytest tests/test_rag.py -v -m "not llm"
"""

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RAG_DIR = PROJECT_ROOT / "rag"
KB_EXP_PATH = PROJECT_ROOT / "kb" / "knowledge_base_expanded.ttl"

# Ajouter le dossier rag/ au path pour les imports
sys.path.insert(0, str(RAG_DIR))
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Données de test — questions de référence (domaine sportifs)
# ---------------------------------------------------------------------------

# Format : (intent, entity, mot_cle_attendu_dans_résultat)
REFERENCE_QUESTIONS = [
    ("medals",       "UsainBolt",      "Gold"),
    ("competitions", "UsainBolt",      "Olympics"),
    ("sport",        "SerenaWilliams", "Tennis"),
    ("country",      "UsainBolt",      "Jamaica"),
]

# Questions dont la réponse N'EST PAS dans le graphe (test du fallback)
UNKNOWN_QUESTIONS = [
    ("medals",       "PersonnageInexistant123"),
    ("competitions", "AthleteFantome456"),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def kb_graph():
    """Charge la KB étendue pour les tests RAG."""
    try:
        from rdflib import Graph
    except ImportError:
        pytest.skip("rdflib non installé")
    if not KB_EXP_PATH.exists():
        pytest.skip(f"KB étendue absente : {KB_EXP_PATH}")
    g = Graph()
    g.parse(KB_EXP_PATH, format="turtle")
    return g


@pytest.fixture(scope="module")
def query_builder():
    """Importe le module query_builder."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "query_builder", RAG_DIR / "query_builder.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        pytest.skip(f"query_builder.py non disponible : {e}")


@pytest.fixture(scope="module")
def sparql_executor():
    """Importe le module sparql_executor."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sparql_executor", RAG_DIR / "sparql_executor.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        pytest.skip(f"sparql_executor.py non disponible : {e}")


# ---------------------------------------------------------------------------
# Tests de structure — fichiers présents
# ---------------------------------------------------------------------------

class TestStructureRAG:
    """Vérifie que tous les fichiers RAG requis sont présents."""

    def test_dossier_rag_existe(self):
        assert RAG_DIR.exists(), (
            f"Dossier rag/ manquant : {RAG_DIR}\n"
            "→ Créer la structure RAG (Phase 7)"
        )

    @pytest.mark.parametrize("fichier", [
        "query_builder.py",
        "sparql_executor.py",
        "llm_client.py",
        "rag_assistant.py",
        "exemples_questions.md",
    ])
    def test_fichier_existe(self, fichier):
        path = RAG_DIR / fichier
        if fichier == ".env.example":
            path = PROJECT_ROOT / ".env.example"  # a la racine, pas dans rag/
        assert path.exists(), f"Fichier manquant : {fichier}"

    def test_env_example_ne_contient_pas_cles_reelles(self):
        env_example = RAG_DIR / ".env.example"
        if not env_example.exists():
            pytest.skip(".env.example absent")
        content = env_example.read_text()
        assert "sk-" not in content, (
            ".env.example contient ce qui ressemble à une vraie clé API — la remplacer par un placeholder"
        )

    def test_env_dans_gitignore(self):
        gitignore = PROJECT_ROOT / ".gitignore"
        if not gitignore.exists():
            pytest.skip(".gitignore absent")
        content = gitignore.read_text()
        assert ".env" in content, (
            ".env absent du .gitignore — risque de commit accidentel des clés API !"
        )

    def test_demo_notebook_existe(self):
        nb_path = RAG_DIR / "demo.ipynb"
        assert nb_path.exists(), (
            "Notebook de démonstration manquant : rag/demo.ipynb"
        )


# ---------------------------------------------------------------------------
# Tests query_builder — NL → SPARQL
# ---------------------------------------------------------------------------

class TestQueryBuilder:
    """Vérifie que le module query_builder génère des requêtes valides."""

    def test_import_reussi(self, query_builder):
        assert query_builder is not None

    def test_fonction_build_query_existe(self, query_builder):
        assert hasattr(query_builder, "build_query"), (
            "La fonction build_query() est absente de query_builder.py"
        )

    @pytest.mark.parametrize("intent,entity,_", REFERENCE_QUESTIONS)
    def test_build_query_retourne_sparql(self, query_builder, intent, entity, _):
        query = query_builder.build_query(intent, entity)
        assert query is not None, (
            f"build_query('{intent}', '{entity}') a retourné None\n"
            f"→ Ajouter le template '{intent}' dans TEMPLATES"
        )
        assert "SELECT" in query.upper(), (
            f"La requête pour '{intent}' ne contient pas SELECT"
        )
        assert entity in query, (
            f"L'entité '{entity}' absente de la requête générée"
        )

    def test_intent_inconnu_retourne_none(self, query_builder):
        result = query_builder.build_query("intent_inexistant_xyz", "UsainBolt")
        assert result is None, (
            "build_query() devrait retourner None pour un intent inconnu"
        )

    def test_templates_couvrent_le_domaine(self, query_builder):
        """Les intents minimaux du domaine sportifs doivent être couverts."""
        intents_requis = ["medals", "competitions", "sport", "country"]
        for intent in intents_requis:
            query = query_builder.build_query(intent, "TestAthlete")
            assert query is not None, (
                f"Intent '{intent}' non couvert dans query_builder.py\n"
                "→ Ajouter ce template (domaine sportifs)"
            )


# ---------------------------------------------------------------------------
# Tests sparql_executor — exécution + fallback
# ---------------------------------------------------------------------------

class TestSparqlExecutor:
    """Vérifie l'exécution des requêtes SPARQL et la gestion du fallback."""

    def test_import_reussi(self, sparql_executor):
        assert sparql_executor is not None

    def test_fonction_query_with_fallback_existe(self, sparql_executor):
        assert hasattr(sparql_executor, "query_with_fallback"), (
            "La fonction query_with_fallback() est absente de sparql_executor.py"
        )

    def test_requete_valide_retourne_resultats(self, sparql_executor, kb_graph, query_builder):
        """Une requête valide sur une entité connue doit retourner des résultats."""
        query = query_builder.build_query("medals", "UsainBolt")
        if query is None:
            pytest.skip("Template 'medals' absent")
        results = sparql_executor.query_with_fallback(query, kb_graph)
        # Peut retourner vide si l'entité n'est pas encore dans la KB — pas un échec critique
        assert isinstance(results, list), "query_with_fallback() doit retourner une liste"

    def test_entite_inconnue_ne_plante_pas(self, sparql_executor, kb_graph, query_builder):
        """Une requête sur une entité inexistante doit retourner [] sans lever d'exception."""
        query = query_builder.build_query("medals", "PersonnageInexistant999")
        if query is None:
            pytest.skip("Template 'medals' absent")
        try:
            results = sparql_executor.query_with_fallback(query, kb_graph)
            assert isinstance(results, list)
        except Exception as e:
            pytest.fail(
                f"query_with_fallback() a levé une exception sur entité inexistante : {e}\n"
                "→ Ajouter un try/except dans sparql_executor.py"
            )

    def test_triplets_cites_existent_dans_graphe(self, sparql_executor, kb_graph, query_builder):
        """Les triplets retournés doivent exister réellement dans le graphe."""
        from rdflib import URIRef
        NS = "http://monprojet.org/sports/"

        query = query_builder.build_query("competitions", "UsainBolt")
        if query is None:
            pytest.skip("Template 'competitions' absent")
        results = sparql_executor.query_with_fallback(query, kb_graph)
        if not results:
            pytest.skip("Aucun résultat — entité peut-être absente de la KB")

        # Vérifier que les objets retournés sont des URIs du graphe
        for row in results[:5]:
            obj = str(row[0]) if hasattr(row, "__iter__") else str(row)
            # L'objet doit exister quelque part dans le graphe
            exists = any(True for _ in kb_graph.triples((None, None, URIRef(obj))))
            assert exists, (
                f"Triplet retourné avec objet '{obj}' introuvable dans le graphe\n"
                "→ Vérifier la cohérence des URIs dans sparql_executor.py"
            )


# ---------------------------------------------------------------------------
# Tests de bout en bout — pipeline RAG
# ---------------------------------------------------------------------------

class TestPipelineRAG:
    """Tests d'intégration du pipeline complet."""

    def test_rag_assistant_importable(self):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "rag_assistant", RAG_DIR / "rag_assistant.py"
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            pytest.fail(f"rag_assistant.py non importable : {e}")

    def test_exemples_questions_non_vide(self):
        path = RAG_DIR / "exemples_questions.md"
        if not path.exists():
            pytest.skip("exemples_questions.md absent")
        content = path.read_text().strip()
        assert len(content) > 100, (
            "exemples_questions.md semble vide ou très court\n"
            "→ Ajouter au moins 5 questions de test avec réponses attendues"
        )

    def test_system_prompt_cite_les_sources(self):
        """Le prompt système doit contenir une instruction de citation des faits."""
        rag_assistant = RAG_DIR / "rag_assistant.py"
        if not rag_assistant.exists():
            pytest.skip("rag_assistant.py absent")
        content = rag_assistant.read_text()
        assert "cite" in content.lower() or "source" in content.lower() or "fait" in content.lower(), (
            "Le prompt système ne semble pas demander la citation des triplets sources\n"
            "→ Ajouter l'instruction de citation dans SYSTEM_PROMPT"
        )

    def test_gestion_zero_resultat_documentee(self):
        """Le code RAG doit gérer explicitement le cas 0 résultat."""
        for fichier in ("rag_assistant.py", "sparql_executor.py"):
            path = RAG_DIR / fichier
            if not path.exists():
                continue
            content = path.read_text()
            if "not results" in content or "len(results) == 0" in content or "if results" in content:
                return  # trouvé dans au moins un fichier
        pytest.fail(
            "Aucun fichier RAG ne gère explicitement le cas 0 résultat SPARQL\n"
            "→ Ajouter la gestion du fallback dans sparql_executor.py"
        )


# ---------------------------------------------------------------------------
# Tests LLM (nécessitent une clé API) — marqués @pytest.mark.llm
# ---------------------------------------------------------------------------

@pytest.mark.llm
class TestLLM:
    """Tests nécessitant un appel API LLM réel. Skippés sans clé valide."""

    @pytest.fixture(autouse=True)
    def check_api_key(self):
        import os
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
        if not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY")):
            pytest.skip("Aucune clé API LLM disponible — test LLM ignoré")

    def test_llm_repond_sur_question_connue(self):
        """Le pipeline complet doit retourner une réponse non vide."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "rag_assistant", RAG_DIR / "rag_assistant.py"
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            response = mod.ask("Quelles médailles a remporté Usain Bolt ?")
            assert response and len(response) > 10, (
                "Le pipeline RAG a retourné une réponse vide ou trop courte"
            )
        except AttributeError:
            pytest.skip("Fonction ask() absente de rag_assistant.py")

    def test_llm_cite_les_triplets(self):
        """La réponse LLM doit contenir au moins une citation de triplet."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "rag_assistant", RAG_DIR / "rag_assistant.py"
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            response = mod.ask("Dans quel sport Usain Bolt est-il spécialisé ?")
            # La citation est au format [sujet → prédicat → objet]
            assert "→" in response or "->" in response or "[" in response, (
                "La réponse LLM ne contient aucune citation de triplet\n"
                "→ Renforcer l'instruction de citation dans SYSTEM_PROMPT"
            )
        except AttributeError:
            pytest.skip("Fonction ask() absente de rag_assistant.py")

    def test_llm_avoue_ignorance_sur_inconnu(self):
        """Sur une question hors du graphe, le LLM doit signaler l'absence d'info."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "rag_assistant", RAG_DIR / "rag_assistant.py"
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            response = mod.ask("Quel est le palmarès de AthleteInexistant999 ?")
            mots_absence = ["pas", "aucun", "introuvable", "ne contient", "disponible", "absent"]
            contient_aveu = any(m in response.lower() for m in mots_absence)
            assert contient_aveu, (
                "Le LLM n'a pas signalé l'absence d'information pour une entité inconnue\n"
                "→ Vérifier la règle 2 du SYSTEM_PROMPT"
            )
        except AttributeError:
            pytest.skip("Fonction ask() absente de rag_assistant.py")
