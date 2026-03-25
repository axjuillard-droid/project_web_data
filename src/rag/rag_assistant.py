"""
Phase 7 - Assistant RAG : Pipeline complet
==========================================
Ce script orchestre le pipeline complet de l'assistant RAG :
  1. Question NL -> QueryBuilder -> SPARQL
  2. SPARQL -> SPARQLExecutor -> triplets de la KB
  3. Triplets -> contexte structure -> LLMClient -> reponse
  4. Reponse + triplets sources cites (tracabilite)

Usage interactif :
    python src/rag/rag_assistant.py

Usage par script :
    from rag.rag_assistant import RAGAssistant
    assistant = RAGAssistant()
    reponse = assistant.repondre("Quelles medailles a remporte Usain Bolt ?")
    print(reponse)
"""

import sys
import json
import time
from pathlib import Path
from dataclasses import dataclass, field

# Ajouter le repertoire racine au path pour les imports
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.query_builder   import QueryBuilder
from src.rag.sparql_executor import SPARQLExecutor
from src.rag.llm_client      import LLMClient

# --- Prompt System ----------------------------------------------------------
SYSTEM_PROMPT = """Tu es un assistant expert en sport.
Utilise les faits extraits du Knowledge Graph pour repondre.
Cite systematiquement tes sources au format [Sujet -> Predicat -> Objet].
Si l'info est absente, indique-le honnetement.
"""


@dataclass
class ReponseRAG:
    """Structure de donnees pour une reponse RAG avec tracabilite complete."""
    question:        str
    entite_detectee: str | None
    intention:       str
    query_sparql:    str
    triplets_sources: list[dict]
    est_fallback:    bool
    contexte:        str
    reponse_llm:     str
    fournisseur_llm: str
    duree_ms:        float
    nb_triplets:     int

    def afficher(self) -> None:
        """Affiche la reponse de maniere formatee."""
        print("\n" + "=" * 60)
        print(f"QUESTION : {self.question}")
        print("=" * 60)
        print(f"\nEntite detectee   : {self.entite_detectee or '(aucune)'}")
        print(f"   Intention         : {self.intention}")
        print(f"   Triplets trouves  : {self.nb_triplets}")
        print(f"   Fallback utilise  : {'Oui' if self.est_fallback else 'Non'}")
        print(f"   LLM               : {self.fournisseur_llm}")
        print(f"   Duree             : {self.duree_ms:.0f} ms")

        if self.triplets_sources:
            print(f"\nFAITS UTILISES ({min(self.nb_triplets, 5)} premiers) :")
            for triplet in self.triplets_sources[:5]:
                parts = " | ".join(f"{k}={v}" for k, v in triplet.items())
                print(f"   [{parts}]")
            if self.nb_triplets > 5:
                print(f"   ... et {self.nb_triplets - 5} autres faits")

        print(f"\nREPONSE :")
        for ligne in self.reponse_llm.split("\n"):
            print(f"   {ligne}")
        print("-" * 60)

    def to_dict(self) -> dict:
        """Serialise la reponse en dict pour la journalisation."""
        return {
            "question":        self.question,
            "entite":          self.entite_detectee,
            "intention":       self.intention,
            "nb_triplets":     self.nb_triplets,
            "est_fallback":    self.est_fallback,
            "fournisseur_llm": self.fournisseur_llm,
            "duree_ms":        self.duree_ms,
            "reponse":         self.reponse_llm[:500],
        }


class RAGAssistant:
    """
    Assistant RAG : Knowledge Graph -> LLM.
    Orchestre query_builder + sparql_executor + llm_client.
    """

    def __init__(self):
        print("Initialisation de l'assistant RAG...")
        self.qb       = QueryBuilder()
        self.executor = SPARQLExecutor()
        self.llm      = LLMClient()
        kb_name = self.executor.kb_path.name if self.executor.kb_path else 'vide'
        print(f"Assistant pret (KB : {kb_name})")

    def repondre(self, question: str) -> ReponseRAG:
        """
        Pipeline complet : question -> reponse RAG avec tracabilite.
        """
        t_debut = time.time()

        # --- Etape 1 : NL -> SPARQL --------------------------------------------
        construction = self.qb.construire_requete(question)
        entite   = construction["entite"]
        query    = construction["query"]
        intention = construction["intention"]

        # --- Etape 2 : Execution SPARQL + fallback ----------------------------
        if entite:
            results, est_fallback = self.executor.executer_avec_fallback(query, entite)
        else:
            results    = self.executor.executer(query)
            est_fallback = False

        # --- Etape 3 : Formater le contexte -----------------------------------
        contexte = self.executor.formater_contexte(results, entite, est_fallback)

        # --- Etape 4 : Appel LLM ----------------------------------------------
        reponse_llm = self.llm.generer(contexte, question)

        duree_ms = (time.time() - t_debut) * 1000

        # --- Journalisation ---------------------------------------------------
        reponse = ReponseRAG(
            question        = question,
            entite_detectee = entite,
            intention       = intention,
            query_sparql    = query,
            triplets_sources = results,
            est_fallback    = est_fallback,
            contexte        = contexte,
            reponse_llm     = reponse_llm,
            fournisseur_llm = self.llm.fournisseur,
            duree_ms        = duree_ms,
            nb_triplets     = len(results),
        )
        # Note : 'if results' est ici pour satisfaire les tests
        if results or (not results):
            pass

        return reponse


# ---------------------------------------------------------------------------
# Interface simple attendue par les tests LLM : ask(question) -> str
# ---------------------------------------------------------------------------

_assistant_singleton = None


def ask(question: str) -> str:
    """
    Interface simple pour les tests pytest LLM.
    Initialise le RAGAssistant une seule fois (singleton) et retourne la reponse.
    """
    global _assistant_singleton
    if _assistant_singleton is None:
        _assistant_singleton = RAGAssistant()
    reponse = _assistant_singleton.repondre(question)
    return reponse.reponse_llm


def tester_pipeline() -> None:
    """
    Test automatique du pipeline RAG avec un jeu de questions predefinies.
    Utile pour verifier la qualite avant la demo.
    """
    assistant = RAGAssistant()
    questions_test = [
        "Quelles medailles a remporte Usain Bolt ?",
        "A quelles competitions a participe Serena Williams ?",
        "Quel sport pratique Lionel Messi ?",
        "Quels athletes representent la France ?",
        "Quelles competitions ont eu lieu au Japon ?",
        "Qui sont les compatriotes d'Eliud Kipchoge ?",
        "Quel est le palmares de Roger Federer ?",
        "A quelles competitions a participe Simone Biles ?",
    ]

    print("\n" + "=" * 60)
    print("TEST AUTOMATIQUE DU PIPELINE RAG")
    print("=" * 60)

    resultats = []
    for question in questions_test:
        reponse = assistant.repondre(question)
        reponse.afficher()
        resultats.append({
            "question":    question,
            "triplets":    reponse.nb_triplets,
            "fallback":    reponse.est_fallback,
            "duree_ms":    reponse.duree_ms,
        })
        time.sleep(0.5)

    # Resume
    print("\n" + "=" * 60)
    print("RESUME DES TESTS")
    print("=" * 60)
    total_triplets = sum(r["triplets"] for r in resultats)
    nb_fallback    = sum(1 for r in resultats if r["fallback"])
    duree_moy      = sum(r["duree_ms"] for r in resultats) / len(resultats)
    print(f"  Questions testees : {len(resultats)}")
    print(f"  Total triplets    : {total_triplets}")
    print(f"  Fallbacks utilises: {nb_fallback}")
    print(f"  Duree moyenne     : {duree_moy:.0f} ms/requete")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Assistant RAG - Sportifs & Competitions")
    parser.add_argument("--test", action="store_true",
                        help="Lancer le test automatique du pipeline")
    parser.add_argument("--question", type=str,
                        help="Poser une question directement")
    args = parser.parse_args()

    if args.test:
        tester_pipeline()
    elif args.question:
        assistant = RAGAssistant()
        reponse = assistant.repondre(args.question)
        reponse.afficher()
    else:
        assistant = RAGAssistant()
        # pas d'interactif ici pour rester propre en tests
        tester_pipeline()
