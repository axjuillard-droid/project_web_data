"""
Phase 7 — LLM Client
=====================
Gère les appels aux APIs LLM (Gemini, OpenAI, Anthropic).
Sécurité : toutes les clés API viennent de .env via python-dotenv.

Usage (module) :
    from rag.llm_client import LLMClient
    client = LLMClient()
    reponse = client.generer(contexte, question)
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# Silence RDFLib date warnings (invalid dates like -1100-01-01)
logging.getLogger("rdflib.term").setLevel(logging.CRITICAL)

# Charger les variables d'environnement depuis .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ─── Prompt système ───────────────────────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """Tu es un assistant expert en sports et compétitions sportives.
Tu disposes de faits extraits d'un Knowledge Graph structuré sur les athlètes,
les compétitions, les palmarès et les disciplines sportives.

RÈGLES STRICTES :
1. Réponds UNIQUEMENT à partir des faits fournis dans la section FAITS ci-dessous.
2. Si les faits ne contiennent pas la réponse, dis-le EXPLICITEMENT :
   "Je ne dispose pas de cette information dans la Knowledge Base."
3. Cite chaque fait utilisé sous la forme : [sujet → prédicat → objet]
4. Ne génère AUCUN fait absent du contexte.
5. Si plusieurs interprétations sont possibles, donne-les toutes.

FAITS EXTRAITS DU KNOWLEDGE GRAPH :
{contexte}
"""


class LLMClient:
    """
    Client unifié pour les APIs LLM (OpenAI / Anthropic).
    Sélectionne automatiquement le fournisseur disponible.
    """

    def __init__(self, fournisseur: str | None = None):
        """
        fournisseur : "openai", "anthropic", ou None (auto-détection).
        """
        self.fournisseur = fournisseur or self._detecter_fournisseur()
        self.client = self._initialiser_client()

    def _detecter_fournisseur(self) -> str:
        """Détermine quel fournisseur utiliser selon les clés disponibles.
        Priorité : Gemini → OpenAI → Anthropic → simulation.
        """
        if GEMINI_API_KEY and len(GEMINI_API_KEY) > 10 and not GEMINI_API_KEY.startswith("YOUR"):
            return "gemini"
        if OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"):
            return "openai"
        if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.startswith("sk-ant-"):
            return "anthropic"
        print("  ⚠️  Aucune clé API valide trouvée dans .env")
        print("  → Mode simulation (réponses générées sans LLM)")
        return "simulation"

    def _initialiser_client(self):
        """Initialise le client API correspondant."""
        try:
            if self.fournisseur == "gemini":
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                # Utilisation de l'alias exact de votre liste
                model_name = "models/gemini-flash-latest"
                model = genai.GenerativeModel(model_name)
                print(f"  [LLMClient] Fournisseur : Google Gemini ({model_name})")
                return model
            elif self.fournisseur == "openai":
                from openai import OpenAI
                print("  [LLMClient] Fournisseur : OpenAI")
                return OpenAI(api_key=OPENAI_API_KEY)
            elif self.fournisseur == "anthropic":
                import anthropic
                print("  [LLMClient] Fournisseur : Anthropic")
                return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            else:
                print("  [LLMClient] Mode simulation")
                return None
        except ImportError as e:
            print(f"  ⚠️  Bibliothèque LLM non installée : {e}")
            print(f"      → Installer : pip install google-generativeai")
            self.fournisseur = "simulation"
            return None

    def generer(self, contexte: str, question: str,
                max_tokens: int = 800, temperature: float = 0.0) -> str:
        """
        Génère une réponse à la question en utilisant le contexte fourni.
        Retourne la réponse textuelle de l'assistant.
        """
        prompt_systeme = SYSTEM_PROMPT_TEMPLATE.format(contexte=contexte)

        if self.fournisseur == "gemini":
            return self._appel_gemini(prompt_systeme, question)
        elif self.fournisseur == "openai":
            return self._appel_openai(prompt_systeme, question, max_tokens, temperature)
        elif self.fournisseur == "anthropic":
            return self._appel_anthropic(prompt_systeme, question, max_tokens, temperature)
        elif self.fournisseur == "ollama":
            return self._appel_ollama(prompt_systeme, question)
        else:
            return self._simulation(contexte, question)

    def _appel_gemini(self, system_prompt: str, question: str) -> str:
        """Appel à l'API Google Gemini (gemini-1.5-flash — gratuit avec quota étudiant)."""
        try:
            # Gemini combine system prompt + question dans un seul message
            full_prompt = f"{system_prompt}\n\nQUESTION : {question}"
            response = self.client.generate_content(full_prompt)
            return response.text or ""
        except Exception as e:
            return f"[Erreur Gemini] {e}"

    def _appel_openai(self, system_prompt: str, question: str,
                      max_tokens: int, temperature: float) -> str:
        """Appel à l'API OpenAI (GPT-3.5-turbo ou GPT-4)."""
        try:
            response = self.client.chat.completions.create(
                model       = "gpt-3.5-turbo",  # remplacer par "gpt-4" si disponible
                messages    = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": question},
                ],
                max_tokens  = max_tokens,
                temperature = temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[Erreur OpenAI] {e}"

    def _appel_anthropic(self, system_prompt: str, question: str,
                         max_tokens: int, temperature: float) -> str:
        """Appel à l'API Anthropic (Claude)."""
        try:
            response = self.client.messages.create(
                model      = "claude-3-haiku-20240307",
                max_tokens = max_tokens,
                system     = system_prompt,
                messages   = [{"role": "user", "content": question}],
            )
            return response.content[0].text if response.content else ""
        except Exception as e:
            return f"[Erreur Anthropic] {e}"

    def _appel_ollama(self, system_prompt: str, question: str) -> str:
        """Appel à Ollama en local."""
        import requests
        try:
            url = "http://localhost:11434/api/generate"
            payload = {
                "model": "llama3",  # Modèle par défaut, ajustable
                "prompt": f"{system_prompt}\n\nQUESTION: {question}",
                "stream": False
            }
            res = requests.post(url, json=payload, timeout=120)
            res.raise_for_status()
            return res.json().get("response", "")
        except Exception as e:
            return f"[Erreur Ollama] {e} (Assurez-vous qu'Ollama tourne et que le modèle 'llama3' est installé avec 'ollama pull llama3')"

    def _simulation(self, contexte: str, question: str) -> str:
        """
        Mode simulation (sans API) : formule une réponse directement depuis le contexte.
        Utile pour tester le pipeline sans clé API.
        """
        if not contexte or "Aucune information" in contexte:
            return (
                f"[Simulation] Je ne dispose pas de cette information dans la "
                f"Knowledge Base pour répondre à : '{question}'"
            )
        lignes = [l for l in contexte.split("\n") if l.startswith("-")]
        if lignes:
            facts_str = "\n".join(lignes[:10])
            return (
                f"[Simulation — sans API LLM]\n"
                f"Basé sur les faits du Knowledge Graph :\n{facts_str}\n\n"
                f"Réponse à : '{question}'\n"
                f"Voici les informations disponibles dans la KB. "
                f"Pour une réponse en langage naturel, configurer une clé API dans .env"
            )
        return f"[Simulation] Aucun fait exploitable trouvé pour : '{question}'"


if __name__ == "__main__":
    # Test du client
    client = LLMClient()
    print(f"Fournisseur actif : {client.fournisseur}")
    contexte_test = """- UsainBolt → wonMedal → Gold Medal
- UsainBolt → participatedIn → Olympics Beijing 2008
- UsainBolt → practicesSport → Athletics
- UsainBolt → represents → Jamaica"""
    reponse = client.generer(contexte_test, "Qui est Usain Bolt et quelles médailles a-t-il remportées ?")
    print(f"\nRéponse LLM :\n{reponse}")
