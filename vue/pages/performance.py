# -*- coding: utf-8 -*-
"""Étape 8 — temps d'exécution et choix de structures de données."""
import pandas as pd
import streamlit as st

from modele.structures import format_nombre
from vue.etat import obtenir_resultats
from vue.formats import decimal, entier

res = obtenir_resultats()
b = res.benchmark
total_ms = sum(res.timings.values())

st.title("Étape 8 · Performance")
st.caption(f"Recherche de prix dans un historique de {format_nombre(b['nb_lignes'])} lignes : "
           "temps mesurés avec time.perf_counter et choix de structures.")

c1, c2, c3 = st.columns(3)
c1.metric("Pipeline complet", f"{entier(total_ms)} ms")
c2.metric("Recherche dans une liste", f"{entier(b['par_requete_liste_us'])} µs")
c3.metric("Recherche dans un dictionnaire", f"{decimal(b['par_requete_dict_us'], 2)} µs",
          help=f"≈ ×{format_nombre(b['rapport'])} plus rapide")

st.subheader("Temps par étage")
timings = pd.DataFrame({"Étage": list(res.timings), "Durée (ms)": list(res.timings.values())})
st.dataframe(timings.style.format(decimal, subset=["Durée (ms)"]), hide_index=True)

st.subheader("Liste ou dictionnaire ?")
st.markdown(
    f"- **Balayer une liste : O(n).** Chaque recherche parcourt les relevés un à un "
    f"({entier(b['par_requete_liste_us'])} µs en moyenne, mesuré sur {b['n_balayage']} recherches).\n"
    f"- **Dictionnaire à clé `(source, produit_id, date)` : O(1).** Accès direct "
    f"({decimal(b['par_requete_dict_us'], 2)} µs, mesuré sur {format_nombre(b['n_dict'])} recherches), "
    f"soit ≈ ×{format_nombre(b['rapport'])} plus rapide, quelle que soit la taille de l'historique.\n"
    "- **Compromis :** le dictionnaire occupe plus de mémoire et coûte O(n) à construire. "
    "Il ne vaut la peine que si l'on interroge souvent les mêmes données.")

st.subheader("Structures retenues")
st.table(pd.DataFrame([
    ("Offres", "liste de dataclass `Offre`", "un seul parcours pour construire le comparatif"),
    ("Index des offres", "dict `produit_id → {enseigne → Offre}`", "comparatif et panier en accès direct, O(1)"),
    ("Rapprochement", "motifs regex compilés une fois", "évite de recompiler à chaque désignation"),
    ("Historique", "DataFrame pandas + `groupby`", "moyennes sur toutes les lignes sans boucle Python"),
    ("Recherche ponctuelle", "dict `(source, produit, date) → prix`", "accès direct au lieu d'un balayage"),
], columns=["Où", "Structure", "Pourquoi"]).set_index("Où"))

st.subheader("Architecture")
st.code(
    "app.py          navigation\n"
    "vue/            pages Streamlit, formatage ; ne lit aucun fichier, ne calcule rien\n"
    "controleur/     exécute le pipeline, chronomètre, exporte le CSV\n"
    "modele/         chargement, nettoyage, rapprochement, comparaison, historique\n"
    "                (aucune dépendance à Streamlit)", language="text")
