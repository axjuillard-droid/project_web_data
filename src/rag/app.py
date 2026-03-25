import streamlit as st
import sys
import json
import random
from pathlib import Path
import os
import pandas as pd

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.rag_assistant import RAGAssistant

# Configurer la page (le thème sombre est forcé par .streamlit/config.toml)
st.set_page_config(page_title="RAG Sports Assistant", page_icon="🏅", layout="wide")

# Chemins des données
STATS_KB_PATH = ROOT / "kg_artifacts" / "stats_kb.json"
COMPARAISON_KGE_PATH = ROOT / "models" / "kge_results" / "results" / "comparaison_modeles.json"

st.title("🏆 Knowledge Graph & RAG Assistant")
st.markdown("Interface professionnelle pour interroger la base de connaissances via LLM et analyser les KGE.")

# --- INITIALISATION ET ETAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar Navigation
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/Streamlit_logo.png/640px-Streamlit_logo.png", width=150)
    st.header("Navigation")
    page = st.radio("Menu", ["💬 Assistant RAG", "🔮 Link Prediction (KGE)", "📊 Dashboard & Statistiques"])

# =====================================================================
# PAGE 1 : ASSISTANT RAG
# =====================================================================
if page == "💬 Assistant RAG":
    st.header("💬 Assistant RAG (Sportifs & Compétitions)")
    
    with st.sidebar:
        st.markdown("---")
        st.subheader("⚙️ Configuration RAG")
        modele_choisi = st.radio(
            "Modèle LLM pour le RAG",
            ("Gemini API (Cloud)", "Ollama (Local) - llama3", "Simulation (Sans LLM)")
        )
        
        provider_map = {
            "Gemini API (Cloud)": "gemini",
            "Ollama (Local) - llama3": "ollama",
            "Simulation (Sans LLM)": "simulation"
        }
    
    actuel_provider = provider_map[modele_choisi]
    
    if "rag_assistant" not in st.session_state or st.session_state.rag_assistant.llm.fournisseur != actuel_provider:
        with st.spinner(f"Initialisation de l'assistant avec {actuel_provider}..."):
            assistant = RAGAssistant()
            assistant.llm.fournisseur = actuel_provider
            assistant.llm.client = assistant.llm._initialiser_client()
            st.session_state.rag_assistant = assistant
    else:
        assistant = st.session_state.rag_assistant
    
    # Bouton Vider le chat
    if st.button("🧹 Vider la conversation", key="clear_chat"):
        st.session_state.messages = []
        st.rerun()

    # Chat interface
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ex: Quelles médailles a remporté Usain Bolt ?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Recherche dans le Knowledge Graph et génération..."):
                reponse_rag = assistant.repondre(prompt)
                
                reponse = reponse_rag.reponse_llm
                
                # Traçabilité
                tracabilite = f"**{reponse_rag.nb_triplets} faits trouvés** dans le Graphe de Connaissances."
                if reponse_rag.triplets_sources:
                    tracabilite += "\n\n*Sources utilisées :*\n"
                    for i, triplet in enumerate(reponse_rag.triplets_sources[:5]):
                        parts = " | ".join(f"`{k}={v}`" for k, v in triplet.items())
                        tracabilite += f"- {parts}\n"
                    if reponse_rag.nb_triplets > 5:
                        tracabilite += f"- ... et {reponse_rag.nb_triplets - 5} autres.\n"
                        
                if reponse_rag.est_fallback:
                    tracabilite += "\n\n⚠️ *Avertissement : Requête générique de Fallback utilisée.*"
                
                message_placeholder.markdown(reponse)
                
                with st.expander("🔍 Voir la traçabilité des sources (Faits du KG)"):
                    st.markdown(tracabilite)
                    
            st.session_state.messages.append({"role": "assistant", "content": reponse})

# =====================================================================
# PAGE 2 : LINK PREDICTION (KGE)
# =====================================================================
elif page == "🔮 Link Prediction (KGE)":
    st.header("🔮 Link Prediction KGE (Prédiction de Triplets)")
    st.markdown("Ce module utilise votre modèle **DistMult** (le plus performant !) pré-entraîné pour deviner l'objet d'une relation manquante.")
    
    # Cacher le chargement du modèle pour la performance
    @st.cache_resource
    def load_kge_model_and_tf():
        import torch
        from pykeen.triples import TriplesFactory
        
        # Reconstruire le dictionnaire (identique à l'entraînement)
        tf = TriplesFactory.from_path(
            ROOT / "data" / "kge" / "train.txt",
            create_inverse_triples=False
        )
        
        try:
            import class_resolver.func
            if not hasattr(class_resolver.func.FunctionResolver, "__class_getitem__"):
                class_resolver.func.FunctionResolver.__class_getitem__ = lambda cls, x: cls
        except:
            pass
        model_path = ROOT / "models" / "kge_results" / "results" / "DistMult" / "trained_model.pkl"
        if not model_path.exists():
            return None, None
        model = torch.load(str(model_path), map_location="cpu", weights_only=False)
        model.eval()
        return model, tf
        
    model, tf = load_kge_model_and_tf()
    
    if not model or not tf:
        st.error("Impossible de charger le modèle DistMult. Avez-vous entraîné DistMult ?")
    else:
        import requests
                    
        @st.cache_data(show_spinner=False)
        def get_clean_human_label(uri):
            if not isinstance(uri, str): return str(uri)
            uri = uri.strip()
            if "monprojet.org" in uri:
                return uri.split("/")[-1]
            if uri.startswith("http://www.wikidata.org/entity/Q") or uri.startswith("http://www.wikidata.org/prop/direct/P"):
                code = uri.split("/")[-1]
                try:
                    url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={code}&format=json&props=labels"
                    headers = {"User-Agent": "MyKGProject/1.0 (mailto:admin@local.com)"}
                    res = requests.get(url, headers=headers, timeout=5).json()
                    labels = res.get("entities", {}).get(code, {}).get("labels", {})
                    return labels.get("fr", {}).get("value", labels.get("en", {}).get("value", code))
                except Exception as e:
                    return code
            return uri.split("/")[-1] if "/" in uri else str(uri)

        entities_list = list(tf.entity_to_id.keys())
        relations_list = list(tf.relation_to_id.keys())
        
        # Charger les sets
        @st.cache_data
        def load_tuples(file_name):
            path = ROOT / "data" / "kge" / file_name
            if not path.exists(): return []
            with open(path, "r", encoding="utf-8") as f:
                lines = [l.strip().split("\t") for l in f if l.strip()]
            return [t for t in lines if len(t) == 3]
            
        test_triplets = load_tuples("test.txt")
        train_triplets = load_tuples("train.txt")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 Piger un Vrai Triplet (Base d'Entraînement)"):
                if train_triplets:
                    t = random.choice(train_triplets)
                    st.session_state.random_head = t[0]
                    st.session_state.random_relation = t[1]
                    st.session_state.vrai_tail_cache = t[2]
                    st.session_state.is_test_triplet = False
        with col_btn2:
            if st.button("🎲 Piger depuis le set de TEST (Inconnu)"):
                if test_triplets:
                    t = random.choice(test_triplets)
                    st.session_state.random_head = t[0]
                    st.session_state.random_relation = t[1]
                    st.session_state.vrai_tail_cache = t[2]
                    st.session_state.is_test_triplet = True
                else:
                    st.error("Le fichier test.txt est introuvable !")
                    
        # Initialisation par défaut
        if "random_head" not in st.session_state:
            st.session_state.random_head = random.choice(entities_list)
            st.session_state.random_relation = random.choice(relations_list)
            st.session_state.vrai_tail_cache = None
            st.session_state.is_test_triplet = False
            
        col1, col2 = st.columns(2)
        with col1:
            head = st.text_input("Head (Sujet)", value=st.session_state.random_head)
            st.caption(f"🧠 Détecté : **{get_clean_human_label(head)}**")
        with col2:
            relation = st.text_input("Relation (Prédicat)", value=st.session_state.random_relation)
            st.caption(f"🔗 Détecté : **{get_clean_human_label(relation)}**")
            
        if st.button("🚀 Prédire la Tail (Objet)", type="primary"):
            with st.spinner("Inférence en cours de calcul..."):
                try:
                    from pykeen.predict import predict_target
                    
                    df_pred = predict_target(
                        model=model,
                        head=head,
                        relation=relation,
                        triples_factory=tf
                    ).df
                    
                    import requests
                    
                    @st.cache_data(show_spinner=False)
                    def get_clean_label(uri):
                        if not isinstance(uri, str): return str(uri)
                        if "monprojet.org" in uri:
                            return uri.split("/")[-1]
                        if uri.startswith("http://www.wikidata.org/entity/Q") or uri.startswith("http://www.wikidata.org/prop/direct/P"):
                            code = uri.split("/")[-1]
                            try:
                                url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={code}&format=json&props=labels"
                                headers = {"User-Agent": "MyKGProject/1.0 (mailto:admin@local.com)"}
                                res = requests.get(url, headers=headers, timeout=5).json()
                                labels = res.get("entities", {}).get(code, {}).get("labels", {})
                                return labels.get("fr", {}).get("value", labels.get("en", {}).get("value", code))
                            except Exception as e:
                                return code
                        return uri.split("/")[-1] if "/" in uri else str(uri)

                    
                    # On garde les URI raw d'abord pour vérifier si on a le bon hit
                    df_top_raw = df_pred.head(10)[["tail_label", "score"]].reset_index(drop=True)
                    
                    # Chercher les "Vraies Réponses" dans d'entraînement
                    vrais_resultats_labels = []
                    h_id = tf.entity_to_id.get(head)
                    r_id = tf.relation_to_id.get(relation)
                    if h_id is not None and r_id is not None:
                        from pykeen.triples import TriplesFactory
                        mask = (tf.mapped_triples[:, 0] == h_id) & (tf.mapped_triples[:, 1] == r_id)
                        t_ids = tf.mapped_triples[mask, 2]
                        
                        id_to_entity = {v: k for k, v in tf.entity_to_id.items()}
                        for idx in t_ids.tolist():
                            tail_uri = id_to_entity.get(idx)
                            vrais_resultats_labels.append(get_clean_human_label(tail_uri))

                    # Vérifier s'il y a un tail cible caché issu de nos tirages (Train ou Test)
                    tail_cible = st.session_state.get("vrai_tail_cache") 
                    is_test = st.session_state.get("is_test_triplet", False)
                    
                    if tail_cible:
                        lbl_cible = get_clean_human_label(tail_cible)
                        origine = "Test Set (Inconnu du modèle)" if is_test else "Set d'Entraînement (Connu du modèle)"
                        st.info(f"🎯 **Objectif caché du {origine} :** `{lbl_cible}`")
                        
                        # Vérifier si cet objectif est dans le top 10 des prédictions
                        tail_cible_in_top10 = tail_cible in df_top_raw["tail_label"].values
                        if tail_cible_in_top10:
                            st.success(f"🏆 Incroyable, le modèle a formellement prédit la vraie réponse (`{lbl_cible}`) dans le Top 10 !")
                        else:
                            st.warning(f"📉 La vraie réponse (`{lbl_cible}`) n'est pas remontée dans le Top 10.")
                    else:
                        if vrais_resultats_labels:
                            st.info(f"📌 **Vrai(s) résultat(s) historiquement connu(s) dans l'Entraînement :** {', '.join(vrais_resultats_labels)}")
                        else:
                            st.warning("📌 Aucun résultat connu dans la base pour ce Sujet + Prédicat (C'est une pure prédiction ou lien manquant !)")

                    # Remplacement des URIs par de beaux labels pour l'affichage final
                    df_top = df_top_raw.copy()
                    df_top["tail_label"] = df_top["tail_label"].apply(get_clean_human_label)
                    df_top.index += 1
                    df_top.columns = ["Objet Prédit (Tail)", "Score de Confiance"]
                    
                    st.success("✅ Prédiction réussie ! Voici le classement des candidats probables :")
                    st.table(df_top)
                    
                except Exception as e:
                    st.error(f"Une erreur est survenue lors de la prédiction : {e}")

# =====================================================================
# PAGE 3 : DASHBOARD & STATISTIQUES
# =====================================================================
elif page == "📊 Dashboard & Statistiques":
    st.header("📊 Dashboard : Métriques et Performances")
    
    # 1. Statistiques du Knowledge Graph
    st.subheader("Volumétrie du Knowledge Graph")
    if STATS_KB_PATH.exists():
        with open(STATS_KB_PATH, "r", encoding="utf-8") as f:
            stats_kb = json.load(f)
            
        col1, col2, col3 = st.columns(3)
        col1.metric("Triplets Totaux", f"{stats_kb.get('nb_triplets', 0):,}")
        col2.metric("Entités Uniques", f"{stats_kb.get('nb_entities', 0):,}")
        col3.metric("Relations", f"{stats_kb.get('nb_relations', 0):,}")
    else:
        st.warning(f"Fichier introuvable : {STATS_KB_PATH}")
        
    st.markdown("---")
    
    # 2. Comparaison des modèles KGE
    st.subheader("Performance des Modèles KGE (Filtrés)")
    if COMPARAISON_KGE_PATH.exists():
        with open(COMPARAISON_KGE_PATH, "r", encoding="utf-8") as f:
            comp = json.load(f)
            
        results = comp.get("resultats", [])
        if results:
            df = pd.DataFrame(results)
            # Sélectionner et renommer les colonnes pertinentes
            cols_to_show = ["model", "MRR_filtered", "Hits@1_filtered", "Hits@3_filtered", "Hits@10_filtered", "duration_s"]
            df_show = df[[c for c in cols_to_show if c in df.columns]]
            df_show = df_show.rename(columns={
                "model": "Modèle",
                "duration_s": "Durée (s)"
            })
            
            st.dataframe(df_show, use_container_width=True)
            
            # Petit graphique interactif
            if "model" in df.columns:
                st.bar_chart(df.set_index("model")["MRR_filtered"], height=250)
        else:
            st.info("Aucun résultat d'évaluation de modèle trouvé.")
    else:
        st.warning(f"Fichier de comparaison introuvable : {COMPARAISON_KGE_PATH}")
