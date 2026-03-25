"""
Phase 7 - SPARQL Executor : Execution des requetes sur la KB locale
====================================================================
Ce module :
  1. Charge la KB etendue avec rdflib
  2. Execute les requetes SPARQL sur la KB locale
  3. Gere le fallback si 0 resultat
  4. Formate les resultats en contexte lisible pour le LLM

Usage (module) :
    from rag.sparql_executor import SPARQLExecutor
    executor = SPARQLExecutor()
    triplets = executor.executer("SELECT ?p ?o WHERE { <:UsainBolt> ?p ?o }")
"""

import re
from pathlib import Path
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.plugins.sparql.processor import SPARQLResult

# --- Chemins ----------------------------------------------------------------
BASE_DIR = Path(__file__).parent
KB_DIR   = Path(__file__).parent.parent.parent / "kg_artifacts"
NS       = Namespace("http://monprojet.org/sports/")

# Preference de KB : etendue > initiale
KB_PRIORITE = [
    Path(__file__).parent.parent.parent / "kg_artifacts" / "expanded.ttl",
    Path(__file__).parent.parent.parent / "kg_artifacts" / "knowledge_base_v1.ttl",
]


def libelle_court(uri_str: str) -> str:
    """Convertit une URI en libelle court lisible (derniere partie)."""
    uri_str = str(uri_str)
    if "/" in uri_str:
        partie = uri_str.split("/")[-1]
    elif "#" in uri_str:
        partie = uri_str.split("#")[-1]
    else:
        partie = uri_str
    # Convertir camelCase -> mots separes
    return re.sub(r"([A-Z])", r" \1", partie).strip()


def formater_valeur(val) -> str:
    """Formate une valeur RDF (URI ou Literal) en texte lisible."""
    if isinstance(val, URIRef):
        return libelle_court(str(val))
    elif isinstance(val, Literal):
        return str(val)
    return str(val)


# ---------------------------------------------------------------------------
# Interface module-level attendue par les tests pytest
# ---------------------------------------------------------------------------

def query_with_fallback(query: str, graph, entity: str = "") -> list:
    """
    Execute la requete SPARQL sur un graphe rdflib.
    En cas de 0 resultat, tente une requete generale sur l'entite.
    Retourne une liste de tuples (resultats bruts rdflib).
    """
    try:
        results = list(graph.query(query))
        if results:
            return results
        # Fallback si 0 resultat
        if entity:
            ns = "http://monprojet.org/sports/"
            fallback = f"""
                SELECT ?p ?o WHERE {{
                    <{ns}{entity}> ?p ?o .
                    FILTER(!isLiteral(?o) || LANG(?o) = "" || LANG(?o) = "fr")
                }} LIMIT 20"""
            return list(graph.query(fallback))
        return []
    except Exception:
        return []


class SPARQLExecutor:
    """Execute des requetes SPARQL sur la KB locale via rdflib."""

    def __init__(self):
        self.g = None
        self.kb_path = None
        self._charger_kb()

    def _charger_kb(self) -> None:
        """Charge la KB disponible (etendue en priorite)."""
        for kb_path in KB_PRIORITE:
            if kb_path.exists():
                print(f"  [SPARQLExecutor] Chargement de {kb_path.name}...")
                self.g = Graph()
                # On force utf-8 si possible, mais ici on reste simple
                self.g.parse(str(kb_path), format="turtle")
                self.g.bind("", NS)
                print(f"  -> {len(self.g):,} triplets charges")
                self.kb_path = kb_path
                return
        print("  [SPARQLExecutor] Aucune KB disponible - reponses vides")
        self.g = Graph()
        self.kb_path = None

    def recharger_kb(self) -> None:
        """Force le rechargement de la KB."""
        self._charger_kb()

    def executer(self, query: str) -> list[dict]:
        """
        Execute une requete SPARQL SELECT sur la KB locale.
        Retourne une liste de dicts {variable: valeur}.
        """
        if self.g is None:
            return []
        try:
            resultats = self.g.query(query)
            rows = []
            for row in resultats:
                if hasattr(row, "asdict"):
                    rows.append({k: formater_valeur(v) for k, v in row.asdict().items()})
                elif hasattr(row, "_fields"):
                    rows.append({f: formater_valeur(getattr(row, f)) for f in row._fields})
                else:
                    rows.append({"valeur": formater_valeur(row)})
            return rows
        except Exception as e:
            print(f"  Erreur SPARQL : {e}")
            return []

    def executer_avec_fallback(self, query: str, entite: str) -> tuple[list, bool]:
        """
        Execute la requete et applique un fallback si 0 resultat.
        Retourne (results, est_fallback).
        """
        results = self.executer(query)
        # La condition 'if results' est requise par les tests
        if results:
            return results, False

        # Fallback : requete generale sur l'entite
        fallback_query = f"""
SELECT ?p ?o WHERE {{
    <{NS}{entite}> ?p ?o .
    FILTER(!isLiteral(?o) || (LANG(?o) = "" || LANG(?o) = "en" || LANG(?o) = "fr"))
}} LIMIT 20
"""
        results_fallback = self.executer(fallback_query)
        return results_fallback, True

    def formater_contexte(self, results: list[dict], entite: str | None = None,
                          est_fallback: bool = False) -> str:
        """
        Formate les resultats en contexte structure pour le LLM.
        Ce texte permet au LLM de citer ses sources.
        """
        if not results:
            msg = f"Aucune information trouvee"
            if entite:
                msg += f" sur {entite}"
            return msg

        lignes = []
        if est_fallback:
            lignes.append(f"[Informations generales - requete elargie]")

        # Limiter a 50 triplets
        results_affiches = results[:50]
        for row in results_affiches:
            if entite and len(row) == 1:
                val = list(row.values())[0]
                lignes.append(f"- {entite} -> {list(row.keys())[0]} -> {val}")
            elif len(row) == 2 and "p" in row and "o" in row:
                lignes.append(f"- {entite or '?'} -> {row['p']} -> {row['o']}")
            else:
                parts = " | ".join(f"{k}={v}" for k, v in row.items())
                lignes.append(f"- {parts}")

        return "\n".join(lignes)


if __name__ == "__main__":
    ex = SPARQLExecutor()
    query = f"SELECT ?p ?o WHERE {{ <{NS}UsainBolt> ?p ?o }} LIMIT 5"
    res = ex.executer(query)
    print(ex.formater_contexte(res, "UsainBolt"))
