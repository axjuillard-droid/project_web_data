"""
Phase 7 - Query Builder : NL -> SPARQL
=======================================
Deux interfaces disponibles :
  A. API pytest : build_query(intent: str, entity: str) -> str | None
  B. API NL   : QueryBuilder().construire_requete(question: str) -> dict

Usage (module) :
    from rag.query_builder import QueryBuilder, build_query
    qb = QueryBuilder()
    query = qb.construire_requete("Quelles medailles a remporte Usain Bolt ?")
"""

import re
from pathlib import Path

# Namespace local de la KB
NS_PREFIX = "http://monprojet.org/sports/"

# --- Entites connues (pour entity linking) -----------------------------------
ENTITES_CONNUES = {
    # Athletes
    "usain bolt":        "UsainBolt",
    "bolt":              "UsainBolt",
    "serena williams":   "SerenaWilliams",
    "serena":            "SerenaWilliams",
    "lionel messi":      "LionelMessi",
    "messi":             "LionelMessi",
    "michael phelps":    "MichaelPhelps",
    "phelps":            "MichaelPhelps",
    "simone biles":      "SimoneBiles",
    "biles":             "SimoneBiles",
    "roger federer":     "RogerFederer",
    "federer":           "RogerFederer",
    "rafael nadal":      "RafaelNadal",
    "nadal":             "RafaelNadal",
    "novak djokovic":    "NovakDjokovic",
    "djokovic":          "NovakDjokovic",
    "eliud kipchoge":    "EliudKipchoge",
    "kipchoge":          "EliudKipchoge",
    "cristiano ronaldo": "CristianoRonaldo",
    "ronaldo":           "CristianoRonaldo",
    "kylian mbappe":     "KylianMbappe",
    "mbappe":            "KylianMbappe",
    "lebron james":      "LeBronJames",
    "lebron":            "LeBronJames",
    "mo farah":          "MoFarah",
    "farah":             "MoFarah",
    # Competitions
    "jeux olympiques de paris": "OlympicsParis2024",
    "jo paris":                 "OlympicsParis2024",
    "paris 2024":               "OlympicsParis2024",
    "jeux olympiques tokyo":    "OlympicsTokyo2020",
    "tokyo 2020":               "OlympicsTokyo2020",
    "jeux olympiques de rio":   "OlympicsRioDeJaneiro2016",
    "rio 2016":                 "OlympicsRioDeJaneiro2016",
    "jeux olympiques beijing":  "OlympicsBeijing2008",
    "beijing 2008":             "OlympicsBeijing2008",
    "coupe du monde 2022":      "FIFAWorldCup2022",
    "worldcup 2022":            "FIFAWorldCup2022",
    "coupe du monde 2018":      "FIFAWorldCup2018",
    "coupe du monde 2014":      "FIFAWorldCup2014",
    "wimbledon":                "Wimbledon2015",
    "roland garros":            "RolandGarros2022",
    "us open":                  "USOpen2015",
    "australian open":          "AustralianOpen2019",
    # Pays
    "jamaique":    "Jamaica",
    "etats-unis":  "UnitedStates",
    "usa":         "UnitedStates",
    "argentine":   "Argentina",
    "espagne":     "Spain",
    "france":      "France",
    "bresil":      "Brazil",
    "kenya":       "Kenya",
    "portugal":    "Portugal",
}

# --- Templates SPARQL --------------------------------------------------------
# Mapping intent (cle simple) -> template SPARQL
INTENT_TEMPLATES = {
    "medals": """
SELECT ?medal ?medalLabel WHERE {{
    <{ns}{e}> <{ns}wonMedal> ?medal .
    OPTIONAL {{ ?medal <http://www.w3.org/2000/01/rdf-schema#label> ?medalLabel }}
}}""",

    "competitions": """
SELECT ?comp WHERE {{
    <{ns}{e}> <{ns}participatedIn> ?comp .
}}""",

    "sport": """
SELECT ?sport WHERE {{
    <{ns}{e}> <{ns}practicesSport> ?sport .
}}""",

    "country": """
SELECT ?pays WHERE {{
    <{ns}{e}> <{ns}represents> ?pays .
}}""",

    "team": """
SELECT ?team WHERE {{
    <{ns}{e}> <{ns}memberOfTeam> ?team .
}}""",

    "rivals": """
SELECT ?rival WHERE {{
    <{ns}{e}> <{ns}hasCompeted> ?rival .
}}""",

    "nationality": """
SELECT ?compatriote WHERE {{
    <{ns}{e}> <{ns}sameNationality> ?compatriote .
}}""",

    "general": """
SELECT ?p ?o WHERE {{
    <{ns}{e}> ?p ?o .
    FILTER(!isLiteral(?o) || (LANG(?o) = "" || LANG(?o) = "en" || LANG(?o) = "fr"))
}}
LIMIT 20""",
}

# Mapping keyword -> intent (pour la detection NL)
KEYWORD_TO_INTENT = {
    r"medal|medaille|palmares":          "medals",
    r"particip|competition|compet|event": "competitions",
    r"sport|discipline|pratique|joue":    "sport",
    r"pays|national|represent|country":   "country",
    r"equipe|club|team":                  "team",
    r"rival|adversaire|concouru|competed":"rivals",
    r"compatriote|meme pays|nationali":   "nationality",
}


# =============================================================================
# Interface A : API simple attendue par les tests pytest
# =============================================================================

def build_query(intent: str, entity: str) -> str | None:
    """
    Interface simple attendue par les tests pytest.

    Parametres :
      intent  : cle du template ("medals", "competitions", "sport",
                "country", "team", "rivals", "nationality")
      entity  : ID interne de l'entite (ex: "UsainBolt")

    Retourne la requete SPARQL ou None si l'intent est inconnu.
    """
    if intent not in INTENT_TEMPLATES:
        return None  # intent inconnu -> les tests verifient ce cas
    template = INTENT_TEMPLATES[intent]
    return template.format(ns=NS_PREFIX, e=entity).strip()


def query_with_fallback(query: str, graph, entity: str = "") -> list:
    """
    Interface attendue par les tests sparql_executor.
    Execute la requete SPARQL sur un graphe rdflib et retourne une liste.
    Si 0 resultat, tente une requete generale sur l'entite.
    """
    try:
        resultats = list(graph.query(query))
        if resultats:
            return resultats
        # Fallback : requete generale
        if entity:
            fallback = INTENT_TEMPLATES["general"].format(ns=NS_PREFIX, e=entity).strip()
            return list(graph.query(fallback))
        return []
    except Exception:
        return []


# =============================================================================
# Interface B : QueryBuilder oriente NL (questions en langage naturel)
# =============================================================================

class QueryBuilder:
    """
    Construit des requetes SPARQL locales depuis des questions en langage naturel.
    Strategie principale : template matching.
    """

    def __init__(self, ns: str = NS_PREFIX):
        self.ns = ns
        self.entites_connues = ENTITES_CONNUES

    def detecter_entite(self, question: str) -> str | None:
        """
        Tente de detecter une entite nommee dans la question.
        Retourne l'ID interne (ex: "UsainBolt") ou None.
        """
        question_lower = question.lower()
        # Correspondance exacte d'abord (plus longue en premier)
        for libelle, entity_id in sorted(self.entites_connues.items(),
                                         key=lambda x: -len(x[0])):
            if libelle in question_lower:
                return entity_id
        # Fallback : mot capitalise
        mots_cap = re.findall(r"\b[A-Z][a-z]+\b", question)
        if mots_cap:
            return "".join(mots_cap[:2])
        return None

    def detecter_intention(self, question: str) -> str:
        """
        Identifie l'intent a utiliser a partir de la question.
        Retourne la cle du template.
        """
        question_lower = question.lower()
        for pattern, intent in KEYWORD_TO_INTENT.items():
            if re.search(pattern, question_lower):
                return intent
        return "general"

    def construire_requete(self, question: str) -> dict:
        """
        Point d'entree principal.
        Retourne un dict avec : query, entity, intention, fiabilite.
        """
        entite = self.detecter_entite(question)
        intention = self.detecter_intention(question)
        query = build_query(intention, entite) if entite else build_query("general", "")

        if not query:
            # Requete liste generale
            query = (
                f"SELECT ?athlete ?sport WHERE {{"
                f" ?athlete a <{self.ns}Athlete> ."
                f" ?athlete <{self.ns}practicesSport> ?sport ."
                f"}} LIMIT 20"
            )
            fiabilite = "basse"
            intention = "liste_generale"
        else:
            fiabilite = "haute" if intention != "general" else "basse"

        return {
            "question":  question,
            "entite":    entite,
            "intention": intention,
            "query":     query,
            "fiabilite": fiabilite,
        }

    def construire_fallback(self, entite: str) -> str:
        """Requete fallback si la requete principale retourne 0 resultat."""
        return INTENT_TEMPLATES["general"].format(ns=self.ns, e=entite).strip()


# --- Few-shot prompt LLM (Option B) ------------------------------------------

FEW_SHOT_PROMPT = """Genere une requete SPARQL pour interroger un Knowledge Graph local.
PREFIX : <http://monprojet.org/sports/>
Proprietes disponibles : wonMedal, participatedIn, represents, practicesSport,
memberOfTeam, hasCompeted, sameNationality, hostedBy, locatedIn, year.

Exemples :
Q: Quelles medailles a remporte Usain Bolt ?
A: SELECT ?medal WHERE {{ <http://monprojet.org/sports/UsainBolt> <http://monprojet.org/sports/wonMedal> ?medal . }}

Q: A quelles competitions a participe Serena Williams ?
A: SELECT ?comp WHERE {{ <http://monprojet.org/sports/SerenaWilliams> <http://monprojet.org/sports/participatedIn> ?comp . }}

Q: {question}
A:"""


def construire_requete_llm(question: str, client_llm) -> str | None:
    """
    Genere une requete SPARQL via few-shot prompting d'un LLM.
    Utilise en fallback si les templates ne correspondent pas.
    """
    prompt = FEW_SHOT_PROMPT.format(question=question)
    try:
        reponse = client_llm.completer(prompt, max_tokens=200, stop=["\n\n"])
        match = re.search(r"SELECT.*?(?=\n\n|$)", reponse, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(0).strip()
    except Exception as e:
        print(f"  Erreur LLM few-shot : {e}")
    return None


if __name__ == "__main__":
    # Test rapide du QueryBuilder + build_query
    qb = QueryBuilder()
    questions_test = [
        "Quelles medailles a remporte Usain Bolt ?",
        "A quelles competitions a participe Serena Williams ?",
        "Quel sport pratique Lionel Messi ?",
        "Quels athletes representent la France ?",
        "Qui sont les rivaux de Novak Djokovic ?",
    ]
    print("=" * 60)
    print("Test QueryBuilder (interface NL)")
    print("=" * 60)
    for q in questions_test:
        result = qb.construire_requete(q)
        print(f"\nQ: {q}")
        print(f"   Entite    : {result['entite']}")
        print(f"   Intention : {result['intention']}")
        print(f"   Requete   : {result['query'][:80]}...")

    print("\n" + "=" * 60)
    print("Test build_query (interface pytest)")
    print("=" * 60)
    for intent in ["medals", "competitions", "sport", "country", "intent_inconnu"]:
        q = build_query(intent, "UsainBolt")
        print(f"  intent={intent!r} -> {'None' if q is None else q[:60] + '...'}")
