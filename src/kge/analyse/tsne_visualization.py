"""
Phase 6 — Analyse KGE : Clustering t-SNE
==========================================
Ce script :
  1. Charge les embeddings d'un modèle entraîné
  2. Applique t-SNE pour réduire la dimensionnalité à 2D
  3. Colorie les entités par classe ontologique (Athlete, Competition, Country…)
  4. Sauvegarde la visualisation en PNG

Usage :
    python kge/analyse/tsne_visualization.py [--model TransE]

Prérequis :
    - kge/results/<modele>/ doit exister (Phase 6 entraînement)
    - pip install scikit-learn matplotlib
"""

import argparse
import json
from pathlib import Path

# Monkeypatch global pour class_resolver (fix TypeError dans pykeen avec certaines versions de conda)
import class_resolver.func
if not hasattr(class_resolver.func.FunctionResolver, "__class_getitem__"):
    class_resolver.func.FunctionResolver.__class_getitem__ = lambda cls, x: cls

import numpy as np
import matplotlib
matplotlib.use("Agg")  # mode non-interactif (compatible serveur)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from sklearn.manifold import TSNE

# ─── Chemins ────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent.parent.parent
BASE_DIR    = ROOT / "models" / "kge_analyse"
RESULTS_DIR = ROOT / "models" / "kge_results" / "results"
PNG_OUT     = BASE_DIR / "tsne_entities.png"
STATS_OUT   = BASE_DIR / "tsne_stats.json"

# ─── Couleurs par classe ontologique ─────────────────────────────────────────
NS_LOCAL = "http://monprojet.org/sports/"
WD_URI   = "http://www.wikidata.org/entity/"

CLASSES_COULEURS = {
    "Athlete":     "#E63946",   # rouge vif
    "Competition": "#457B9D",   # bleu acier
    "Country":     "#2A9D8F",   # vert sarcelle
    "Sport":       "#F4A261",   # orange
    "Team":        "#9B5DE5",   # violet
    "City":        "#F7B731",   # jaune doré
    "Medal":       "#81B29A",   # vert sauge
    "Wikidata":    "#AAAAAA",   # gris clair
    "Autre":       "#CCCCCC",   # gris très clair
}

# Suffixes des URIs locales par classe
CLASSIFICATION_PATTERNS = {
    "Athlete":     {"UsainBolt", "SerenaWilliams", "LionelMessi", "MichaelPhelps",
                    "SimoneBiles", "RogerFederer", "RafaelNadal", "NovakDjokovic",
                    "EliudKipchoge", "CristianoRonaldo", "KylianMbappe", "LeBronJames",
                    "MoFarah", "MichaelJordan", "NadiaComaneci", "TigerWoods",
                    "Pele", "MuhammadAli", "CarlLewis", "ValentinaVezzali"},
    "Competition": {"Olympics", "FIFAWorldCup", "Wimbledon", "RolandGarros",
                    "AustralianOpen", "USOpen", "TourDeFrance", "BerlinMarathon",
                    "WorldAthletics"},
    "Country":     {"Jamaica", "UnitedStates", "Argentina", "Switzerland", "Spain",
                    "Serbia", "France", "Brazil", "Portugal", "Kenya", "China",
                    "UnitedKingdom", "Germany", "Russia", "Qatar", "Japan",
                    "Italy", "Greece", "SouthAfrica", "Australia", "Romania"},
    "Sport":       {"Athletics", "Tennis", "Football", "Swimming", "Gymnastics",
                    "Basketball", "Boxing", "Golf", "Cycling", "Fencing"},
    "Team":        {"FootballTeam", "BasketballTeam"},
    "Medal":       {"GoldMedal", "SilverMedal", "BronzeMedal"},
    "City":        {"Beijing", "London", "Rio", "Tokyo", "Paris", "Moscow",
                    "Berlin", "Athens", "Melbourne", "NewYork", "Doha"},
}


def classifier_entite(uri: str) -> str:
    """Détermine la classe d'une entité à partir de son URI."""
    libelle = uri.split("/")[-1]
    # Entités locales
    if NS_LOCAL in uri:
        for classe, patterns in CLASSIFICATION_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in libelle.lower():
                    return classe
        return "Autre"
    # Entités Wikidata
    if WD_URI in uri:
        return "Wikidata"
    return "Autre"


def charger_embeddings(modele_dir: Path) -> tuple:
    """
    Charge les embeddings du modèle PyKEEN.
    Priorité : entity_embeddings.npy (export Colab rapide) → trained_model.pkl.
    Retourne (embeddings_np, liste_uri, triples_factory).
    """
    import torch

    # ── Chemin rapide : fichiers .npy exportés depuis Colab ─────────────────
    npy_path  = modele_dir / "entity_embeddings.npy"
    e2id_path = modele_dir.parent / "entity_to_id.json"   # kge/results/entity_to_id.json

    if npy_path.exists():
        print(f"  Chargement rapide (.npy) : {npy_path}")
        embeddings = np.load(str(npy_path))

        if e2id_path.exists():
            with open(e2id_path, encoding="utf-8") as f:
                entity_to_id = json.load(f)
            id_to_entity = {v: k for k, v in entity_to_id.items()}
            uris = [id_to_entity.get(i, f"entity_{i}") for i in range(len(embeddings))]
        else:
            uris = [f"entity_{i}" for i in range(len(embeddings))]

        print(f"  → {embeddings.shape[0]:,} entités · {embeddings.shape[1]} dimensions")
        return embeddings, uris, None

    # ── Chemin complet : charger le .pkl du modèle ──────────────────────────
    model_path = modele_dir / "trained_model.pkl"
    if not model_path.exists():
        print(f"  ❌ Ni entity_embeddings.npy ni trained_model.pkl trouvés dans {modele_dir}")
        return None, None, None

    print(f"  Chargement de {model_path}...")
    model = None
    try:
        # weights_only=False nécessaire pour les modèles PyKEEN (pickle complet)
        model = torch.load(str(model_path), map_location="cpu", weights_only=False)
    except Exception as e:
        print(f"  [ERREUR] torch.load (weights_only=False) : {e}")
        return None, None, None

    model.eval()

    # Embeddings des entités
    with torch.no_grad():
        embeddings = model.entity_representations[0]().detach().numpy()

    # Index entités — priorité : entity_to_id.json → triples_factory → entity_X
    tf = model.triples_factory if hasattr(model, "triples_factory") else None
    if tf:
        id_to_entity = {v: k for k, v in tf.entity_to_id.items()}
        uris = [id_to_entity.get(i, f"entity_{i}") for i in range(len(embeddings))]
    elif e2id_path.exists():
        with open(e2id_path, encoding="utf-8") as f:
            entity_to_id = json.load(f)
        id_to_entity = {v: k for k, v in entity_to_id.items()}
        uris = [id_to_entity.get(i, f"entity_{i}") for i in range(len(embeddings))]
    else:
        uris = [f"entity_{i}" for i in range(len(embeddings))]

    print(f"  → {embeddings.shape[0]:,} entités · {embeddings.shape[1]} dimensions")
    return embeddings, uris, tf


def appliquer_tsne(embeddings: np.ndarray, perplexite: int = 30,
                   n_iter: int = 1000, seed: int = 42) -> tuple:
    """Applique t-SNE pour projeter les embeddings en 2D."""
    # Limiter le nombre d'entités pour la visualisation (t-SNE est lent sur > 5000 points)
    max_entites = 3000
    if len(embeddings) > max_entites:
        print(f"  Sous-échantillonnage : {len(embeddings):,} → {max_entites:,} entités")
        indices = np.random.RandomState(seed).choice(len(embeddings), max_entites, replace=False)
        embeddings_sub = embeddings[indices]
        # Appliquer t-SNE directement sur le sous-ensemble (pas de récursion)
        print(f"  Application t-SNE (perplexité={perplexite}, n_iter={n_iter})...")
        tsne = TSNE(
            n_components=2,
            perplexity=perplexite,
            n_iter=n_iter,
            random_state=seed,
            verbose=1,
        )
        coords = tsne.fit_transform(embeddings_sub)
        return coords, indices

    print(f"  Application t-SNE (perplexité={perplexite}, n_iter={n_iter})...")
    tsne = TSNE(
        n_components=2,
        perplexity=perplexite,
        n_iter=n_iter,
        random_state=seed,
        verbose=1,
    )
    coords = tsne.fit_transform(embeddings)
    return coords, None


def visualiser(coords: np.ndarray, uris: list, modele_nom: str) -> dict:
    """Crée et sauvegarde la visualisation t-SNE."""
    # Classifier les entités
    classes = [classifier_entite(uri) for uri in uris]
    couleurs = [CLASSES_COULEURS.get(c, "#CCCCCC") for c in classes]

    # Compter les entités par classe
    from collections import Counter
    comptes = Counter(classes)

    # Créer la figure
    fig, ax = plt.subplots(figsize=(16, 12), dpi=150)
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    # Tracer les points (sans légende d'abord pour performance)
    sc = ax.scatter(
        coords[:, 0], coords[:, 1],
        c=couleurs,
        s=8,
        alpha=0.7,
        linewidths=0,
    )

    # Légende
    patches = [
        mpatches.Patch(color=couleur, label=f"{classe} ({comptes.get(classe, 0)})")
        for classe, couleur in CLASSES_COULEURS.items()
        if comptes.get(classe, 0) > 0
    ]
    legend = ax.legend(
        handles=patches,
        loc="upper right",
        fontsize=9,
        framealpha=0.3,
        facecolor="#0f3460",
        edgecolor="#e94560",
        labelcolor="white",
    )

    # Annoter quelques entités clés
    entites_cles = {
        "http://monprojet.org/sports/UsainBolt":       "Usain Bolt",
        "http://monprojet.org/sports/SerenaWilliams":  "Serena Williams",
        "http://monprojet.org/sports/LionelMessi":     "L. Messi",
        "http://monprojet.org/sports/MichaelPhelps":   "M. Phelps",
        "http://monprojet.org/sports/OlympicsParis2024": "JO Paris 2024",
        "http://monprojet.org/sports/FIFAWorldCup2022": "CM 2022",
    }
    for i, uri in enumerate(uris):
        if uri in entites_cles:
            ax.annotate(
                entites_cles[uri],
                (coords[i, 0], coords[i, 1]),
                fontsize=7,
                color="white",
                fontweight="bold",
                xytext=(5, 5),
                textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.2", fc="#e94560", alpha=0.7),
            )

    # Titre et labels
    ax.set_title(
        f"t-SNE des entités du Knowledge Graph — {modele_nom}\n"
        f"({len(uris):,} entités · colorées par classe ontologique)",
        color="white", fontsize=14, fontweight="bold", pad=15,
    )
    ax.set_xlabel("Dimension t-SNE 1", color="#aaaaaa", fontsize=10)
    ax.set_ylabel("Dimension t-SNE 2", color="#aaaaaa", fontsize=10)
    ax.tick_params(colors="#aaaaaa")
    for spine in ax.spines.values():
        spine.set_edgecolor("#333366")

    plt.tight_layout()
    plt.savefig(str(PNG_OUT), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  ✅ {PNG_OUT}")

    return dict(comptes)


def main():
    parser = argparse.ArgumentParser(description="Visualisation t-SNE des embeddings KGE")
    parser.add_argument("--model", default="TransE", help="Nom du modèle (défaut: TransE)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"Phase 6 — Visualisation t-SNE ({args.model})")
    print("=" * 60)

    modele_dir = RESULTS_DIR / args.model
    if not modele_dir.exists():
        print(f"❌ Modèle {args.model} non trouvé — exécuter train_kge.py d'abord")
        return

    print(f"\n[1/3] Chargement des embeddings...")
    embeddings, uris, tf = charger_embeddings(modele_dir)
    if embeddings is None:
        return

    print(f"\n[2/3] Application t-SNE...")
    result = appliquer_tsne(embeddings)
    if isinstance(result, tuple) and len(result) == 2:
        coords, indices = result
        if indices is not None:
            uris = [uris[i] for i in indices]
    else:
        coords = result
        indices = None

    print(f"\n[3/3] Génération de la visualisation...")
    comptes = visualiser(coords, uris, args.model)

    # Export stats
    with open(STATS_OUT, "w", encoding="utf-8") as f:
        json.dump({"modele": args.model, "entites_par_classe": comptes}, f, indent=2)
    print(f"  ✅ {STATS_OUT}")

    print(f"\n📊 Entités par classe :")
    for classe, n in sorted(comptes.items(), key=lambda x: -x[1]):
        print(f"   {classe:<15} : {n}")

    print(f"\n🔍 Questions d'analyse :")
    print("   - Les athlètes forment-ils un cluster distinct des compétitions ?")
    print("   - Les entités du même sport se regroupent-elles ?")
    print("   - Les entités Wikidata sont-elles proches des entités locales alignées ?")
    print("   - Si aucun clustering clair → observer et documenter (c'est valide) !")


if __name__ == "__main__":
    main()
