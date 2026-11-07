# -*- coding: utf-8 -*-
"""Nettoyage des données (étape 2) : conversions de valeurs et contrôle de cohérence."""
from __future__ import annotations

import re
import statistics
import unicodedata

import pandas as pd

from .structures import Journal, Offre, RAISON_SUSPECT, format_nombre

# Séparateurs de milliers possibles : espace, insécable U+00A0, fine insécable U+202F…
_ESPACES = re.compile(r"[\s\u00a0\u202f\u2009\u2007\u2008]+")
_NUMERIQUE = re.compile(r"^\d+(?:[.,]\d+)?$")

DISPONIBILITES = {"en stock": True, "stock limite": True, "rupture": False}


def normaliser(texte: str) -> str:
    """Minuscules, sans accent ni ponctuation, espaces simples (pour le rapprochement)."""
    texte = unicodedata.normalize("NFKD", str(texte))
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = re.sub(r"[^a-z0-9]+", " ", texte.lower())
    return texte.strip()


def nettoyer_designation(brut) -> str:
    """Supprime les espaces parasites (début, fin, doublés)."""
    return re.sub(r"\s+", " ", str(brut)).strip()


def convertir_prix(brut) -> tuple[float | None, str | None]:
    """« 102 900 FCFA » ou 102900 -> (102900.0, None).

    Retourne (valeur, anomalie) : valeur est None si le prix n'est pas numérique ;
    anomalie contient alors le texte d'origine (« Prix sur demande »…), ou None
    si la cellule est simplement vide.
    """
    if brut is None or pd.isna(brut):
        return None, None
    texte = str(brut).strip()
    if texte == "":
        return None, None
    nettoye = _ESPACES.sub("", texte).upper().replace("FCFA", "")
    if _NUMERIQUE.match(nettoye):
        return float(nettoye.replace(",", ".")), None
    return None, texte


def convertir_entier(brut) -> int | None:
    if brut is None or pd.isna(brut):
        return None
    try:
        return int(float(str(brut).strip()))
    except ValueError:
        return None


def convertir_disponibilite(brut, journal: Journal, source: str, ref: str) -> bool:
    """« En stock » / « Stock limité » -> True, « Rupture » -> False.

    Valeur absente ou inconnue : considérée en stock par prudence, et journalisée.
    """
    if brut is not None and not pd.isna(brut):
        cle = normaliser(nettoyer_designation(brut))
        if cle in DISPONIBILITES:
            return DISPONIBILITES[cle]
        probleme = f"Disponibilité non reconnue : « {brut} »"
    else:
        probleme = "Disponibilité absente"
    journal.log(source, "avertissement", ref, probleme, "Considérée comme « En stock » par prudence")
    return True


def controler_coherence(offres: list[Offre], journal: Journal) -> None:
    """Contrôle croisé : un prix > 3 × la médiane des autres enseignes est suspect.

    Complète le contrôle prix / prix barré fait au chargement de Marché Lagune.
    Une offre déjà exclue n'est pas réexaminée.
    """
    par_produit: dict[str, list[tuple[str, float]]] = {}
    for o in offres:
        if o.produit_id is not None and o.prix_paye is not None:
            par_produit.setdefault(o.produit_id, []).append((o.enseigne, o.prix_paye))

    nb = 0
    for o in offres:
        if o.produit_id is None or o.prix_paye is None or o.probleme is not None:
            continue
        autres = [p for e, p in par_produit[o.produit_id] if e != o.enseigne]
        if len(autres) < 2:
            continue
        mediane = statistics.median(autres)
        if o.prix_paye > 3.0 * mediane:
            journal.log("Comparaison", "critique", o.ref,
                        f"Prix {format_nombre(o.prix_paye)} FCFA très supérieur à la médiane des autres "
                        f"enseignes ({format_nombre(mediane)} FCFA) pour {o.produit_id}",
                        "Prix exclu du comparatif (prix aberrant)")
            o.probleme = RAISON_SUSPECT
            nb += 1

    journal.log("Comparaison", "info", "—",
                f"Contrôle croisé inter-enseignes sur {len(par_produit)} produits",
                f"{nb} nouvelle(s) anomalie(s) détectée(s)")
