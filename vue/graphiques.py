# -*- coding: utf-8 -*-
"""Graphique en barres aux couleurs des enseignes."""
import altair as alt
import pandas as pd
import streamlit as st

from vue.formats import COULEURS


def barres_enseignes(df: pd.DataFrame, colonne_x: str, colonne_y: str, titre_y: str) -> None:
    d = df[[colonne_x, colonne_y]].set_axis(["enseigne", "valeur"], axis=1)
    graphique = alt.Chart(d).mark_bar().encode(
        x=alt.X("enseigne:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("valeur:Q", title=titre_y),
        color=alt.Color("enseigne:N", legend=None, scale=alt.Scale(
            domain=list(COULEURS), range=list(COULEURS.values()))),
        tooltip=["enseigne", "valeur"],
    ).properties(height=260)
    st.altair_chart(graphique)
