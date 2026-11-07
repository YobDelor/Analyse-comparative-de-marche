# -*- coding: utf-8 -*-
"""Étape 4 — comparatif des prix payés."""
import pandas as pd
import streamlit as st

from modele.structures import CLES, ENSEIGNES
from vue.etat import obtenir_resultats
from vue.formats import decimal, entier, surligner_min

res = obtenir_resultats()

st.title("Étape 4 · Comparatif des prix")
st.caption("Prix réellement payé (livraison incluse ou ajoutée, remise déduite) pour les "
           "produits disponibles dans au moins deux enseignes. Cliquez sur un en-tête "
           "pour trier.")


def non_retenus(df: pd.DataFrame) -> pd.Series:
    """Texte « Enseigne : raison » pour les offres exclues de chaque ligne."""
    def ligne(row):
        return " ; ".join(f"{e} : {row['remarque_' + CLES[e]]}"
                          for e in ENSEIGNES if row["remarque_" + CLES[e]])
    return df.apply(ligne, axis=1)


def prix_par_enseigne(df: pd.DataFrame) -> dict:
    return {e: df["prix_" + CLES[e]] for e in ENSEIGNES}


categorie = st.selectbox("Catégorie", ["Toutes", "Smartphone", "Informatique", "Électroménager"])
df = res.df_comparatif
if categorie != "Toutes":
    df = df[df["categorie"] == categorie]

tableau = pd.DataFrame({
    "Produit": df["produit_id"] + " · " + df["nom"],
    **prix_par_enseigne(df),
    "Moins chère": df["moins_chere"],
    "Écart (FCFA)": df["ecart_fcfa"],
    "Écart (%)": df["ecart_pct"],
    "Offres non retenues": non_retenus(df),
})
st.dataframe(
    tableau.style.apply(surligner_min, axis=1, subset=ENSEIGNES)
    .format(entier, subset=[*ENSEIGNES, "Écart (FCFA)"], na_rep="—")
    .format(decimal, subset=["Écart (%)"]),
    hide_index=True,
)
st.caption(f"{len(df)} produit(s). En vert : le meilleur prix. Écart = prix le plus haut − prix le plus bas. "
           "Une offre non retenue (rupture, prix sur demande, prix aberrant…) n'entre "
           "pas dans le classement.")

st.download_button("Télécharger le comparatif complet (CSV)",
                   data=res.chemin_export.read_bytes(),
                   file_name="comparatif_prix.csv", mime="text/csv")

if st.toggle("Afficher les produits non comparables (moins de 2 offres exploitables)"):
    hors = res.df_hors_comparatif
    if categorie != "Toutes":
        hors = hors[hors["categorie"] == categorie]
    st.dataframe(pd.DataFrame({
        "Produit": hors["produit_id"] + " · " + hors["nom"],
        "Offres exploitables": hors["nb_offres"],
        "Offres non retenues": non_retenus(hors),
    }), hide_index=True)
