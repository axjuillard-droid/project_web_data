"""
Phase 2 — Alignement des entités avec Wikidata
===============================================
Ce script :
  1. Charge la KB initiale (kb/knowledge_base_v1.ttl)
  2. Pour chaque entité :
     - cherche son URI Wikidata via l'API wbsearchentities
     - si trouvée → ajoute owl:sameAs + score de confiance
     - si non trouvée → définit sémantiquement (classe + rdfs:label)
  3. Exporte mapping_entites.csv et les triplets owl:sameAs dans la KB

Usage :
    python src/kg/script_alignement.py

Prérequis :
    - kb/knowledge_base_v1.ttl doit exister (Phase 1)
"""

import csv
import json
import time
import requests
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL

# ─── Chemins ────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
KB_DIR      = Path(__file__).parent.parent.parent / "kg_artifacts"
KB_V1       = Path(__file__).parent.parent.parent / "kg_artifacts" / "knowledge_base_v1.ttl"
MAPPING_CSV = Path(__file__).parent.parent.parent / "kg_artifacts" / "mapping_entites.csv"
NOUVELLES   = Path(__file__).parent.parent.parent / "kg_artifacts" / "nouvelles_entites.ttl"

# ─── Namespaces ──────────────────────────────────────────────────────────────
NS = Namespace("http://monprojet.org/sports/")
WD = Namespace("http://www.wikidata.org/entity/")

# ─── API Wikidata ─────────────────────────────────────────────────────────────
WIKIDATA_API  = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "KnowledgeGraphProject/1.0 (ESILV academic)"}

# ─── Mappings connus (seed) ───────────────────────────────────────────────────
# Évite les appels API pour les entités dont on connaît déjà l'URI Wikidata
KNOWN_MAPPINGS = {
    "UsainBolt":          ("wd:Q1190522", "http://www.wikidata.org/entity/Q1190522", 0.99),
    "SerenaWilliams":     ("wd:Q32684",   "http://www.wikidata.org/entity/Q32684",   0.99),
    "LionelMessi":        ("wd:Q615",     "http://www.wikidata.org/entity/Q615",     0.99),
    "MichaelPhelps":      ("wd:Q83868",   "http://www.wikidata.org/entity/Q83868",   0.99),
    "SimoneBiles":        ("wd:Q202090",  "http://www.wikidata.org/entity/Q202090",  0.99),
    "RogerFederer":       ("wd:Q171277",  "http://www.wikidata.org/entity/Q171277",  0.99),
    "RafaelNadal":        ("wd:Q179477",  "http://www.wikidata.org/entity/Q179477",  0.99),
    "NovakDjokovic":      ("wd:Q149985",  "http://www.wikidata.org/entity/Q149985",  0.99),
    "EliudKipchoge":      ("wd:Q193003",  "http://www.wikidata.org/entity/Q193003",  0.99),
    "CristianoRonaldo":   ("wd:Q46220",   "http://www.wikidata.org/entity/Q46220",   0.99),
    "KylianMbappe":       ("wd:Q180617",  "http://www.wikidata.org/entity/Q180617",  0.99),
    "LeBronJames":        ("wd:Q192616",  "http://www.wikidata.org/entity/Q192616",  0.99),
    "MoFarah":            ("wd:Q220109",  "http://www.wikidata.org/entity/Q220109",  0.99),
    "MichaelJordan":      ("wd:Q168523",  "http://www.wikidata.org/entity/Q168523",  0.99),
    "OlympicsBeijing2008":    ("wd:Q8567",   "http://www.wikidata.org/entity/Q8567",   0.97),
    "OlympicsLondon2012":     ("wd:Q8566",   "http://www.wikidata.org/entity/Q8566",   0.97),
    "OlympicsRioDeJaneiro2016": ("wd:Q8575", "http://www.wikidata.org/entity/Q8575",   0.97),
    "OlympicsTokyo2020":      ("wd:Q76543456", "http://www.wikidata.org/entity/Q76543456", 0.96),
    "OlympicsParis2024":      ("wd:Q193078", "http://www.wikidata.org/entity/Q193078", 0.97),
    "FIFAWorldCup2022":       ("wd:Q20771",  "http://www.wikidata.org/entity/Q20771",  0.99),
    "FIFAWorldCup2018":       ("wd:Q38717",  "http://www.wikidata.org/entity/Q38717",  0.99),
    "FIFAWorldCup2014":       ("wd:Q20149",  "http://www.wikidata.org/entity/Q20149",  0.99),
}


def rechercher_wikidata(nom: str, type_entite: str = "Athlete") -> tuple:
    """
    Recherche une entité sur Wikidata via l'API wbsearchentities.
    Retourne (uri_wikidata, score_confiance) ou (None, 0.0).
    """
    type_hint = "Q5" if type_entite == "Athlete" else "Q27020041"
    try:
        params = {
            "action": "wbsearchentities",
            "search": nom,
            "language": "en",
            "format": "json",
            "type": "item",
            "limit": 5,
        }
        resp = requests.get(WIKIDATA_API, params=params,
                            headers=HEADERS, timeout=10)
        resp.raise_for_status()
        resultats = resp.json().get("search", [])
        if not resultats:
            return None, 0.0
        # Prendre le premier résultat et calculer un score de confiance approximatif
        premier = resultats[0]
        uri = premier.get("concepturi", "")
        label = premier.get("label", "").lower()
        nom_normalise = nom.lower().replace(" ", "")
        score = 0.9 if label.replace(" ", "") == nom_normalise else 0.7
        return uri, round(score, 2)
    except requests.exceptions.RequestException:
        return None, 0.0


def charger_entites_kb(g: Graph) -> list:
    """
    Extrait les entités (Athlete, Competition) du graphe RDF.
    Retourne une liste de (entity_id, label, type_entite).
    """
    entites = []
    for uri, _, label in g.triples((None, RDFS.label, None)):
        if not isinstance(uri, URIRef):
            continue
        str_uri = str(uri)
        if not str_uri.startswith(str(NS)):
            continue
        entity_id = str_uri[len(str(NS)):]
        # Déterminer le type
        type_entite = None
        if (uri, RDF.type, NS.Athlete) in g:
            type_entite = "Athlete"
        elif (uri, RDF.type, NS.Competition) in g:
            type_entite = "Competition"
        if type_entite:
            entites.append((entity_id, str(label), type_entite))
    return entites


def aligner_entites(g: Graph, entites: list) -> list:
    """
    Pour chaque entité, cherche son URI Wikidata et ajoute owl:sameAs.
    Retourne la liste des mappings.
    """
    mappings = []

    print(f"  → {len(entites)} entités à aligner...")
    for entity_id, label, type_entite in entites:
        uri = NS[entity_id]
        statut = "?"

        # 1. Vérifier si déjà mappé (known mappings)
        if entity_id in KNOWN_MAPPINGS:
            wd_label, wd_uri, score = KNOWN_MAPPINGS[entity_id]
            g.add((uri, OWL.sameAs, URIRef(wd_uri)))
            statut = "✅ alignée (connue)"
            mappings.append({
                "entite_privee": f":{entity_id}",
                "label":         label,
                "type":          type_entite,
                "uri_wikidata":  wd_uri,
                "wd_label":      wd_label,
                "score_confiance": score,
                "statut":        "alignée",
            })
            print(f"    ✅ {entity_id:40s} → {wd_label} (score={score})")
            continue

        # 2. Vérifier si owl:sameAs déjà présent dans le graphe (depuis CSV Phase 0)
        same_as_existant = list(g.objects(uri, OWL.sameAs))
        if same_as_existant:
            wd_uri = str(same_as_existant[0])
            mappings.append({
                "entite_privee": f":{entity_id}",
                "label":         label,
                "type":          type_entite,
                "uri_wikidata":  wd_uri,
                "wd_label":      "",
                "score_confiance": 0.85,
                "statut":        "alignée (CSV)",
            })
            print(f"    ✅ {entity_id:40s} → {wd_uri[:50]} (depuis CSV)")
            continue

        # 3. Chercher sur Wikidata via API
        wd_uri, score = rechercher_wikidata(entity_id, type_entite)
        if wd_uri and score >= 0.7:
            g.add((uri, OWL.sameAs, URIRef(wd_uri)))
            statut = f"✅ alignée (API, score={score})"
            mappings.append({
                "entite_privee": f":{entity_id}",
                "label":         label,
                "type":          type_entite,
                "uri_wikidata":  wd_uri,
                "wd_label":      "",
                "score_confiance": score,
                "statut":        "alignée",
            })
        else:
            # Entité non trouvée — définir sémantiquement
            statut = "🆕 nouvelle entité"
            mappings.append({
                "entite_privee": f":{entity_id}",
                "label":         label,
                "type":          type_entite,
                "uri_wikidata":  "—",
                "wd_label":      "—",
                "score_confiance": "—",
                "statut":        "nouvelle entité",
            })
        print(f"    {statut[:2]} {entity_id:40s}")
        time.sleep(0.3)  # rate limit API Wikidata

    return mappings


def exporter_nouvelles_entites(g: Graph, mappings: list) -> None:
    """Exporte un fichier Turtle pour les entités sans URI Wikidata."""
    g_new = Graph()
    g_new.bind("", NS)
    g_new.bind("rdf", RDF)
    g_new.bind("rdfs", RDFS)
    for m in mappings:
        if m["statut"] == "nouvelle entité":
            entity_id = m["entite_privee"].lstrip(":")
            uri = NS[entity_id]
            g_new.add((uri, RDF.type, NS[m["type"]]))
            g_new.add((uri, RDFS.label, Literal(m["label"], lang="en")))
            g_new.add((uri, RDFS.comment,
                       Literal(f"Entité non trouvée dans Wikidata — définie sémantiquement", lang="fr")))
    g_new.serialize(destination=str(NOUVELLES), format="turtle")
    print(f"  ✅ {NOUVELLES} ({sum(1 for m in mappings if m['statut']=='nouvelle entité')} nouvelles entités)")


def main():
    print("=" * 60)
    print("Phase 2 — Alignement des entités avec Wikidata")
    print("=" * 60)

    # Charger la KB initiale
    if not KB_V1.exists():
        print(f"❌ {KB_V1} non trouvé — exécuter d'abord : python src/kg/script_construction.py")
        return
    print(f"\n[1/4] Chargement de {KB_V1.name}...")
    g = Graph()
    g.parse(str(KB_V1), format="turtle")
    g.bind("", NS)
    g.bind("wd", WD)
    print(f"  → {len(g)} triplets chargés")

    print("\n[2/4] Extraction des entités à aligner...")
    entites = charger_entites_kb(g)
    print(f"  → {len(entites)} entités (athlètes + compétitions)")

    print("\n[3/4] Alignement avec Wikidata...")
    mappings = aligner_entites(g, entites)

    print("\n[4/4] Export des fichiers...")
    BASE_DIR.mkdir(exist_ok=True)

    # CSV de mapping
    champs = ["entite_privee", "label", "type", "uri_wikidata", "wd_label", "score_confiance", "statut"]
    with open(MAPPING_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=champs)
        writer.writeheader()
        writer.writerows(mappings)
    print(f"  ✅ {MAPPING_CSV}")

    # Nouvelles entités
    exporter_nouvelles_entites(g, mappings)

    # Mettre à jour la KB avec les owl:sameAs
    g.serialize(destination=str(KB_V1), format="turtle")
    print(f"  ✅ {KB_V1} (mis à jour avec owl:sameAs)")

    # Résumé
    alignees = sum(1 for m in mappings if "alignée" in m["statut"])
    nouvelles = sum(1 for m in mappings if m["statut"] == "nouvelle entité")
    print(f"\n📊 Résumé :")
    print(f"   Total entités    : {len(mappings)}")
    print(f"   Alignées         : {alignees}")
    print(f"   Nouvelles        : {nouvelles}")

    print("\n✅ Phase 2 terminée — Passer à : python src/kg/script_alignement_sparql.py")


if __name__ == "__main__":
    main()
