# -*- coding: utf-8 -*-
"""Comparateur de prix de l'électronique à Abidjan.

Lancement :  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="Comparateur de prix · Abidjan", layout="wide")

st.navigation([
    st.Page("vue/pages/accueil.py", title="Résumé", default=True),
    st.Page("vue/pages/journal.py", title="Nettoyage"),
    st.Page("vue/pages/comparatif.py", title="Comparatif"),
    st.Page("vue/pages/synthese.py", title="Synthèse"),
    st.Page("vue/pages/panier.py", title="Panier"),
    st.Page("vue/pages/historique.py", title="Historique"),
    st.Page("vue/pages/performance.py", title="Performance"),
]).run()