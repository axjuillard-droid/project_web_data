"""
Phase 0 — Collecte de données : Sportifs & compétitions
========================================================
Ce script :
  1. Interroge l'API Wikidata pour collecter des athlètes et compétitions
  2. Scrape les pages Wikipedia pour extraire du texte brut
  3. Applique NER (spacy) pour valider / enrichir les entités
  4. Exporte les résultats dans data/entités.csv

Usage :
    python src/crawl/script_collecte.py
"""

import csv
import json
import time
import requests
from pathlib import Path
from typing import Optional

# spacy est importé conditionnellement pour ne pas bloquer si le modèle manque
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_OK = True
except OSError:
    print("[AVERTISSEMENT] Modèle spacy non trouvé. Exécuter : python -m spacy download en_core_web_sm")
    SPACY_OK = False

# ─── Chemins ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
TEXTES_DIR = Path(__file__).parent.parent.parent / "data" / "textes_sources"
ENTITES_CSV = Path(__file__).parent.parent.parent / "data" / "entités.csv"
TEXTES_DIR.mkdir(exist_ok=True)

# ─── Configuration SPARQL ────────────────────────────────────────────────────
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "KnowledgeGraphProject/1.0 (ESILV academic project)",
    "Accept": "application/sparql-results+json",
}

# ─── Requêtes SPARQL ─────────────────────────────────────────────────────────

QUERY_ATHLETES = """
SELECT DISTINCT ?athlete ?athleteLabel ?sport ?sportLabel ?country ?countryLabel ?wikidataId WHERE {
  ?athlete wdt:P31 wd:Q5 ;               # instance of human
           wdt:P641 ?sport ;              # sport pratiqué
           wdt:P27 ?country .             # nationalité
  ?sport wdt:P31 wd:Q349 .               # sport olympique uniquement
  BIND(STRAFTER(STR(?athlete), "entity/") AS ?wikidataId)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 200
"""

QUERY_COMPETITIONS = """
SELECT DISTINCT ?competition ?competitionLabel ?year ?country ?countryLabel ?wikidataId WHERE {
  ?competition wdt:P31/wdt:P279* wd:Q27020041 .  # événement sportif
  OPTIONAL { ?competition wdt:P585 ?date . BIND(YEAR(?date) AS ?year) }
  OPTIONAL { ?competition wdt:P17 ?country . }
  FILTER(?year >= 2000)
  BIND(STRAFTER(STR(?competition), "entity/") AS ?wikidataId)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 100
"""

# Athlètes spécifiques de départ (entités ancrées connues)
SEED_ATHLETES = [
    ("Q1190522", "Usain Bolt",       "Athletics",  "Jamaica"),
    ("Q32684",   "Serena Williams",  "Tennis",     "United States"),
    ("Q615",     "Lionel Messi",     "Football",   "Argentina"),
    ("Q83868",   "Michael Phelps",   "Swimming",   "United States"),
    ("Q202090",  "Simone Biles",     "Gymnastics", "United States"),
    ("Q171277",  "Roger Federer",    "Tennis",     "Switzerland"),
    ("Q179477",  "Rafael Nadal",     "Tennis",     "Spain"),
    ("Q149985",  "Novak Djokovic",   "Tennis",     "Serbia"),
    ("Q12725",   "Carl Lewis",       "Athletics",  "United States"),
    ("Q1254",    "Muhammad Ali",     "Boxing",     "United States"),
    ("Q107348",  "Tiger Woods",      "Golf",       "United States"),
    ("Q36819",   "Pelé",             "Football",   "Brazil"),
    ("Q46220",   "Cristiano Ronaldo","Football",   "Portugal"),
    ("Q313746",  "Valentina Vezzali","Fencing",    "Italy"),
    ("Q220109",  "Mo Farah",         "Athletics",  "United Kingdom"),
    ("Q12823",   "Nadia Comaneci",   "Gymnastics", "Romania"),
    ("Q193003",  "Eliud Kipchoge",   "Athletics",  "Kenya"),
    ("Q180617",  "Kylian Mbappé",    "Football",   "France"),
    ("Q192616",  "LeBron James",     "Basketball", "United States"),
    ("Q168523",  "Michael Jordan",   "Basketball", "United States"),
]

SEED_COMPETITIONS = [
    ("Q8567",   "2008 Summer Olympics",      2008, "China"),
    ("Q8567",   "2012 Summer Olympics",      2012, "United Kingdom"),
    ("Q8567",   "2016 Summer Olympics",      2016, "Brazil"),
    ("Q8567",   "2020 Summer Olympics",      2021, "Japan"),
    ("Q193078", "2024 Summer Olympics",      2024, "France"),
    ("Q20771",  "2022 FIFA World Cup",       2022, "Qatar"),
    ("Q38717",  "2018 FIFA World Cup",       2018, "Russia"),
    ("Q20149",  "2014 FIFA World Cup",       2014, "Brazil"),
    ("Q52",     "Wimbledon Championships",   2023, "United Kingdom"),
    ("Q43255",  "Tour de France",            2023, "France"),
    ("Q55494",  "Boston Marathon",           2023, "United States"),
    ("Q212974", "UEFA Champions League",     2023, "United Kingdom"),
    ("Q192785", "Roland Garros",             2023, "France"),
    ("Q48800",  "US Open Tennis",            2023, "United States"),
    ("Q120918", "Australian Open",           2023, "Australia"),
]


def sparql_query(query: str, endpoint: str = WIKIDATA_ENDPOINT,
                 retries: int = 3) -> Optional[list]:
    """Exécute une requête SPARQL et retourne les résultats sous forme de liste."""
    for attempt in range(retries):
        try:
            response = requests.get(
                endpoint,
                params={"query": query, "format": "json"},
                headers=HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", {}).get("bindings", [])
        except requests.exceptions.RequestException as e:
            print(f"  [Erreur SPARQL tentative {attempt+1}/{retries}] {e}")
            time.sleep(2 ** attempt)
    return None


def fetch_wikipedia_text(title: str) -> Optional[str]:
    """Récupère le résumé Wikipedia d'une entité (section intro)."""
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + title.replace(" ", "_")
    try:
        response = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=10)
        if response.status_code == 200:
            return response.json().get("extract", "")
    except requests.exceptions.RequestException:
        pass
    return None


def extract_entities_from_text(text: str) -> list:
    """Applique NER spacy sur un texte et retourne les entités nommées."""
    if not SPACY_OK or not text:
        return []
    doc = nlp(text[:10_000])  # limiter à 10k caractères
    return [(ent.text, ent.label_) for ent in doc.ents
            if ent.label_ in ("PERSON", "ORG", "GPE", "EVENT", "LOC")]


def build_entity_id(name: str) -> str:
    """Construit un identifiant camelCase propre à partir d'un nom."""
    parts = name.strip().split()
    if not parts:
        return "unknownEntity"
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def collect_entities() -> list:
    """
    Collecte toutes les entités — athletes + compétitions — depuis les seeds
    et optionnellement depuis SPARQL.
    Retourne une liste de dicts avec colonnes : id, nom, type, wikidata_uri, source_url.
    """
    entites = []

    print("=== Collecte des athlètes (seeds) ===")
    for qid, nom, sport, pays in SEED_ATHLETES:
        entity_id = build_entity_id(nom)
        entites.append({
            "id": entity_id,
            "nom": nom,
            "type": "Athlete",
            "sport": sport,
            "pays": pays,
            "wikidata_uri": f"http://www.wikidata.org/entity/{qid}",
            "source_url": f"https://en.wikipedia.org/wiki/{nom.replace(' ', '_')}",
        })
        print(f"  ✓ {nom} ({qid})")

        # Télécharger le texte Wikipedia pour NER
        texte = fetch_wikipedia_text(nom)
        if texte:
            chemin = TEXTES_DIR / f"{entity_id}.txt"
            chemin.write_text(texte, encoding="utf-8")
            entites_ner = extract_entities_from_text(texte)
            if entites_ner:
                print(f"    → NER : {entites_ner[:5]}...")
        time.sleep(0.5)  # respecter les rate limits

    print("\n=== Collecte des compétitions (seeds) ===")
    seen_competitions = set()
    for qid, nom, annee, pays in SEED_COMPETITIONS:
        entity_id = build_entity_id(nom)
        if entity_id in seen_competitions:
            continue
        seen_competitions.add(entity_id)
        entites.append({
            "id": entity_id,
            "nom": nom,
            "type": "Competition",
            "sport": "",
            "annee": annee,
            "pays": pays,
            "wikidata_uri": f"http://www.wikidata.org/entity/{qid}",
            "source_url": f"https://en.wikipedia.org/wiki/{nom.replace(' ', '_')}",
        })
        print(f"  ✓ {nom} ({qid})")

    print("\n=== Requête SPARQL Wikidata — athlètes additionnels ===")
    resultats = sparql_query(QUERY_ATHLETES)
    if resultats:
        ids_existants = {e["wikidata_uri"] for e in entites}
        compteur = 0
        for r in resultats:
            uri = r.get("athlete", {}).get("value", "")
            nom = r.get("athleteLabel", {}).get("value", "")
            sport = r.get("sportLabel", {}).get("value", "")
            pays = r.get("countryLabel", {}).get("value", "")
            if uri and uri not in ids_existants and nom:
                entity_id = build_entity_id(nom)
                entites.append({
                    "id": entity_id,
                    "nom": nom,
                    "type": "Athlete",
                    "sport": sport,
                    "pays": pays,
                    "wikidata_uri": uri,
                    "source_url": "",
                })
                ids_existants.add(uri)
                compteur += 1
        print(f"  → {compteur} athlètes supplémentaires collectés via SPARQL")
    else:
        print("  [INFO] Requête SPARQL ignorée (timeout ou erreur réseau)")

    return entites


def exporter_csv(entites: list, chemin: Path) -> None:
    """Exporte la liste d'entités dans un fichier CSV."""
    if not entites:
        print("[AVERTISSEMENT] Aucune entité à exporter.")
        return
    champs = list(entites[0].keys())
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=champs, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(entites)
    print(f"\n✅ {len(entites)} entités exportées → {chemin}")


def main():
    print("=" * 60)
    print("Phase 0 — Collecte de données : Sportifs & compétitions")
    print("=" * 60)

    entites = collect_entities()
    exporter_csv(entites, ENTITES_CSV)

    # Statistiques
    athletes = [e for e in entites if e["type"] == "Athlete"]
    competitions = [e for e in entites if e["type"] == "Competition"]
    print(f"\n📊 Statistiques :")
    print(f"   Athlètes    : {len(athletes)}")
    print(f"   Compétitions: {len(competitions)}")
    print(f"   Total       : {len(entites)}")
    print(f"\n💾 Textes sauvegardés dans : {TEXTES_DIR}")
    print("\n✅ Phase 0 terminée — Passer à : python src/kg/script_construction.py")


if __name__ == "__main__":
    main()
