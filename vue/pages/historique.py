# -*- coding: utf-8 -*-
"""Étape 7 — historique des prix et Black Friday."""
import streamlit as st

from modele import historique as modele_historique
from modele.structures import ENSEIGNES, format_nombre
from vue.etat import obtenir_resultats
from vue.formats import COULEURS, couleur_ecart, decimal, entier, pct
from vue.graphiques import barres_enseignes

res = obtenir_resultats()
ECART = "Écart à la moyenne annuelle (%)"

st.title("Étape 7 · Quand fallait-il acheter ?")
st.caption(f"{format_nombre(len(res.historique))} relevés quotidiens, du 01/11/2025 au 31/10/2026.")

# --- Black Friday -----------------------------------------------------------
st.subheader("Black Friday : semaine du 24 au 30 novembre 2025")
bf = res.bf.rename(columns={"source": "Enseigne", "ecart_pct": ECART, "nb_produits": "Produits"})
col_tab, col_graph = st.columns(2)
col_tab.dataframe(bf.style.map(couleur_ecart, subset=[ECART]).format(decimal, subset=[ECART]),
                  hide_index=True)
with col_graph:
    barres_enseignes(bf, "Enseigne", ECART, ECART)
for r in res.bf.itertuples():
    verdict = "prix plus bas que d'habitude" if r.ecart_pct < 0 else "prix plus élevés que d'habitude"
    st.markdown(f"- **{r.source}** : {pct(r.ecart_pct, signe=True)} — {verdict}.")
st.caption("Écart calculé produit par produit (prix moyen de la semaine vs prix moyen de "
           "l'année), puis moyenné par enseigne. Comptoir Ivoire : prix catalogue, sans la remise.")

# --- meilleure semaine ------------------------------------------------------
st.subheader("Meilleure semaine de l'année, par enseigne")
semaines = res.meilleures_semaines.rename(columns={
    "source": "Enseigne", "semaine_du": "Semaine du (lundi)", "ecart_pct": ECART})
st.dataframe(semaines.style.map(couleur_ecart, subset=[ECART]).format(decimal, subset=[ECART]),
             hide_index=True)

# --- courbe d'un produit ----------------------------------------------------
st.subheader("Explorer un produit")
noms = dict(zip(res.catalogue["produit_id"], res.catalogue["nom"]))
ids = sorted(res.historique["produit_id"].unique())
pid = st.selectbox("Produit", ids, format_func=lambda p: f"{p} · {noms.get(p, p)}")

courbe = modele_historique.courbe_produit(res.historique, pid)
courbe = courbe[[e for e in ENSEIGNES if e in courbe.columns]]
st.line_chart(courbe, color=[COULEURS[e] for e in courbe.columns])

detail = modele_historique.detail_black_friday_produit(res.historique, pid)
if not detail.empty:
    detail = detail.rename(columns={
        "source": "Enseigne", "prix_bf": "Prix moyen Black Friday",
        "prix_annee": "Prix moyen de l'année", "ecart_pct": "Écart (%)"})
    st.dataframe(detail.style.map(couleur_ecart, subset=["Écart (%)"])
                 .format(entier, subset=["Prix moyen Black Friday", "Prix moyen de l'année"])
                 .format(decimal, subset=["Écart (%)"]), hide_index=True)
st.caption("Les prix de Comptoir Ivoire, relevés une fois par semaine, sont reportés "
           "jusqu'au relevé suivant.")
