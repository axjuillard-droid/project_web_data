"""
tests/test_kb_validation.py
Validation de la Knowledge Base RDF — Phases 1 à 4
Domaine : Sportifs & compétitions

Lancer : pytest tests/test_kb_validation.py -v
"""

import pytest
from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, Literal
from rdflib.namespace import XSD

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent
KB_V1_PATH   = PROJECT_ROOT / "kb" / "knowledge_base_v1.ttl"
KB_EXP_PATH  = PROJECT_ROOT / "kb" / "knowledge_base_expanded.ttl"
ONTO_PATH    = PROJECT_ROOT / "kb" / "ontologie.owl"

NS = Namespace("http://monprojet.org/sports/")

# Seuils attendus
MIN_TRIPLETS_V1       = 100
MIN_ENTITIES_V1       = 50
MIN_TRIPLETS_EXPANDED = 50_000
MAX_TRIPLETS_EXPANDED = 200_000
MIN_ENTITIES_EXPANDED = 5_000
MAX_ENTITIES_EXPANDED = 30_000
MIN_RELATIONS_EXPANDED = 50
MAX_RELATIONS_EXPANDED = 200

# Classes obligatoires dans l'ontologie (domaine sportifs)
REQUIRED_CLASSES = [
    "Athlete", "Competition", "Sport", "Country", "Medal",
]

# Propriétés obligatoires dans l'ontologie
REQUIRED_PROPERTIES = [
    "participatedIn", "wonMedal", "represents", "practicesSport",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def graph_v1():
    """Charge la KB initiale (Phase 1)."""
    if not KB_V1_PATH.exists():
        pytest.skip(f"KB initiale introuvable : {KB_V1_PATH}")
    g = Graph()
    g.parse(KB_V1_PATH, format="turtle")
    return g


@pytest.fixture(scope="module")
def graph_expanded():
    """Charge la KB étendue (Phase 4)."""
    if not KB_EXP_PATH.exists():
        pytest.skip(f"KB étendue introuvable : {KB_EXP_PATH}")
    g = Graph()
    g.parse(KB_EXP_PATH, format="turtle")
    return g


@pytest.fixture(scope="module")
def graph_ontology():
    """Charge l'ontologie."""
    if not ONTO_PATH.exists():
        pytest.skip(f"Ontologie introuvable : {ONTO_PATH}")
    g = Graph()
    g.parse(ONTO_PATH, format="xml")
    return g


# ---------------------------------------------------------------------------
# Phase 1 — KB initiale
# ---------------------------------------------------------------------------

class TestKBInitiale:
    """Tests de base sur la KB initiale (≥ 100 triplets, ≥ 50 entités)."""

    def test_fichier_existe(self):
        assert KB_V1_PATH.exists(), (
            f"Fichier manquant : {KB_V1_PATH}\n"
            "→ Créer la KB initiale avec RDFLib (Phase 1)"
        )

    def test_volume_triplets(self, graph_v1):
        nb = len(graph_v1)
        assert nb >= MIN_TRIPLETS_V1, (
            f"Seulement {nb} triplets — minimum requis : {MIN_TRIPLETS_V1}"
        )

    def test_volume_entites(self, graph_v1):
        entites = set(graph_v1.subjects(RDF.type, None))
        nb = len(entites)
        assert nb >= MIN_ENTITIES_V1, (
            f"Seulement {nb} entités typées — minimum requis : {MIN_ENTITIES_V1}"
        )

    def test_pas_de_doublons(self, graph_v1):
        triplets = list(graph_v1)
        nb_total  = len(triplets)
        nb_unique = len(set(triplets))
        assert nb_total == nb_unique, (
            f"{nb_total - nb_unique} triplets dupliqués détectés"
        )

    def test_uris_valides(self, graph_v1):
        """Vérifie qu'aucun sujet ou objet-entité n'est une string brute."""
        for s, p, o in graph_v1:
            if isinstance(s, URIRef):
                assert str(s).startswith("http"), (
                    f"URI sujet malformée : {s}"
                )

    def test_predicats_camel_case(self, graph_v1):
        """Vérifie que les prédicats du namespace projet sont en camelCase."""
        ns_str = str(NS)
        for _, p, _ in graph_v1:
            local = str(p).replace(ns_str, "")
            if str(p).startswith(ns_str) and local:
                assert local[0].islower(), (
                    f"Prédicat '{local}' ne commence pas par une minuscule (camelCase attendu)"
                )

    def test_athletes_ont_un_sport(self, graph_v1):
        """Chaque entité de type Athlete doit pratiquer au moins un sport."""
        athletes = list(graph_v1.subjects(RDF.type, NS.Athlete))
        if not athletes:
            pytest.skip("Aucun Athlete trouvé — vérifier les types RDF")
        for a in athletes:
            sports = list(graph_v1.objects(a, NS.practicesSport))
            assert sports, f"Athlete {a} n'a pas de :practicesSport"

    def test_competitions_ont_une_annee(self, graph_v1):
        """Chaque Competition doit avoir une année."""
        competitions = list(graph_v1.subjects(RDF.type, NS.Competition))
        if not competitions:
            pytest.skip("Aucune Competition trouvée")
        for c in competitions:
            years = list(graph_v1.objects(c, NS.year))
            assert years, f"Competition {c} n'a pas de :year"


# ---------------------------------------------------------------------------
# Phase 2 — Alignement entités
# ---------------------------------------------------------------------------

class TestAlignementEntites:
    """Tests sur les alignements owl:sameAs (Phase 2)."""

    def test_au_moins_un_same_as(self, graph_v1):
        alignements = list(graph_v1.subject_objects(OWL.sameAs))
        assert len(alignements) > 0, (
            "Aucun triplet owl:sameAs trouvé — aligner les entités avec Wikidata (Phase 2)"
        )

    def test_same_as_pointe_vers_wikidata(self, graph_v1):
        """Les liens owl:sameAs doivent pointer vers wd: ou dbr:."""
        for s, o in graph_v1.subject_objects(OWL.sameAs):
            uri = str(o)
            assert (
                uri.startswith("http://www.wikidata.org/entity/")
                or uri.startswith("http://dbpedia.org/resource/")
            ), f"owl:sameAs pointe vers URI inconnue : {uri}"

    def test_taux_couverture_alignement(self, graph_v1):
        """Au moins 50% des entités principales doivent être alignées."""
        athletes = set(graph_v1.subjects(RDF.type, NS.Athlete))
        if not athletes:
            pytest.skip("Aucun Athlete — skip")
        alignes = set(graph_v1.subjects(OWL.sameAs, None))
        taux = len(athletes & alignes) / len(athletes)
        assert taux >= 0.5, (
            f"Seulement {taux:.0%} des athlètes sont alignés avec Wikidata — objectif : ≥ 50%"
        )

    def test_mapping_csv_existe(self):
        csv_path = PROJECT_ROOT / "alignement" / "mapping_entites.csv"
        assert csv_path.exists(), (
            f"Fichier manquant : {csv_path}\n"
            "→ Générer le tableau de mapping (Phase 2)"
        )


# ---------------------------------------------------------------------------
# Phase 3 — Alignement prédicats
# ---------------------------------------------------------------------------

class TestAlignementPredicats:
    """Tests sur les alignements de prédicats owl:equivalentProperty (Phase 3)."""

    def test_au_moins_un_equivalent_property(self, graph_v1):
        equiv = list(graph_v1.subject_objects(OWL.equivalentProperty))
        assert len(equiv) > 0, (
            "Aucun owl:equivalentProperty trouvé — aligner les prédicats (Phase 3)"
        )

    def test_mapping_predicats_csv_existe(self):
        csv_path = PROJECT_ROOT / "alignement" / "mapping_predicats.csv"
        assert csv_path.exists(), (
            f"Fichier manquant : {csv_path}"
        )

    def test_predicats_domaine_alignes(self, graph_v1):
        """Les prédicats clés du domaine doivent être alignés."""
        predicats_cles = ["wonMedal", "participatedIn", "represents"]
        for pred in predicats_cles:
            uri = NS[pred]
            equiv = list(graph_v1.objects(uri, OWL.equivalentProperty))
            sub   = list(graph_v1.objects(uri, RDFS.subPropertyOf))
            assert equiv or sub, (
                f"Prédicat :{pred} non aligné — ajouter owl:equivalentProperty ou rdfs:subPropertyOf"
            )


# ---------------------------------------------------------------------------
# Phase 4 — KB étendue
# ---------------------------------------------------------------------------

class TestKBEtendue:
    """Tests sur la KB après expansion SPARQL (Phase 4)."""

    def test_fichier_existe(self):
        assert KB_EXP_PATH.exists(), (
            f"Fichier manquant : {KB_EXP_PATH}\n"
            "→ Lancer le script d'expansion SPARQL (Phase 4)"
        )

    def test_volume_triplets_min(self, graph_expanded):
        nb = len(graph_expanded)
        assert nb >= MIN_TRIPLETS_EXPANDED, (
            f"{nb} triplets — minimum requis : {MIN_TRIPLETS_EXPANDED:,}"
        )

    def test_volume_triplets_max(self, graph_expanded):
        nb = len(graph_expanded)
        assert nb <= MAX_TRIPLETS_EXPANDED, (
            f"{nb} triplets — maximum pour laptop : {MAX_TRIPLETS_EXPANDED:,}"
        )

    def test_volume_entites(self, graph_expanded):
        entites = set(graph_expanded.subjects(RDF.type, None))
        nb = len(entites)
        assert MIN_ENTITIES_EXPANDED <= nb <= MAX_ENTITIES_EXPANDED, (
            f"{nb} entités — attendu entre {MIN_ENTITIES_EXPANDED:,} et {MAX_ENTITIES_EXPANDED:,}"
        )

    def test_volume_relations(self, graph_expanded):
        predicats = set(p for _, p, _ in graph_expanded if str(p).startswith(str(NS)))
        nb = len(predicats)
        assert MIN_RELATIONS_EXPANDED <= nb <= MAX_RELATIONS_EXPANDED, (
            f"{nb} relations — attendu entre {MIN_RELATIONS_EXPANDED} et {MAX_RELATIONS_EXPANDED}"
        )

    def test_connectivite_graphe(self, graph_expanded):
        """Vérifie qu'il n'y a pas d'entités isolées (sans aucune relation sortante)."""
        sujets = set(graph_expanded.subjects())
        nb_total = len(sujets)
        nb_isoles = sum(
            1 for s in sujets
            if len(list(graph_expanded.predicate_objects(s))) == 0
        )
        taux_isoles = nb_isoles / nb_total if nb_total else 0
        assert taux_isoles < 0.05, (
            f"{nb_isoles} entités isolées ({taux_isoles:.1%}) — trop de nœuds sans relation"
        )

    def test_stats_json_existe(self):
        stats_path = PROJECT_ROOT / "kb" / "stats_kb.json"
        assert stats_path.exists(), (
            f"Fichier manquant : {stats_path}\n"
            "→ Générer stats_kb.json après l'expansion"
        )

    def test_stats_json_coherent(self, graph_expanded):
        import json
        stats_path = PROJECT_ROOT / "kb" / "stats_kb.json"
        if not stats_path.exists():
            pytest.skip("stats_kb.json absent")
        with open(stats_path, encoding='utf-8') as f:
            stats = json.load(f)
        assert "nb_triplets" in stats, "Clé 'nb_triplets' manquante dans stats_kb.json"
        assert "nb_entities" in stats, "Clé 'nb_entities' manquante dans stats_kb.json"
        # Tolérance de 5% entre le JSON et le graphe chargé
        diff = abs(stats["nb_triplets"] - len(graph_expanded))
        assert diff / len(graph_expanded) < 0.05, (
            f"stats_kb.json ({stats['nb_triplets']}) incohérent avec le graphe réel ({len(graph_expanded)})"
        )


# ---------------------------------------------------------------------------
# Ontologie
# ---------------------------------------------------------------------------

class TestOntologie:
    """Tests sur la définition de l'ontologie (Phase 1)."""

    def test_fichier_existe(self):
        assert ONTO_PATH.exists(), f"Ontologie manquante : {ONTO_PATH}"

    def test_classes_requises_presentes(self, graph_ontology):
        for cls_name in REQUIRED_CLASSES:
            uri = NS[cls_name]
            types = list(graph_ontology.triples((uri, RDF.type, OWL.Class)))
            assert types, f"Classe :{cls_name} absente de l'ontologie"

    def test_proprietes_ont_domain_et_range(self, graph_ontology):
        for prop_name in REQUIRED_PROPERTIES:
            uri = NS[prop_name]
            domain = list(graph_ontology.objects(uri, RDFS.domain))
            range_ = list(graph_ontology.objects(uri, RDFS.range))
            assert domain, f":{prop_name} n'a pas de rdfs:domain"
            assert range_,  f":{prop_name} n'a pas de rdfs:range"
