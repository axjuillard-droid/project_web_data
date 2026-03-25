"""
Phase 3 — Alignement des prédicats via SPARQL
==============================================
Ce script :
  1. Pour chaque prédicat privé, interroge Wikidata pour trouver une propriété équivalente
  2. Classe l'alignement : owl:equivalentProperty (exact) ou rdfs:subPropertyOf (hiérarchique)
  3. Exporte mapping_predicats.csv

Usage :
    python src/kg/script_alignement_sparql.py

Prérequis :
    - kb/knowledge_base_v1.ttl doit exister (Phase 1)
"""

import csv
import time
import requests
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL

# ─── Chemins ────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
KB_DIR      = Path(__file__).parent.parent.parent / "kg_artifacts"
KB_V1       = Path(__file__).parent.parent.parent / "kg_artifacts" / "knowledge_base_v1.ttl"
MAPPING_CSV = Path(__file__).parent.parent.parent / "kg_artifacts" / "mapping_predicats.csv"

# ─── Namespaces ──────────────────────────────────────────────────────────────
NS  = Namespace("http://monprojet.org/sports/")
WDT = Namespace("http://www.wikidata.org/prop/direct/")

# ─── SPARQL Wikidata ──────────────────────────────────────────────────────────
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "KnowledgeGraphProject/1.0 (ESILV academic)",
    "Accept": "application/sparql-results+json",
}

# ─── Mappings connus (basés sur l'analyse manuelle du domaine sportifs) ───────
# Format : {prédicat_privé: (uri_wikidata, label_wikidata, type_alignement)}
KNOWN_PREDICATE_MAPPINGS = {
    "wonMedal": {
        "wikidata_property": "http://www.wikidata.org/prop/direct/P166",
        "wikidata_label":    "P166 — award received",
        "type_alignement":   "owl:equivalentProperty",
        "notes":             "Wikidata P166 couvre les prix et médailles",
    },
    "participatedIn": {
        "wikidata_property": "http://www.wikidata.org/prop/direct/P1344",
        "wikidata_label":    "P1344 — participant in",
        "type_alignement":   "owl:equivalentProperty",
        "notes":             "Correspondance exacte",
    },
    "represents": {
        "wikidata_property": "http://www.wikidata.org/prop/direct/P27",
        "wikidata_label":    "P27 — country of citizenship",
        "type_alignement":   "owl:equivalentProperty",
        "notes":             "Dans le contexte sportif, représente le pays de compétition",
    },
    "practicesSport": {
        "wikidata_property": "http://www.wikidata.org/prop/direct/P641",
        "wikidata_label":    "P641 — sport",
        "type_alignement":   "owl:equivalentProperty",
        "notes":             "Correspondance exacte",
    },
    "memberOfTeam": {
        "wikidata_property": "http://www.wikidata.org/prop/direct/P54",
        "wikidata_label":    "P54 — member of sports team",
        "type_alignement":   "owl:equivalentProperty",
        "notes":             "Correspondance exacte",
    },
    "hostedBy": {
        "wikidata_property": "http://www.wikidata.org/prop/direct/P17",
        "wikidata_label":    "P17 — country",
        "type_alignement":   "rdfs:subPropertyOf",
        "notes":             "P17 est plus général (pays d'une entité) — sous-propriété conservatrice",
    },
    "locatedIn": {
        "wikidata_property": "http://www.wikidata.org/prop/direct/P276",
        "wikidata_label":    "P276 — location",
        "type_alignement":   "owl:equivalentProperty",
        "notes":             "Lieu d'un événement",
    },
    "teamRepresents": {
        "wikidata_property": "http://www.wikidata.org/prop/direct/P17",
        "wikidata_label":    "P17 — country",
        "type_alignement":   "rdfs:subPropertyOf",
        "notes":             "Sous-propriété spécialisée pour les équipes sportives",
    },
    # Propriétés inférées (SWRL) — pas d'équivalent direct Wikidata
    "hasCompeted": {
        "wikidata_property": "—",
        "wikidata_label":    "—",
        "type_alignement":   "sans équivalent",
        "notes":             "Relation inférée SWRL — pas d'équivalent direct dans Wikidata",
    },
    "sameNationality": {
        "wikidata_property": "—",
        "wikidata_label":    "—",
        "type_alignement":   "sans équivalent",
        "notes":             "Relation inférée SWRL — symétrique, pas de propriété Wikidata",
    },
    "multiMedalist": {
        "wikidata_property": "—",
        "wikidata_label":    "—",
        "type_alignement":   "sans équivalent",
        "notes":             "Relation inférée SWRL — calculée à partir de wonMedal",
    },
}

# ─── Requête SPARQL de recherche par mot-clé ────────────────────────────────
def chercher_propriete_wikidata(mot_cle: str) -> list:
    """
    Cherche des propriétés Wikidata dont le label contient le mot-clé donné.
    Retourne une liste de (property_uri, property_label).
    """
    query = f"""
SELECT ?property ?propertyLabel WHERE {{
  ?property rdf:type wikibase:Property .
  ?property rdfs:label ?propertyLabel .
  FILTER(CONTAINS(LCASE(?propertyLabel), "{mot_cle.lower()}"))
  FILTER(LANG(?propertyLabel) = "en")
}}
LIMIT 10
"""
    try:
        resp = requests.get(
            WIKIDATA_ENDPOINT,
            params={"query": query, "format": "json"},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        resultats = resp.json().get("results", {}).get("bindings", [])
        return [(r["property"]["value"], r["propertyLabel"]["value"]) for r in resultats]
    except requests.exceptions.RequestException as e:
        print(f"    [Erreur SPARQL] {e}")
        return []


def ajouter_alignements_rdf(g: Graph, mappings: list) -> None:
    """
    Ajoute les triplets d'alignement dans le graphe RDF :
    - owl:equivalentProperty pour les correspondances exactes
    - rdfs:subPropertyOf pour les correspondances hiérarchiques
    """
    for m in mappings:
        if m["wikidata_property"] == "—":
            continue
        prop_locale = NS[m["predicat_prive"]]
        prop_wikidata = URIRef(m["wikidata_property"])
        if m["type_alignement"] == "owl:equivalentProperty":
            g.add((prop_locale, OWL.equivalentProperty, prop_wikidata))
        elif m["type_alignement"] == "rdfs:subPropertyOf":
            g.add((prop_locale, RDFS.subPropertyOf, prop_wikidata))


def main():
    print("=" * 60)
    print("Phase 3 — Alignement des prédicats via SPARQL")
    print("=" * 60)

    # Charger la KB
    if not KB_V1.exists():
        print(f"❌ {KB_V1} non trouvé — exécuter d'abord : python src/kg/script_construction.py")
        return
    print(f"\n[1/4] Chargement de {KB_V1.name}...")
    g = Graph()
    g.parse(str(KB_V1), format="turtle")
    g.bind("", NS)
    print(f"  → {len(g)} triplets chargés")

    print("\n[2/4] Inventaire des prédicats privés...")
    # Extraire tous les prédicats locaux utilisés dans la KB
    predicats_locaux = set()
    for s, p, o in g:
        if isinstance(p, URIRef) and str(p).startswith(str(NS)):
            predicats_locaux.add(str(p)[len(str(NS)):])
    print(f"  → {len(predicats_locaux)} prédicats locaux trouvés : {sorted(predicats_locaux)}")

    print("\n[3/4] Alignement des prédicats...")
    mappings = []
    for predicat in sorted(predicats_locaux):
        mapping_connu = KNOWN_PREDICATE_MAPPINGS.get(predicat, None)
        if mapping_connu:
            m = {"predicat_prive": predicat, **mapping_connu}
            mappings.append(m)
            emoji = "✅" if "equivalent" in mapping_connu["type_alignement"] else (
                    "↗️" if "subProperty" in mapping_connu["type_alignement"] else "—")
            print(f"  {emoji} :{predicat:30s} → {mapping_connu['wikidata_label']}")
        else:
            # Prédicat non couvert — chercher via SPARQL (fallback)
            print(f"  🔍 :{predicat:30s} → recherche SPARQL...")
            resultats_sparql = chercher_propriete_wikidata(predicat)
            if resultats_sparql:
                wd_uri, wd_label = resultats_sparql[0]
                print(f"    → Candidat : {wd_label} ({wd_uri})")
                m = {
                    "predicat_prive":   predicat,
                    "wikidata_property": wd_uri,
                    "wikidata_label":   wd_label,
                    "type_alignement":  "rdfs:subPropertyOf (à vérifier manuellement)",
                    "notes":            "Trouvé via SPARQL — vérifier la pertinence",
                }
            else:
                print(f"    → Aucun candidat trouvé")
                m = {
                    "predicat_prive":   predicat,
                    "wikidata_property": "—",
                    "wikidata_label":   "—",
                    "type_alignement":  "sans équivalent",
                    "notes":            "Prédicat spécifique au domaine — pas de correspondance Wikidata",
                }
            mappings.append(m)
            time.sleep(1)

    print("\n[4/4] Export des fichiers...")
    BASE_DIR.mkdir(exist_ok=True)

    # Ajouter les alignements dans le graphe
    ajouter_alignements_rdf(g, mappings)

    # Exporter le CSV
    champs = ["predicat_prive", "wikidata_property", "wikidata_label", "type_alignement", "notes"]
    with open(MAPPING_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=champs)
        writer.writeheader()
        writer.writerows(mappings)
    print(f"  ✅ {MAPPING_CSV}")

    # Mettre à jour la KB
    g.serialize(destination=str(KB_V1), format="turtle")
    print(f"  ✅ {KB_V1} (mis à jour avec les alignements de prédicats)")

    # Résumé
    equivalents    = sum(1 for m in mappings if "equivalent" in m["type_alignement"])
    sous_proprietes = sum(1 for m in mappings if "subProperty" in m["type_alignement"])
    sans_equiv     = sum(1 for m in mappings if m["type_alignement"] == "sans équivalent")
    print(f"\n📊 Résumé :")
    print(f"   owl:equivalentProperty : {equivalents}")
    print(f"   rdfs:subPropertyOf     : {sous_proprietes}")
    print(f"   Sans équivalent        : {sans_equiv}")
    print(f"   Total                  : {len(mappings)}")

    print("\n✅ Phase 3 terminée — Passer à : python src/kg/script_expansion_sparql.py")


if __name__ == "__main__":
    main()
