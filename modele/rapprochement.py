# -*- coding: utf-8 -*-
"""Rapprochement des articles avec le catalogue de référence (étape 3).

Chaque enseigne écrit les noms à sa façon :
  * Marché Lagune : « SAMSUNG GALAXY A15 (128GB) », tout en majuscules ;
  * Baobab Shop   : « Galaxy A15 128GB - Samsung » ;
  * Comptoir Ivoire: « Samsun Galaxy A15 128Go » (avec coquille !).

Stratégie en deux niveaux :
  1. des motifs regex par produit (marque + indice distinctif du modèle),
     évalués sur une désignation normalisée — déterministe et explicable ;
  2. en repli, une comparaison floue (difflib) avec les noms du catalogue.
Chaque décision est traçable et les anomalies sont journalisées.
"""
from __future__ import annotations

import difflib
import re
from collections import Counter

import pandas as pd

from .nettoyage import normaliser
from .structures import Journal, Offre, format_nombre

# Tous les motifs d'une même ligne doivent matcher (ET logique).
# Les indices de modèle (A15, Spark 20, M185, 205 L, 1 CV…) sont plus
# discriminants que les marques seules : deux Samsung 24" et 43" ne
# partagent que la marque, pas l'indice.
REGLES_PRODUITS: dict[str, list[re.Pattern]] = {
    "P01": [r"\ba15\b"],
    "P02": [r"\ba25\b"],
    "P03": [r"\ba55\b"],
    "P04": [r"spark"],
    "P05": [r"camon"],
    "P06": [r"hot 40"],
    "P07": [r"note 40"],
    "P08": [r"a70"],
    "P09": [r"iphone 13"],
    "P10": [r"redmi"],
    "P11": [r"250 g9"],
    "P12": [r"ideapad"],
    "P13": [r"inspiron"],
    "P14": [r"sandisk"],
    "P15": [r"seagate"],
    "P16": [r"m185"],
    "P17": [r"deskjet"],
    "P18": [r"archer"],
    "P19": [r"\b24\b", r"ecran|monitor|pouce"],
    "P20": [r"205", r"frigo|refrigerateur|fridge"],
    "P21": [r"nasco|congel"],
    "P22": [r"\b43\b", r"tv|uhd|crystal"],
    "P23": [r"\b32\b", r"tv|hisense"],
    "P24": [r"\blg\b", r"clim|air|condition|1cv|1hp"],
    "P25": [r"ventilat|ventilo"],
    "P26": [r"moulinex|mixeur"],
    "P27": [r"philips", r"\bfer\b|iron|repass"],
    "P28": [r"micro ondes|microwave"],
    "P29": [r"bouilloire|kettle"],
    "P30": [r"hisense", r"clim|air|condition|1 5"],
}

for _pid, _motifs in REGLES_PRODUITS.items():
    REGLES_PRODUITS[_pid] = [re.compile(m) for m in _motifs]

SEUIL_FLOU = 0.50


def _score_flou(designation: str, nom_catalogue: str) -> float:
    return difflib.SequenceMatcher(None, designation, nom_catalogue).ratio()


def rapprocher(offres: list[Offre], catalogue: pd.DataFrame, journal: Journal) -> None:
    """Remplit ``offre.produit_id`` pour chaque offre, en journalisant."""
    noms_catalogue = {
        str(ligne["produit_id"]): normaliser(ligne["nom"])
        for _, ligne in catalogue.iterrows()
    }
    marques = {
        str(ligne["produit_id"]): normaliser(ligne["marque"])
        for _, ligne in catalogue.iterrows()
    }

    bilans: Counter = Counter()

    for offre in offres:
        texte = normaliser(offre.designation)

        # --- niveau 1 : motifs regex --------------------------------------
        candidats = [
            pid for pid, motifs in REGLES_PRODUITS.items()
            if all(m.search(texte) for m in motifs)
        ]
        methode = "motif"
        if len(candidats) > 1:
            # départage par ressemblance avec les noms du catalogue
            candidats = [
                max(candidats, key=lambda p: _score_flou(texte, noms_catalogue[p]))
            ]
            journal.log("Rapprochement", "avertissement", offre.ref,
                        f"Désignation « {offre.designation} » ambiguë "
                        f"(plusieurs produits possibles)",
                        "Départagée par similarité avec le nom du catalogue")
        elif len(candidats) == 0:
            # --- niveau 2 : repli flou --------------------------------------
            pid, score = max(
                ((p, _score_flou(texte, n)) for p, n in noms_catalogue.items()),
                key=lambda x: x[1],
            )
            if score >= SEUIL_FLOU:
                candidats = [pid]
                methode = "flou"
                journal.log("Rapprochement", "avertissement", offre.ref,
                            f"Désignation « {offre.designation} » sans motif direct",
                            f"Rapprochée de {pid} par similarité floue (score {format_nombre(score, 2)})")
            else:
                journal.log("Rapprochement", "critique", offre.ref,
                            f"Désignation « {offre.designation} » non reconnue "
                            f"(meilleur score flou {format_nombre(score, 2)} < {format_nombre(SEUIL_FLOU, 2)})",
                            "Offre exclue du rapprochement")
                bilans["echec"] += 1
                continue

        offre.produit_id = candidats[0]
        bilans[methode] += 1

        # --- détection de coquille dans la marque -------------------------
        marque = marques.get(offre.produit_id, "")
        if marque and marque not in texte.split() and marque not in texte:
            proche = difflib.get_close_matches(marque, texte.split(), n=1, cutoff=0.8)
            if proche:
                journal.log("Rapprochement", "info", offre.ref,
                            f"Coquille probable dans la marque : « {proche[0]} » ≈ "
                            f"« {marque} »",
                            f"Reconnu malgré tout comme {offre.produit_id} grâce à "
                            "l'indice de modèle")

    journal.log("Rapprochement", "info", "—",
                f"{bilans['motif']} offres rapprochées par motif regex, "
                f"{bilans['flou']} par repli flou, "
                f"{bilans['echec']} en échec",
                "Correspondance produit_id <-> article établie pour le comparatif")
