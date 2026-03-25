"""
Phase 1 — Construction de la KB initiale (RDF)
===============================================
Ce script :
  1. Charge les entités issues de data/entités.csv
  2. Définit l'ontologie (classes, propriétés avec rdfs:domain et rdfs:range)
  3. Modélise les triplets RDF du domaine Sportifs & compétitions
  4. Exporte kb/knowledge_base_v1.ttl et kb/ontologie.owl
  5. Affiche les statistiques de la KB

Usage :
    python src/kg/script_construction.py

Prérequis :
    - data/entités.csv doit exister (Phase 0)
    - pip install rdflib
"""

import csv
import json
from pathlib import Path
from rdflib import (
    Graph, Namespace, URIRef, Literal, BNode,
    RDF, RDFS, OWL, XSD
)
from rdflib.namespace import NamespaceManager

# ─── Chemins ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DATA_DIR   = Path(__file__).parent.parent.parent / "data"
ENTITES_CSV = DATA_DIR / "entités.csv"
TTL_V1     = Path(__file__).parent.parent.parent / "kg_artifacts" / "knowledge_base_v1.ttl"
OWL_FILE   = Path(__file__).parent.parent.parent / "kg_artifacts" / "ontology.ttl"
STATS_FILE = Path(__file__).parent.parent.parent / "kg_artifacts" / "stats_kb.json"

# ─── Namespaces ──────────────────────────────────────────────────────────────
NS   = Namespace("http://monprojet.org/sports/")
WD   = Namespace("http://www.wikidata.org/entity/")

# Données enrichies manuellement pour les seeds connus
# Format : {entity_id: {"participations": [...], "medals": [...], "team": ...}}
DONNEES_ENRICHIES = {
    "UsainBolt": {
        "participations": ["OlympicsBeijing2008", "OlympicsLondon2012", "OlympicsRioDeJaneiro2016"],
        "medals": ["GoldMedal"],
        "sport": "Athletics",
        "nationality": "Jamaica",
    },
    "SerenaWilliams": {
        "participations": ["Wimbledon2012", "Wimbledon2015", "Wimbledon2016",
                           "USOpen2012", "USOpen2014", "AustralianOpen2015"],
        "medals": ["GoldMedal"],
        "sport": "Tennis",
        "nationality": "UnitedStates",
    },
    "LionelMessi": {
        "participations": ["FIFAWorldCup2006", "FIFAWorldCup2010", "FIFAWorldCup2014",
                           "FIFAWorldCup2018", "FIFAWorldCup2022"],
        "medals": ["GoldMedal"],
        "team": "ArgentinaFootballTeam",
        "sport": "Football",
        "nationality": "Argentina",
    },
    "MichaelPhelps": {
        "participations": ["OlympicsAthens2004", "OlympicsBeijing2008",
                           "OlympicsLondon2012", "OlympicsRioDeJaneiro2016"],
        "medals": ["GoldMedal"],
        "sport": "Swimming",
        "nationality": "UnitedStates",
    },
    "SimoneBiles": {
        "participations": ["OlympicsRioDeJaneiro2016", "OlympicsTokyo2020",
                           "OlympicsParis2024"],
        "medals": ["GoldMedal", "SilverMedal"],
        "sport": "Gymnastics",
        "nationality": "UnitedStates",
    },
    "RogerFederer": {
        "participations": ["Wimbledon2003", "Wimbledon2004", "Wimbledon2012",
                           "AustralianOpen2004", "USOpen2004"],
        "medals": ["GoldMedal"],
        "sport": "Tennis",
        "nationality": "Switzerland",
    },
    "RafaelNadal": {
        "participations": ["RolandGarros2005", "RolandGarros2010", "RolandGarros2022",
                           "AustralianOpen2009", "USOpen2010"],
        "medals": ["GoldMedal"],
        "sport": "Tennis",
        "nationality": "Spain",
    },
    "NovakDjokovic": {
        "participations": ["AustralianOpen2008", "AustralianOpen2019", "Wimbledon2014",
                           "USOpen2015", "RolandGarros2016"],
        "medals": ["GoldMedal"],
        "sport": "Tennis",
        "nationality": "Serbia",
    },
    "EliudKipchoge": {
        "participations": ["OlympicsRioDeJaneiro2016", "OlympicsTokyo2020",
                           "OlympicsParis2024", "BerlinMarathon2018"],
        "medals": ["GoldMedal"],
        "sport": "Athletics",
        "nationality": "Kenya",
    },
    "CristianoRonaldo": {
        "participations": ["FIFAWorldCup2006", "FIFAWorldCup2010", "FIFAWorldCup2014",
                           "FIFAWorldCup2018", "FIFAWorldCup2022"],
        "medals": ["GoldMedal"],
        "team": "PortugalFootballTeam",
        "sport": "Football",
        "nationality": "Portugal",
    },
    "KylianMbappe": {
        "participations": ["FIFAWorldCup2018", "FIFAWorldCup2022", "OlympicsParis2024"],
        "medals": ["GoldMedal", "SilverMedal"],
        "team": "FranceFootballTeam",
        "sport": "Football",
        "nationality": "France",
    },
    "LeBronJames": {
        "participations": ["OlympicsAthens2004", "OlympicsBeijing2008", "OlympicsLondon2012"],
        "medals": ["GoldMedal", "BronzeMedal"],
        "team": "USABasketballTeam",
        "sport": "Basketball",
        "nationality": "UnitedStates",
    },
    "MoFarah": {
        "participations": ["OlympicsLondon2012", "OlympicsRioDeJaneiro2016",
                           "WorldAthleticsChampionships2013"],
        "medals": ["GoldMedal"],
        "sport": "Athletics",
        "nationality": "UnitedKingdom",
    },
    "AdilGaliakhmetov": {
        "participations": ["OlympicsBeijing2008"],
        "sport": "ShortTrackSpeedSkating", # En supposant ce sport, ou un autre du domaine
        "nationality": "Kazakhstan",
    },
}

# Compétitions enrichies manuellement
COMPETITIONS_ENRICHIES = {
    "OlympicsBeijing2008":          ("Competition", 2008, "Beijing",   "China"),
    "OlympicsLondon2012":           ("Competition", 2012, "London",    "UnitedKingdom"),
    "OlympicsRioDeJaneiro2016":     ("Competition", 2016, "Rio de Janeiro", "Brazil"),
    "OlympicsTokyo2020":            ("Competition", 2021, "Tokyo",     "Japan"),
    "OlympicsParis2024":            ("Competition", 2024, "Paris",     "France"),
    "OlympicsAthens2004":           ("Competition", 2004, "Athens",    "Greece"),
    "FIFAWorldCup2022":             ("Competition", 2022, "Doha",      "Qatar"),
    "FIFAWorldCup2018":             ("Competition", 2018, "Moscow",    "Russia"),
    "FIFAWorldCup2014":             ("Competition", 2014, "Brasilia",  "Brazil"),
    "FIFAWorldCup2010":             ("Competition", 2010, "Cape Town", "SouthAfrica"),
    "FIFAWorldCup2006":             ("Competition", 2006, "Berlin",    "Germany"),
    "Wimbledon2003":                ("Competition", 2003, "London",    "UnitedKingdom"),
    "Wimbledon2004":                ("Competition", 2004, "London",    "UnitedKingdom"),
    "Wimbledon2012":                ("Competition", 2012, "London",    "UnitedKingdom"),
    "Wimbledon2014":                ("Competition", 2014, "London",    "UnitedKingdom"),
    "Wimbledon2015":                ("Competition", 2015, "London",    "UnitedKingdom"),
    "Wimbledon2016":                ("Competition", 2016, "London",    "UnitedKingdom"),
    "RolandGarros2005":             ("Competition", 2005, "Paris",     "France"),
    "RolandGarros2010":             ("Competition", 2010, "Paris",     "France"),
    "RolandGarros2016":             ("Competition", 2016, "Paris",     "France"),
    "RolandGarros2022":             ("Competition", 2022, "Paris",     "France"),
    "AustralianOpen2004":           ("Competition", 2004, "Melbourne", "Australia"),
    "AustralianOpen2008":           ("Competition", 2008, "Melbourne", "Australia"),
    "AustralianOpen2009":           ("Competition", 2009, "Melbourne", "Australia"),
    "AustralianOpen2015":           ("Competition", 2015, "Melbourne", "Australia"),
    "AustralianOpen2019":           ("Competition", 2019, "Melbourne", "Australia"),
    "USOpen2004":                   ("Competition", 2004, "New York",  "UnitedStates"),
    "USOpen2010":                   ("Competition", 2010, "New York",  "UnitedStates"),
    "USOpen2012":                   ("Competition", 2012, "New York",  "UnitedStates"),
    "USOpen2014":                   ("Competition", 2014, "New York",  "UnitedStates"),
    "USOpen2015":                   ("Competition", 2015, "New York",  "UnitedStates"),
    "WorldAthleticsChampionships2013": ("Competition", 2013, "Moscow", "Russia"),
    "BerlinMarathon2018":           ("Competition", 2018, "Berlin",    "Germany"),
    "2008SummerOlympics":           ("Competition", 2008, "Beijing",   "China"),
}

# Sports
SPORTS = [
    "Athletics", "Tennis", "Football", "Swimming", "Gymnastics",
    "Basketball", "Boxing", "Golf", "Cycling", "Fencing",
]

# Pays
PAYS = [
    "Jamaica", "UnitedStates", "Argentina", "Switzerland", "Spain",
    "Serbia", "France", "Brazil", "Portugal", "Kenya", "China",
    "UnitedKingdom", "Germany", "Russia", "Qatar", "Japan",
    "Italy", "Greece", "SouthAfrica", "Australia", "Romania",
]

# Types de médailles
MEDALS = ["GoldMedal", "SilverMedal", "BronzeMedal"]

# Équipes
TEAMS = [
    "ArgentinaFootballTeam", "PortugalFootballTeam", "FranceFootballTeam",
    "USABasketballTeam", "BrazilFootballTeam", "GermanyFootballTeam",
]


def creer_graphe() -> Graph:
    """Crée et retourne un graphe RDF configuré avec les namespaces."""
    g = Graph()
    g.bind("", NS)
    g.bind("wd", WD)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    g.bind("xsd", XSD)
    return g


def definir_ontologie(g: Graph) -> None:
    """Définit les classes et propriétés OWL de l'ontologie."""

    # ── Déclaration de l'ontologie ────────────────────────────────────────────
    ontologie_uri = URIRef("http://monprojet.org/sports/ontologie")
    g.add((ontologie_uri, RDF.type, OWL.Ontology))
    g.add((ontologie_uri, RDFS.label, Literal("Sports & Competitions Ontology", lang="en")))
    g.add((ontologie_uri, RDFS.comment,
           Literal("Ontologie pour les sportifs, compétitions, disciplines et palmarès.", lang="fr")))

    # ── Classes ────────────────────────────────────────────────────────────────
    classes = {
        "Person":      "Être humain (classe parente)",
        "Athlete":     "Sportif ou sportive de compétition",
        "Competition": "Événement sportif (JO, Coupe du Monde, tournoi…)",
        "Sport":       "Discipline sportive",
        "Team":        "Équipe sportive nationale ou de club",
        "Country":     "Pays ou nation",
        "Medal":       "Médaille (or, argent, bronze)",
        "Award":       "Récompense ou titre sportif (non-médaille)",
        "City":        "Ville hôte d'une compétition",
    }
    for nom_classe, description in classes.items():
        uri = NS[nom_classe]
        g.add((uri, RDF.type, OWL.Class))
        g.add((uri, RDFS.label, Literal(nom_classe, lang="en")))
        g.add((uri, RDFS.comment, Literal(description, lang="fr")))

    # Athlete est une sous-classe de Person
    g.add((NS.Athlete, RDFS.subClassOf, NS.Person))

    # Sous-classes de Medal
    for m in MEDALS:
        uri = NS[m]
        g.add((uri, RDF.type, OWL.Class))
        g.add((uri, RDFS.subClassOf, NS.Medal))
        g.add((uri, RDFS.label, Literal(m, lang="en")))

    # ── Propriétés d'objet (ObjectProperty) ───────────────────────────────────
    proprietes_objet = [
        # (nom, domaine, range, commentaire)
        ("participatedIn",  "Athlete",      "Competition", "L'athlète a participé à cette compétition"),
        ("wonMedal",        "Athlete",      "Medal",       "L'athlète a remporté cette médaille"),
        ("represents",      "Athlete",      "Country",     "L'athlète représente ce pays"),
        ("practicesSport",  "Athlete",      "Sport",       "L'athlète pratique ce sport"),
        ("memberOfTeam",    "Athlete",      "Team",        "L'athlète est membre de cette équipe"),
        ("hasCompeted",     "Athlete",      "Athlete",     "L'athlète a concouru contre cet autre athlète (inféré SWRL)"),
        ("sameNationality", "Athlete",      "Athlete",     "Les deux athlètes représentent le même pays (inféré SWRL)"),
        ("multiMedalist",   "Athlete",      "Medal",       "L'athlète a remporté plusieurs types de médailles (inféré SWRL)"),
        ("hostedBy",        "Competition",  "Country",     "La compétition est organisée par ce pays"),
        ("locatedIn",       "Competition",  "City",        "La compétition se déroule dans cette ville"),
        ("teamRepresents",  "Team",         "Country",     "L'équipe représente ce pays"),
    ]
    for nom_prop, domaine, range_, commentaire in proprietes_objet:
        uri = NS[nom_prop]
        g.add((uri, RDF.type, OWL.ObjectProperty))
        g.add((uri, RDFS.domain, NS[domaine]))
        g.add((uri, RDFS.range, NS[range_]))
        g.add((uri, RDFS.label, Literal(nom_prop, lang="en")))
        g.add((uri, RDFS.comment, Literal(commentaire, lang="fr")))

    # ── Propriétés de données (DatatypeProperty) ──────────────────────────────
    proprietes_donnees = [
        ("year",       "Competition", XSD.integer, "Année de la compétition"),
        ("birthYear",  "Athlete",     XSD.integer, "Année de naissance de l'athlète"),
        ("fullName",   "Person",      XSD.string,  "Nom complet"),
    ]
    for nom_prop, domaine, type_xsd, commentaire in proprietes_donnees:
        uri = NS[nom_prop]
        g.add((uri, RDF.type, OWL.DatatypeProperty))
        g.add((uri, RDFS.domain, NS[domaine]))
        g.add((uri, RDFS.range, type_xsd))
        g.add((uri, RDFS.label, Literal(nom_prop, lang="en")))
        g.add((uri, RDFS.comment, Literal(commentaire, lang="fr")))

    # ── Alignements owl:equivalentProperty avec Wikidata ─────────────────────
    alignements = [
        ("wonMedal",       "http://www.wikidata.org/prop/direct/P166"),  # award received
        ("participatedIn", "http://www.wikidata.org/prop/direct/P1344"), # participant in
        ("represents",     "http://www.wikidata.org/prop/direct/P27"),   # country of citizenship
        ("practicesSport", "http://www.wikidata.org/prop/direct/P641"),  # sport
        ("memberOfTeam",   "http://www.wikidata.org/prop/direct/P54"),   # member of sports team
    ]
    for prop_locale, prop_wikidata in alignements:
        g.add((NS[prop_locale], OWL.equivalentProperty, URIRef(prop_wikidata)))


def ajouter_instances(g: Graph) -> None:
    """Ajoute les instances (individus) au graphe RDF."""

    # ── Sports ────────────────────────────────────────────────────────────────
    for sport in SPORTS:
        uri = NS[sport]
        g.add((uri, RDF.type, NS.Sport))
        g.add((uri, RDFS.label, Literal(sport, lang="en")))

    # ── Pays ──────────────────────────────────────────────────────────────────
    for pays in PAYS:
        uri = NS[pays]
        g.add((uri, RDF.type, NS.Country))
        g.add((uri, RDFS.label, Literal(pays, lang="en")))

    # ── Médailles ─────────────────────────────────────────────────────────────
    for medal in MEDALS:
        uri = NS[medal]
        g.add((uri, RDF.type, NS[medal]))  # GoldMedal rdf:type GoldMedal
        g.add((uri, RDF.type, NS.Medal))
        g.add((uri, RDFS.label, Literal(medal.replace("Medal", " Medal"), lang="en")))

    # ── Équipes ───────────────────────────────────────────────────────────────
    for team in TEAMS:
        uri = NS[team]
        g.add((uri, RDF.type, NS.Team))
        g.add((uri, RDFS.label, Literal(team, lang="en")))
        # Lier l'équipe à son pays
        for pays in PAYS:
            if team.lower().startswith(pays.lower()):
                g.add((uri, NS.teamRepresents, NS[pays]))
                break

    # ── Compétitions ──────────────────────────────────────────────────────────
    for comp_id, (comp_type, annee, ville, pays) in COMPETITIONS_ENRICHIES.items():
        uri = NS[comp_id]
        g.add((uri, RDF.type, NS.Competition))
        g.add((uri, RDFS.label, Literal(comp_id, lang="en")))
        g.add((uri, NS.year, Literal(annee, datatype=XSD.integer)))
        g.add((uri, NS.hostedBy, NS[pays.replace(" ", "")]))
        # Ville
        ville_id = ville.replace(" ", "")
        ville_uri = NS[ville_id]
        g.add((ville_uri, RDF.type, NS.City))
        g.add((ville_uri, RDFS.label, Literal(ville, lang="en")))
        g.add((uri, NS.locatedIn, ville_uri))

    # ── Athlètes ──────────────────────────────────────────────────────────────
    for athlete_id, donnees in DONNEES_ENRICHIES.items():
        uri = NS[athlete_id]
        g.add((uri, RDF.type, NS.Athlete))
        g.add((uri, RDF.type, NS.Person))
        g.add((uri, RDFS.label, Literal(athlete_id, lang="en")))

        # Sport
        if "sport" in donnees:
            if donnees["sport"] in SPORTS:
                g.add((uri, NS.practicesSport, NS[donnees["sport"]]))

        # Nationalité
        if "nationality" in donnees:
            g.add((uri, NS.represents, NS[donnees["nationality"]]))

        # Participations
        for comp in donnees.get("participations", []):
            if comp in COMPETITIONS_ENRICHIES:
                g.add((uri, NS.participatedIn, NS[comp]))

        # Médailles
        for medal in donnees.get("medals", []):
            g.add((uri, NS.wonMedal, NS[medal]))

        # Équipe
        if "team" in donnees:
            g.add((uri, NS.memberOfTeam, NS[donnees["team"]]))


def ajouter_entites_csv(g: Graph, chemin_csv: Path) -> int:
    """
    Ajoute les entités du CSV (Phase 0) qui ne sont pas déjà dans le graphe.
    Retourne le nombre d'entités ajoutées.
    """
    if not chemin_csv.exists():
        print(f"  [INFO] {chemin_csv} non trouvé — ignorer les entités CSV")
        return 0
    compteur = 0
    with open(chemin_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entity_id = row.get("id", "")
            nom       = row.get("nom", "")
            type_     = row.get("type", "Athlete")
            wd_uri    = row.get("wikidata_uri", "")
            if not entity_id:
                continue
            uri = NS[entity_id]
            # Ne pas re-ajouter les entités déjà manuellement enrichies
            if (uri, RDF.type, None) in g:
                continue
            g.add((uri, RDF.type, NS[type_]))
            g.add((uri, RDF.type, NS.Person if type_ == "Athlete" else NS[type_]))
            if nom:
                g.add((uri, RDFS.label, Literal(nom, lang="en")))
            if wd_uri:
                g.add((uri, OWL.sameAs, URIRef(wd_uri)))
            # Propriétés spéciales
            sport = row.get("sport", "")
            if sport and sport in SPORTS:
                g.add((uri, NS.practicesSport, NS[sport]))
            pays = row.get("pays", "")
            if pays:
                pays_id = pays.replace(" ", "").replace(",", "")
                pays_uri = NS[pays_id]
                g.add((pays_uri, RDF.type, NS.Country))
                g.add((uri, NS.represents, pays_uri))
            compteur += 1
    return compteur


def calculer_stats(g: Graph) -> dict:
    """Calcule et retourne les statistiques de la KB."""
    # Compter les triplets (hors ax ontologiques)
    total_triplets = len(g)
    entites = set()
    relations = set()
    for s, p, o in g:
        if isinstance(s, URIRef):
            entites.add(str(s))
        if isinstance(p, URIRef):
            relations.add(str(p))
    return {
        "total_triplets": total_triplets,
        "nb_entites": len(entites),
        "nb_relations": len(relations),
    }


def main():
    print("=" * 60)
    print("Phase 1 — Construction de la KB initiale (RDF)")
    print("=" * 60)

    g = creer_graphe()

    print("\n[1/4] Définition de l'ontologie...")
    definir_ontologie(g)
    print(f"  → {len(g)} triplets après ontologie")

    print("\n[2/4] Ajout des instances (athlètes, compétitions, sports, pays)...")
    ajouter_instances(g)
    print(f"  → {len(g)} triplets après instances")

    print("\n[3/4] Intégration des entités supplémentaires (CSV Phase 0)...")
    n = ajouter_entites_csv(g, ENTITES_CSV)
    print(f"  → {n} entités supplémentaires ajoutées depuis CSV")
    print(f"  → {len(g)} triplets au total")

    print("\n[4/4] Export des fichiers...")
    BASE_DIR.mkdir(exist_ok=True)

    # Exporter Turtle
    g.serialize(destination=str(TTL_V1), format="turtle")
    print(f"  ✅ {TTL_V1}")

    # Exporter OWL (format XML)
    g.serialize(destination=str(OWL_FILE), format="xml")
    print(f"  ✅ {OWL_FILE}")

    # Statistiques
    stats = calculer_stats(g)
    stats["source"] = "knowledge_base_v1.ttl"
    stats["phase"] = "Phase 1 — KB initiale"
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"  ✅ {STATS_FILE}")

    print("\n📊 Statistiques de la KB initiale :")
    for cle, val in stats.items():
        if cle not in ("source", "phase"):
            print(f"   {cle:<20} : {val}")

    # Vérifications
    print("\n🔍 Validation :")
    if stats["total_triplets"] >= 100:
        print(f"  ✅ Triplets : {stats['total_triplets']} ≥ 100")
    else:
        print(f"  ⚠️  Triplets : {stats['total_triplets']} < 100 — Enrichir la KB")

    if stats["nb_entites"] >= 50:
        print(f"  ✅ Entités  : {stats['nb_entites']} ≥ 50")
    else:
        print(f"  ⚠️  Entités  : {stats['nb_entites']} < 50 — Enrichir la KB")

    print("\n✅ Phase 1 terminée — Passer à : python src/kg/script_alignement.py")


if __name__ == "__main__":
    main()
