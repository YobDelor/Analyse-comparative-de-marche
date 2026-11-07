# -*- coding: utf-8 -*-
"""Mesures de performance (étape 8 de l'énoncé).

Deux volets :
  * le chronométrage de chaque étage du pipeline (fait par le contrôleur) ;
  * un petit benchmark comparant deux structures de données pour chercher
    un prix dans l'historique : balayage d'une liste O(n) contre
    dictionnaire (table de hachage) O(1).
"""
from __future__ import annotations

import random
import time

import pandas as pd

from .structures import Journal, format_nombre


def benchmark_recherche(hist: pd.DataFrame, n_balayage: int = 300,
                        n_dict: int = 20_000, graine: int = 42) -> dict:
    """Compare le coût d'une recherche de prix (source, produit, date).

    * « liste »  : parcourt les 20 876 relevés jusqu'à trouver le bon — O(n) ;
    * « dict »   : accès direct par clé composée — O(1) en moyenne.

    Le balayage est limité à ``n_balayage`` requêtes (sinon l'attente serait
    de plusieurs minutes), le dictionnaire en enchaîne 20 000 pour montrer
    l'écart de coût unitaire.
    """
    rng = random.Random(graine)

    lignes = [(r.source, r.produit_id, r.date, int(r.prix_fcfa))
              for r in hist.itertuples(index=False)]
    index_dict = {(src, pid, date): prix for src, pid, date, prix in lignes}
    cles = list(index_dict.keys())
    requetes = [rng.choice(cles) for _ in range(max(n_balayage, n_dict))]

    # --- balayage de liste -------------------------------------------------
    debut = time.perf_counter()
    for i in range(n_balayage):
        src, pid, date = requetes[i]
        for src_l, pid_l, date_l, prix_l in lignes:
            if src_l == src and pid_l == pid and date_l == date:
                _ = prix_l
                break
    duree_liste = time.perf_counter() - debut

    # --- dictionnaire --------------------------------------------------------
    debut = time.perf_counter()
    for i in range(n_dict):
        _ = index_dict[requetes[i]]
    duree_dict = time.perf_counter() - debut

    par_requete_liste = duree_liste / n_balayage
    par_requete_dict = duree_dict / n_dict
    rapport = par_requete_liste / par_requete_dict if par_requete_dict > 0 else float("inf")

    return {
        "nb_lignes": len(lignes),
        "n_balayage": n_balayage,
        "n_dict": n_dict,
        "duree_liste_s": duree_liste,
        "duree_dict_s": duree_dict,
        "par_requete_liste_us": par_requete_liste * 1e6,
        "par_requete_dict_us": par_requete_dict * 1e6,
        "rapport": rapport,
    }


def journaliser_benchmark(bench: dict, journal: Journal) -> None:
    journal.log(
        "Complexité", "info", "—",
        f"Recherche d'un prix parmi {format_nombre(bench['nb_lignes'])} relevés : "
        f"balayage de liste {format_nombre(bench['par_requete_liste_us'])} µs/recherche contre "
        f"{format_nombre(bench['par_requete_dict_us'], 2)} µs/recherche avec un dictionnaire",
        f"Le dictionnaire (clé composée source+produit+date) est "
        f"≈ ×{format_nombre(bench['rapport'])} plus rapide — O(1) contre O(n)",
    )
