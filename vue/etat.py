# -*- coding: utf-8 -*-
"""Le pipeline s'exécute une seule fois ; les pages réutilisent le résultat."""
import streamlit as st

from controleur.controleur import Controleur


@st.cache_resource(show_spinner="Analyse des données…")
def obtenir_resultats():
    return Controleur().executer()
