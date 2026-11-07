# -*- coding: utf-8 -*-
"""Étape 2 — journal de nettoyage."""
import streamlit as st

from vue.etat import obtenir_resultats
from vue.formats import couleur_gravite

res = obtenir_resultats()
journal = res.journal

st.title("Étape 2 · Journal de nettoyage")
st.caption("Chaque anomalie repérée pendant le chargement, avec le traitement appliqué. "
           "Rien n'est corrigé en silence.")

c1, c2, c3 = st.columns(3)
c1.metric("Critiques", journal.compter("critique"))
c2.metric("Avertissements", journal.compter("avertissement"))
c3.metric("Informations", journal.compter("info"))

df = journal.vers_dataframe()
f1, f2 = st.columns(2)
gravites = f1.multiselect("Gravité", ["critique", "avertissement", "info"],
                          default=["critique", "avertissement", "info"])
sources = f2.multiselect("Source", sorted(df["source"].unique()),
                         default=sorted(df["source"].unique()))

filtre = df[df["gravite"].isin(gravites) & df["source"].isin(sources)]
st.dataframe(
    filtre.style.map(couleur_gravite, subset=["gravite"]), hide_index=True,
    column_config={
        "source": st.column_config.TextColumn("Source", width="small"),
        "gravite": st.column_config.TextColumn("Gravité", width="small"),
        "ref": st.column_config.TextColumn("Réf.", width="small"),
        "probleme": st.column_config.TextColumn("Problème", width="large"),
        "traitement": st.column_config.TextColumn("Traitement", width="large"),
    },
)
