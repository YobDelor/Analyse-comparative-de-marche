# -*- coding: utf-8 -*-
"""Étape 5 — synthèse."""
import pandas as pd
import streamlit as st

from modele.structures import ENSEIGNES
from vue.etat import obtenir_resultats
from vue.formats import decimal, entier, fcfa
from vue.graphiques import barres_enseignes

res = obtenir_resultats()
s = res.synthese

st.title("Étape 5 · Synthèse")

# --- 1. victoires -----------------------------------------------------------
st.subheader("1 · Combien de fois chaque enseigne est-elle la moins chère ?")
victoires = pd.DataFrame({
    "Enseigne": ENSEIGNES,
    "Produits gagnés": [s["victoires"][e] for e in ENSEIGNES],
    "dont ex æquo": [s["ex_aequo"][e] for e in ENSEIGNES],
})
col_tab, col_graph = st.columns(2)
col_tab.dataframe(victoires, hide_index=True)
with col_graph:
    barres_enseignes(victoires, "Enseigne", "Produits gagnés", "Produits gagnés")
st.caption(f"Sur {s['nb_produits']} produits comparables. En cas d'ex æquo, les deux "
           "enseignes sont comptées : le total peut donc dépasser ce nombre.")

# --- 2. écart moyen ---------------------------------------------------------
st.subheader("2 · Écart moyen de chaque enseigne au prix le plus bas")
ecarts = pd.DataFrame({
    "Enseigne": ENSEIGNES,
    "Écart moyen (FCFA)": [s["ecarts"][e]["moyen_fcfa"] for e in ENSEIGNES],
    "Écart moyen (%)": [s["ecarts"][e]["moyen_pct"] for e in ENSEIGNES],
    "Produits concernés": [s["ecarts"][e]["n"] for e in ENSEIGNES],
})
col_tab, col_graph = st.columns(2)
col_tab.dataframe(ecarts.style.format(entier, subset=["Écart moyen (FCFA)"])
                  .format(decimal, subset=["Écart moyen (%)"]), hide_index=True)
with col_graph:
    barres_enseignes(ecarts, "Enseigne", "Écart moyen (FCFA)", "Écart moyen (FCFA)")
proche_fcfa = ecarts.loc[ecarts["Écart moyen (FCFA)"].idxmin(), "Enseigne"]
proche_pct = ecarts.loc[ecarts["Écart moyen (%)"].idxmin(), "Enseigne"]
st.caption(f"Calculé sur les produits où l'enseigne a une offre exploitable. Plus proche du "
           f"meilleur prix en FCFA : {proche_fcfa} ; en pourcentage : {proche_pct}.")

# --- 3. top 3 ---------------------------------------------------------------
st.subheader("3 · Les trois produits où il y a le plus à gagner à comparer")
top3 = pd.DataFrame([{
    "Produit": f"{t['produit_id']} · {t['nom']}",
    "Moins chère": t["moins_chere"],
    "Prix le plus bas": t["prix_min"],
    "Plus chère": t["plus_chere"],
    "Prix le plus haut": t["prix_max"],
    "Écart (FCFA)": t["ecart_fcfa"],
    "Écart (%)": t["ecart_pct"],
} for t in s["top3"]])
st.dataframe(top3.style.format(entier, subset=["Prix le plus bas", "Prix le plus haut", "Écart (FCFA)"])
             .format(decimal, subset=["Écart (%)"]), hide_index=True)
st.caption(f"En moyenne, l'écart entre l'enseigne la plus chère et la moins chère est de "
           f"{fcfa(res.df_comparatif['ecart_fcfa'].mean())} par produit comparable.")
