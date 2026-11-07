# -*- coding: utf-8 -*-
"""Formats français et styles communs aux pages."""
import pandas as pd

from modele.structures import format_nombre

#: Une couleur par enseigne, la même dans tous les graphiques.
COULEURS = {"Marché Lagune": "#2563EB", "Baobab Shop": "#0E9F6E", "Comptoir Ivoire": "#F25C05"}

_VERT = "background-color:#D3F9D8;color:#0B5D2A;font-weight:600"
_GRAVITES = {
    "critique": "background-color:#FFE3E3;color:#A61E1E;font-weight:600",
    "avertissement": "background-color:#FFF3BF;color:#8A5A00;font-weight:600",
    "info": "background-color:#E7F5FF;color:#1864AB",
}


def fcfa(valeur: float) -> str:
    return f"{format_nombre(valeur)}\u00a0FCFA"


def pct(valeur: float, signe: bool = False) -> str:
    texte = f"{valeur:+.1f}" if signe else f"{valeur:.1f}"
    return texte.replace(".", ",") + "\u00a0%"


def entier(valeur) -> str:
    return format_nombre(valeur)


def decimal(valeur, chiffres: int = 1) -> str:
    return format_nombre(valeur, chiffres)


def surligner_min(ligne: pd.Series) -> list[str]:
    """Colore en vert le(s) plus bas prix d'une ligne (ex æquo compris)."""
    valeurs = pd.to_numeric(ligne, errors="coerce")
    mini = valeurs.min()
    return [_VERT if pd.notna(v) and abs(v - mini) <= 0.5 else "" for v in valeurs]


def couleur_gravite(valeur: str) -> str:
    return _GRAVITES.get(valeur, "")


def couleur_ecart(valeur: float) -> str:
    """Vert si le prix baisse, rouge s'il monte."""
    if pd.isna(valeur) or valeur == 0:
        return ""
    return "color:#0B7A43;font-weight:600" if valeur < 0 else "color:#C92A2A;font-weight:600"
