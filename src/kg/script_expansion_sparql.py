"""
Phase 4 — Expansion de la KB via SPARQL (Wikidata)
====================================================
Ce script :
  1. Charge les entités alignées avec Wikidata (owl:sameAs) depuis la KB
  2. Expansion 1-hop : récupère tous les triplets directs de chaque entité
  3. Expansion 2-hop : récupère les entités liées aux entités liées
  4. Expansion par discipline : athlètes par sport (athletics, tennis, football…)
  5. Nettoyage : suppression des doublons, URIs malformées, prédicats à forte charge littérale
  6. Export de knowledge_base_expanded.ttl + stats_kb.json

Usage :
    python src/kg/script_expansion_sparql.py

Prérequis :
    - kb/knowledge_base_v1.ttl doit exister avec les owl:sameAs (Phases 2 & 3)
"""

import json
import time
import re
import requests
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD

# ─── Chemins ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
KB_DIR     = Path(__file__).parent.parent.parent / "kg_artifacts"
KB_V1      = Path(__file__).parent.parent.parent / "kg_artifacts" / "knowledge_base_v1.ttl"
KB_EXP     = Path(__file__).parent.parent.parent / "kg_artifacts" / "expanded.ttl"
STATS_FILE = Path(__file__).parent.parent.parent / "kg_artifacts" / "stats_kb.json"

# ─── Namespaces ──────────────────────────────────────────────────────────────
NS  = Namespace("http://monprojet.org/sports/")
WD  = Namespace("http://www.wikidata.org/entity/")
WDT = Namespace("http://www.wikidata.org/prop/direct/")

# ─── Configuration SPARQL ────────────────────────────────────────────────────
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "KnowledgeGraphProject/1.0 (ESILV academic)",
    "Accept": "application/sparql-results+json",
}

# Prédicats à écarter (trop verbeux, ne contribuent pas aux embeddings)
PREDICATS_A_EXCLURE = {
    "http://schema.org/description",
    "http://www.w3.org/2004/02/skos/core#prefLabel",
    "http://www.w3.org/2004/02/skos/core#altLabel",
    "http://www.w3.org/2000/01/rdf-schema#comment",
    "http://www.w3.org/2000/01/rdf-schema#label",
    "http://wikiba.se/ontology#statements",
    "http://www.w3.org/2002/07/owl#sameAs",  # éviter les boucles de sameAs
}

# URIs de sports Wikidata pour l'expansion par discipline
SPORTS_WIKIDATA = {
    "Athletics": "wd:Q542",
    "Tennis":    "wd:Q847",
    "Football":  "wd:Q2736",
    "Swimming":  "wd:Q31920",
    "Gymnastics":"wd:Q1014",
    "Basketball":"wd:Q5372",
    "Cycling":   "wd:Q53124",
    "Boxing":    "wd:Q11462",
    "Golf":      "wd:Q5377",
    "Fencing":   "wd:Q12156",
    "Baseball":  "wd:Q5375",
    "Rugby":     "wd:Q190",
    "IceHockey": "wd:Q41466",
    "Volleyball":"wd:Q1734",
    "Cricket":   "wd:Q15286",
    "Judo":      "wd:Q11424",
    "Karate":    "wd:Q11419",
    "Badminton": "wd:Q7291",
    "Archery":   "wd:Q10884",
    "Skating":   "wd:Q133333",
    "Surfing":   "wd:Q159051",
    "Wrestling": "wd:Q131430",
    "Skiing":    "wd:Q1862",
    "Formula1":  "wd:Q1968",
    "Handball":  "wd:Q102293",
    "TableTennis":"wd:Q39303",
    "Badminton": "wd:Q7291",
    "Archery":   "wd:Q10884",
    "Volleyball":"wd:Q1734",
}


def sparql_query(query: str, retries: int = 3) -> list:
    """Exécute une requête SPARQL sur Wikidata, avec gestion des erreurs et retry."""
    for attempt in range(retries):
        try:
            resp = requests.get(
                WIKIDATA_ENDPOINT,
                params={"query": query, "format": "json"},
                headers=HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("results", {}).get("bindings", [])
        except requests.exceptions.RequestException as e:
            print(f"    [Erreur SPARQL tentative {attempt+1}/{retries}] {e}")
            time.sleep(2 ** attempt)
    return []


def uri_valide(uri_str: str) -> bool:
    """Vérifie qu'une URI est bien formée (commence par http, pas de caractères invalides)."""
    if not uri_str.startswith("http"):
        return False
    if " " in uri_str or "\n" in uri_str:
        return False
    # Exclure les URIs de propriétés de type statement (P...-stmtXXX)
    if "/statement/" in uri_str:
        return False
    return True


def est_litterale_longue(val: str, seuil: int = 500) -> bool:
    """Retourne True si la valeur est un littéral trop long."""
    return len(val) > seuil


def extraire_entites_alignees(g: Graph) -> list:
    """
    Extrait les QIDs Wikidata depuis les triplets owl:sameAs de la KB.
    Retourne une liste de QIDs (ex: "Q1190522").
    """
    qids = []
    for s, p, o in g.triples((None, OWL.sameAs, None)):
        if isinstance(o, URIRef):
            uri_str = str(o)
            if "wikidata.org/entity/Q" in uri_str:
                qid = uri_str.split("/entity/")[-1]
                if qid.startswith("Q"):
                    qids.append(qid)
    return list(set(qids))


def expansion_1hop(qid: str, g: Graph, compteur: dict) -> int:
    query = f"SELECT ?p ?o WHERE {{ wd:{qid} ?p ?o . FILTER(!isLiteral(?o) || LANG(?o) = \"\" || LANG(?o) = \"en\") }} LIMIT 1500"
    resultats = sparql_query(query)
    ajoutes = 0
    sujet = WD[qid]
    for r in resultats:
        p_val = r.get("p", {}).get("value", "")
        o_node = r.get("o", {})
        o_type = o_node.get("type", "")
        o_val  = o_node.get("value", "")

        # Filtrer les prédicats à exclure et les URIs invalides
        if p_val in PREDICATS_A_EXCLURE:
            continue
        if not uri_valide(p_val):
            continue

        predicat = URIRef(p_val)

        if o_type == "uri" and uri_valide(o_val):
            objet = URIRef(o_val)
        elif o_type == "literal":
            if est_litterale_longue(o_val):
                continue
            datatype = o_node.get("datatype", "")
            lang = o_node.get("xml:lang", "")
            if datatype:
                objet = Literal(o_val, datatype=URIRef(datatype))
            elif lang:
                objet = Literal(o_val, lang=lang)
            else:
                objet = Literal(o_val)
        else:
            continue

        triplet = (sujet, predicat, objet)
        if triplet not in g:
            g.add(triplet)
            ajoutes += 1

    compteur["1hop"] += ajoutes
    return ajoutes


def expansion_2hop(qid: str, g: Graph, compteur: dict, limit_entites: int = 20) -> int:
    """Expand 2-hop : pour les entités liées à QID, récupère leurs triplets directs."""
    query = f"""
SELECT DISTINCT ?e2 WHERE {{
  wd:{qid} ?p1 ?e2 .
  ?e2 wdt:P31 ?type .
  FILTER(isIRI(?e2) && STRSTARTS(STR(?e2), "http://www.wikidata.org/entity/Q"))
}}
LIMIT {limit_entites}
"""
    entites_liees = sparql_query(query)
    total = 0
    for r in entites_liees:
        e2_uri = r.get("e2", {}).get("value", "")
        if not e2_uri or "wikidata.org/entity/Q" not in e2_uri:
            continue
        e2_qid = e2_uri.split("/entity/")[-1]
        # On définit le 2-hop manuellement ici pour ne pas polluer le compteur 1hop
        n = extraction_unitaire(e2_qid, g) 
        compteur["2hop"] += n
        total += n
        time.sleep(0.5) 
    return total


def extraction_unitaire(qid: str, g: Graph) -> int:
    """Expansion 1-hop interne sans mise à jour du compteur global."""
    query = f"SELECT ?p ?o WHERE {{ wd:{qid} ?p ?o . FILTER(!isLiteral(?o) || LANG(?o) = \"\" || LANG(?o) = \"en\") }} LIMIT 1500"
    resultats = sparql_query(query)
    ajoutes = 0
    sujet = WD[qid]
    for r in resultats:
        p_val = r.get("p", {}).get("value", "")
        o_node = r.get("o", {})
        o_type = o_node.get("type", "")
        o_val  = o_node.get("value", "")
        if p_val in PREDICATS_A_EXCLURE or not uri_valide(p_val):
            continue
        predicat = URIRef(p_val)
        if o_type == "uri" and uri_valide(o_val):
            objet = URIRef(o_val)
        elif o_type == "literal":
            if est_litterale_longue(o_val): continue
            datatype, lang = o_node.get("datatype", ""), o_node.get("xml:lang", "")
            if datatype: objet = Literal(o_val, datatype=URIRef(datatype))
            elif lang: objet = Literal(o_val, lang=lang)
            else: objet = Literal(o_val)
        else: continue
        if (sujet, predicat, objet) not in g:
            g.add((sujet, predicat, objet))
            ajoutes += 1
    return ajoutes


def expansion_par_discipline(sport_id: str, wd_sport_uri: str, g: Graph, compteur: dict) -> int:
    """Expand par discipline : athlètes pratiquant ce sport sur Wikidata."""
    wd_sport = wd_sport_uri.replace("wd:", "wd:")
    query = f"SELECT DISTINCT ?athlete ?p ?o WHERE {{ ?athlete wdt:P641 {wd_sport} ; wdt:P31 wd:Q5 . ?athlete ?p ?o . FILTER(!isLiteral(?o) || (LANG(?o) = \"\" || LANG(?o) = \"en\")) }} LIMIT 7000"
    resultats = sparql_query(query)
    ajoutes = 0
    for r in resultats:
        s_val = r.get("athlete", {}).get("value", "")
        p_val = r.get("p", {}).get("value", "")
        o_node = r.get("o", {})
        o_type = o_node.get("type", "")
        o_val  = o_node.get("value", "")

        if not uri_valide(s_val) or p_val in PREDICATS_A_EXCLURE or not uri_valide(p_val):
            continue

        sujet   = URIRef(s_val)
        predicat = URIRef(p_val)

        if o_type == "uri" and uri_valide(o_val):
            objet = URIRef(o_val)
        elif o_type == "literal":
            if est_litterale_longue(o_val):
                continue
            lang = o_node.get("xml:lang", "")
            datatype = o_node.get("datatype", "")
            if datatype:
                objet = Literal(o_val, datatype=URIRef(datatype))
            elif lang:
                objet = Literal(o_val, lang=lang)
            else:
                objet = Literal(o_val)
        else:
            continue

        triplet = (sujet, predicat, objet)
        if triplet not in g:
            g.add(triplet)
            ajoutes += 1

    compteur["discipline"] += ajoutes
    return ajoutes


def verifier_connectivite(g: Graph) -> dict:
    """Vérifie la connectivité basique du graphe — statistiques."""
    sujets = set(s for s, p, o in g if isinstance(s, URIRef))
    objets = set(str(o) for s, p, o in g if isinstance(o, URIRef))
    predicats = set(str(p) for s, p, o in g)
    return {
        "nb_sujets_uniques":  len(sujets),
        "nb_objets_urefs":    len(objets),
        "nb_predicats":       len(predicats),
    }


def calculer_stats(g: Graph) -> dict:
    triplets = len(g)
    entites = set()
    relations = set()
    for s, p, o in g:
        if isinstance(s, URIRef):
            entites.add(str(s))
        if isinstance(p, URIRef):
            relations.add(str(p))
    return {
        "total_triplets": triplets,
        "nb_entites":     len(entites),
        "nb_relations":   len(relations),
        "source":         "expanded.ttl",
        "phase":          "Phase 4 — KB étendue",
    }


def main():
    print("=" * 60)
    print("Phase 4 — Expansion de la KB via SPARQL")
    print("=" * 60)

    if not KB_V1.exists():
        print(f"❌ {KB_V1} non trouvé.")
        return

    print(f"\n[1/5] Chargement de {KB_V1.name}...")
    g = Graph()
    g.parse(str(KB_V1), format="turtle")
    g.bind("", NS)
    g.bind("wd", WD)
    g.bind("wdt", WDT)
    nb_initial = len(g)
    print(f"  → {nb_initial} triplets chargés")

    print("\n[2/5] Extraction des entités alignées (owl:sameAs)...")
    qids = extraire_entites_alignees(g)
    print(f"  → {len(qids)} entités alignées : {qids[:10]}...")

    compteur = {"1hop": 0, "2hop": 0, "discipline": 0}

    print("\n[3/5] Expansion 1-hop (triplets directs des entités alignées)...")
    for i, qid in enumerate(qids):
        n = expansion_1hop(qid, g, compteur)
        print(f"  [{i+1}/{len(qids)}] {qid} → +{n} triplets (total={len(g)})")
        time.sleep(1)

    print(f"\n[4/5] Expansion 2-hop (voisins des entités alignées)...")
    limite_2hop = 15 # Réduit de 120 à 15 pour la vitesse
    for i, qid in enumerate(qids[:limite_2hop]):
        n = expansion_2hop(qid, g, compteur)
        print(f"  [{i+1}/{limite_2hop}] {qid} (2-hop) → +{n} triplets (total={len(g)})")
        time.sleep(2)

    print(f"\n[5/5] Expansion par discipline sportive...")
    for sport_id, wd_sport_uri in SPORTS_WIKIDATA.items():
        print(f"  Discipline : {sport_id}...")
        n = expansion_par_discipline(sport_id, wd_sport_uri, g, compteur)
        print(f"    → +{n} triplets (total={len(g)})")
        time.sleep(3)

    # Nettoyage final
    print("\n🧹 Nettoyage (pas nécessaire — les filtres sont inline)...")
    print(f"  → {len(g)} triplets après expansion")

    # Export
    print("\n💾 Export de la KB étendue...")
    g.serialize(destination=str(KB_EXP), format="turtle")
    print(f"  ✅ {KB_EXP}")

    # Statistiques
    stats = calculer_stats(g)
    conn = verifier_connectivite(g)
    stats.update(conn)
    stats["triplets_ajoutes_1hop"]      = compteur["1hop"]
    stats["triplets_ajoutes_2hop"]      = compteur["2hop"]
    stats["triplets_ajoutes_discipline"] = compteur["discipline"]
    stats["triplets_initiaux"]           = nb_initial

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"  ✅ {STATS_FILE}")

    print("\n📊 Statistiques finales :")
    print(f"   Triplets initiaux  : {nb_initial}")
    print(f"   Ajoutés (1-hop)    : {compteur['1hop']}")
    print(f"   Ajoutés (2-hop)    : {compteur['2hop']}")
    print(f"   Ajoutés (discipline): {compteur['discipline']}")
    print(f"   Total triplets     : {stats['total_triplets']}")
    print(f"   Entités uniques    : {stats['nb_entites']}")
    print(f"   Relations uniques  : {stats['nb_relations']}")

    # Vérification des volumes cibles
    print("\n🔍 Vérification volumes cibles :")
    triplets = stats["total_triplets"]
    entites  = stats["nb_entites"]
    relations = stats["nb_relations"]

    if 50_000 <= triplets <= 200_000:
        print(f"  ✅ Triplets : {triplets:,} (cible : 50k–200k)")
    elif triplets < 50_000:
        print(f"  ⚠️  Triplets : {triplets:,} < 50k — augmenter les LIMIT SPARQL")
    else:
        print(f"  ⚠️  Triplets : {triplets:,} > 200k — réduire les LIMIT SPARQL")

    if entites >= 5_000:
        print(f"  ✅ Entités  : {entites:,} (cible : ≥ 5k)")
    else:
        print(f"  ⚠️  Entités  : {entites:,} < 5k — expansion insuffisante")

    if 50 <= relations <= 200:
        print(f"  ✅ Relations : {relations:,} (cible : 50–200)")
    else:
        print(f"  ℹ️  Relations : {relations:,}")

    print("\n✅ Phase 4 terminée — Passer à : python raisonnement/swrl_rules.py")


if __name__ == "__main__":
    main()
