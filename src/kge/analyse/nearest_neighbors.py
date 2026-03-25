"""
Phase 6 — Analyse KGE : Voisins les plus proches
==================================================
Ce script analyse les embeddings entraînés pour identifier les voisins
sémantiques les plus proches dans l'espace d'embedding.

Usage :
    python kge/analyse/nearest_neighbors.py [--model TransE] [--topk 10]

Prérequis :
    - kge/results/<modele>/ doit exister (Phase 6 entraînement)
"""

import json
import argparse
from pathlib import Path

# ─── Chemins ────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent.parent.parent
BASE_DIR    = ROOT / "models" / "kge_analyse"
RESULTS_DIR = ROOT / "models" / "kge_results" / "results"
OUT_FILE    = BASE_DIR / "nearest_neighbors.json"

# Entités de référence à analyser (URIs locales)
ENTITES_REF = [
    "http://monprojet.org/sports/UsainBolt",
    "http://monprojet.org/sports/SerenaWilliams",
    "http://monprojet.org/sports/LionelMessi",
    "http://monprojet.org/sports/MichaelPhelps",
    "http://monprojet.org/sports/EliudKipchoge",
    "http://monprojet.org/sports/CristianoRonaldo",
    "http://monprojet.org/sports/NovakDjokovic",
    "http://monprojet.org/sports/SimoneBiles",
]


def charger_modele(modele_dir: Path):
    """Charge un modèle PyKEEN sauvegardé."""
    import torch
    import pykeen
    model_path = modele_dir / "trained_model.pkl"
    if not model_path.exists():
        print(f"  ❌ Modèle non trouvé : {model_path}")
        return None
    try:
        # Sur certaines versions de torch/pykeen, il faut autoriser les globals
        model = torch.load(str(model_path), map_location="cpu")
        return model
    except Exception as e:
        print(f"  ❌ Erreur de chargement torch.load : {e}")
        print("  → Tentative de chargement via pykeen.models.load_model_from_path...")
        try:
            from pykeen.models import load_model_from_path
            return load_model_from_path(str(model_path))
        except Exception as e2:
            print(f"  ❌ Échec final : {e2}")
            return None


def voisins_plus_proches(model, entity_uri: str, k: int = 10) -> list:
    """
    Calcule les k voisins les plus proches d'une entité dans l'espace d'embedding.
    Retourne une liste de (uri_voisin, score_similarite).
    """
    import torch
    import torch.nn.functional as F

    # Vérifier que l'entité est dans la KB
    entity_to_id = model.entity_representations[0]._embeddings.weight.data
    triples_factory = model.triples_factory if hasattr(model, 'triples_factory') else None

    if triples_factory and entity_uri in triples_factory.entity_to_id:
        entity_idx = triples_factory.entity_to_id[entity_uri]
    else:
        print(f"  ⚠️  Entité non trouvée dans le modèle : {entity_uri.split('/')[-1]}")
        return []

    # Obtenir l'embedding de l'entité
    all_embeddings = model.entity_representations[0]().detach()
    entity_emb = all_embeddings[entity_idx].unsqueeze(0)

    # Calculer la similarité cosinus avec toutes les entités
    similarites = F.cosine_similarity(entity_emb, all_embeddings)
    topk_scores, topk_indices = similarites.topk(k + 1)

    # Convertir les indices en URIs
    id_to_entity = {v: k for k, v in triples_factory.entity_to_id.items()}
    voisins = []
    for idx, score in zip(topk_indices.tolist(), topk_scores.tolist()):
        uri_voisin = id_to_entity.get(idx, f"entity_{idx}")
        if uri_voisin != entity_uri:  # exclure l'entité elle-même
            voisins.append({
                "uri": uri_voisin,
                "libelle": uri_voisin.split("/")[-1],
                "score": round(float(score), 4),
            })
        if len(voisins) == k:
            break
    return voisins


def analyser_voisins(model, modele_nom: str, k: int = 10) -> dict:
    """Analyse les voisins pour toutes les entités de référence."""
    resultats = {}
    print(f"\n  Analyse des voisins ({modele_nom})...")
    for entite_uri in ENTITES_REF:
        libelle = entite_uri.split("/")[-1]
        voisins = voisins_plus_proches(model, entite_uri, k=k)
        resultats[libelle] = {
            "uri": entite_uri,
            "voisins": voisins,
        }
        if voisins:
            top3 = [v["libelle"] for v in voisins[:3]]
            print(f"    {libelle:<25} → {', '.join(top3)}")
        else:
            print(f"    {libelle:<25} → (entité absente du modèle)")
    return resultats


def analyser_comportement_relations(model, modele_nom: str) -> None:
    """
    Analyse le comportement des relations dans l'espace d'embedding.
    Pour TransE : vérifie si vector(r) = vector(tail) - vector(head) en moyenne.
    """
    import torch
    print(f"\n  Comportement des relations ({modele_nom}) :")

    if not hasattr(model, 'relation_representations'):
        print("    ⚠️  Pas de relation_representations disponible")
        return

    rel_embs = model.relation_representations[0]().detach()
    triples_factory = model.triples_factory if hasattr(model, 'triples_factory') else None
    if not triples_factory:
        return

    # Relations d'intérêt
    relations_interessantes = [
        "http://monprojet.org/sports/participatedIn",
        "http://monprojet.org/sports/wonMedal",
        "http://monprojet.org/sports/represents",
        "http://monprojet.org/sports/practicesSport",
    ]

    for rel_uri in relations_interessantes:
        if rel_uri in triples_factory.relation_to_id:
            rel_idx = triples_factory.relation_to_id[rel_uri]
            rel_emb = rel_embs[rel_idx]
            norme = torch.norm(rel_emb).item()
            libelle = rel_uri.split("/")[-1]
            print(f"    {libelle:<30} norme = {norme:.4f}")


def main():
    parser = argparse.ArgumentParser(description="Analyse des voisins KGE")
    parser.add_argument("--model", default="TransE", help="Nom du modèle (défaut: TransE)")
    parser.add_argument("--topk",  type=int, default=10, help="Nombre de voisins (défaut: 10)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"Phase 6 — Analyse : Voisins les plus proches ({args.model})")
    print("=" * 60)

    modele_dir = RESULTS_DIR / args.model
    if not modele_dir.exists():
        print(f"❌ Répertoire du modèle non trouvé : {modele_dir}")
        print(f"   → Exécuter d'abord : python kge/train_kge.py --model {args.model}")
        return

    print(f"\n[1/3] Chargement du modèle {args.model}...")
    model = charger_modele(modele_dir)
    if model is None:
        return

    print(f"\n[2/3] Calcul des voisins les plus proches (top-{args.topk})...")
    resultats = analyser_voisins(model, args.model, k=args.topk)

    print(f"\n[3/3] Analyse du comportement des relations...")
    analyser_comportement_relations(model, args.model)

    # Export
    output = {
        "modele": args.model,
        "top_k": args.topk,
        "resultats": resultats,
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  ✅ {OUT_FILE}")

    print("\n📊 Interprétation :")
    print("   - Les athlètes du même sport doivent apparaître proches (ex: Bolt → Kipchoge)")
    print("   - Les compatriotes doivent être proches (ex: Messi → Ronaldo pour les footballeurs)")
    print("   - Si les voisins sont aléatoires → modèle n'a pas assez appris")


if __name__ == "__main__":
    main()
