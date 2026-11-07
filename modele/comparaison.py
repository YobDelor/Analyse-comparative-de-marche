# -*- coding: utf-8 -*-
"""Comparatif des prix, synthèse et panier (étapes 4, 5 et 6 de l'énoncé)."""
from __future__ import annotations

import pandas as pd

from .structures import (
    CLES,
    ENSEIGNES,
    LignePanier,
    Offre,
    ResultatPanier,
)

EPSILON = 0.5  # tolérance d'égalité entre prix (centimes arrondis)


# ---------------------------------------------------------------------------
# Index des offres 
# ---------------------------------------------------------------------------

def indexer_offres(offres: list[Offre]) -> dict[str, dict[str, Offre]]:
    index: dict[str, dict[str, Offre]] = {}
    for o in offres:
        if o.produit_id is None:
            continue
        index.setdefault(o.produit_id, {})[o.enseigne] = o
    return index


def _raison(offre: Offre | None) -> str:
    """Texte affiché quand une enseigne n'a pas de prix exploitable."""
    if offre is None:
        return ""
    return offre.raison_exclusion() or ""


# ---------------------------------------------------------------------------
# Étape 4 : comparatif
# ---------------------------------------------------------------------------

def construire_comparatif(
    offres: list[Offre], catalogue: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construit deux tables :

    * ``df_comparatif`` : produits disponibles avec prix exploitable dans au
      moins deux enseignes, avec l'enseigne la moins chère et l'écart ;
    * ``df_hors_comparatif`` : produits restants, avec la raison détaillée.
    """
    index = indexer_offres(offres)

    lignes_ok, lignes_hors = [], []
    for _, prod in catalogue.iterrows():
        pid = str(prod["produit_id"])
        offres_prod = index.get(pid, {})
        par_enseigne = {}
        prix_valides = {}
        for ens in ENSEIGNES:
            o = offres_prod.get(ens)
            if o is not None and o.exploitable():
                prix_valides[ens] = float(o.prix_paye)
            par_enseigne[ens] = o

        base = {
            "produit_id": pid,
            "nom": prod["nom"],
            "categorie": prod["categorie"],
            "marque": prod["marque"],
        }
        for ens in ENSEIGNES:
            base["prix_" + CLES[ens]] = prix_valides.get(ens)
            base["remarque_" + CLES[ens]] = _raison(par_enseigne[ens])

        if len(prix_valides) >= 2:
            prix_min = min(prix_valides.values())
            prix_max = max(prix_valides.values())
            gagnantes = [e for e, p in prix_valides.items() if abs(p - prix_min) <= EPSILON]
            base.update({
                "prix_min": prix_min,
                "prix_max": prix_max,
                "moins_chere": " & ".join(gagnantes),
                "ex_aequo": len(gagnantes) > 1,
                "ecart_fcfa": prix_max - prix_min,
                "ecart_pct": (prix_max - prix_min) / prix_min * 100.0 if prix_min else 0.0,
                "nb_offres": len(prix_valides),
            })
            lignes_ok.append(base)
        else:
            base["nb_offres"] = len(prix_valides)
            lignes_hors.append(base)

    df_comparatif = pd.DataFrame(lignes_ok)
    if not df_comparatif.empty:
        df_comparatif = df_comparatif.sort_values(
            ["ecart_fcfa", "produit_id"], ascending=[False, True]
        ).reset_index(drop=True)

    df_hors = pd.DataFrame(lignes_hors)
    if not df_hors.empty:
        df_hors = df_hors.sort_values("produit_id").reset_index(drop=True)

    return df_comparatif, df_hors


# ---------------------------------------------------------------------------
# Étape 5 : synthèse
# ---------------------------------------------------------------------------

def synthese(df_comparatif: pd.DataFrame) -> dict:
    """Répond aux trois questions de l'énoncé :

    1. combien de fois chaque enseigne est-elle la moins chère ?
    2. quel est l'écart moyen de chaque enseigne par rapport au prix le plus bas ?
    3. quels sont les trois produits où il y a le plus à gagner à comparer ?
    """
    victoires = {e: 0 for e in ENSEIGNES}
    ex_aequo = {e: 0 for e in ENSEIGNES}
    ecarts = {e: {"fcfa": 0.0, "pct": 0.0, "n": 0} for e in ENSEIGNES}

    for _, l in df_comparatif.iterrows():
        gagnantes = l["moins_chere"].split(" & ")
        for g in gagnantes:
            victoires[g] += 1
            if l["ex_aequo"]:
                ex_aequo[g] += 1

        for ens in ENSEIGNES:
            prix = l["prix_" + CLES[ens]]
            if pd.notna(prix):
                ecart = float(prix) - float(l["prix_min"])
                ecarts[ens]["fcfa"] += ecart
                ecarts[ens]["pct"] += ecart / float(l["prix_min"]) * 100.0
                ecarts[ens]["n"] += 1

    for ens in ENSEIGNES:
        n = ecarts[ens]["n"] or 1
        ecarts[ens]["moyen_fcfa"] = ecarts[ens]["fcfa"] / n
        ecarts[ens]["moyen_pct"] = ecarts[ens]["pct"] / n

    top3 = []
    for _, l in df_comparatif.head(3).iterrows():
        # enseigne la plus chère (parmi les offres valides)
        prix_valides = {
            ens: l["prix_" + CLES[ens]] for ens in ENSEIGNES
            if pd.notna(l["prix_" + CLES[ens]])
        }
        plus_chere = max(prix_valides, key=prix_valides.get)
        top3.append({
            "produit_id": l["produit_id"],
            "nom": l["nom"],
            "categorie": l["categorie"],
            "moins_chere": l["moins_chere"],
            "prix_min": float(l["prix_min"]),
            "prix_max": float(l["prix_max"]),
            "plus_chere": plus_chere,
            "ecart_fcfa": float(l["ecart_fcfa"]),
            "ecart_pct": float(l["ecart_pct"]),
            **{"prix_" + CLES[e]: float(p) for e, p in prix_valides.items()},
        })

    return {
        "nb_produits": len(df_comparatif),
        "victoires": victoires,
        "ex_aequo": ex_aequo,
        "ecarts": ecarts,
        "top3": top3,
    }


# ---------------------------------------------------------------------------
# Étape 6 : panier
# ---------------------------------------------------------------------------

def calculer_panier(
    articles: list[tuple[str, int]],
    offres: list[Offre],
    catalogue: pd.DataFrame,
) -> ResultatPanier:
    """Coût d'un panier dans chaque enseigne, puis article par article
    là où il est le moins cher (« panier malin »)."""
    index = indexer_offres(offres)
    noms = {str(p["produit_id"]): p["nom"] for _, p in catalogue.iterrows()}

    resultat = ResultatPanier()

    for pid, quantite in articles:
        if quantite <= 0:
            continue
        offres_prod = index.get(pid, {})
        prix_unitaires: dict[str, float | None] = {}
        raisons: dict[str, str | None] = {}
        for ens in ENSEIGNES:
            o = offres_prod.get(ens)
            if o is None:
                prix_unitaires[ens] = None
                raisons[ens] = None
            elif o.exploitable() and o.stock is not None and o.stock < quantite:
                prix_unitaires[ens] = None
                raisons[ens] = f"Stock insuffisant ({o.stock} disponible{'s' if o.stock > 1 else ''})"
            elif o.exploitable():
                prix_unitaires[ens] = float(o.prix_paye)
                raisons[ens] = None
            else:
                prix_unitaires[ens] = None
                raisons[ens] = o.raison_exclusion()

        valides = {e: p for e, p in prix_unitaires.items() if p is not None}
        if valides:
            meilleur = min(valides.values())
            meilleure_ens = min(valides, key=valides.get)
        else:
            meilleur, meilleure_ens = None, None

        resultat.lignes.append(LignePanier(
            produit_id=pid, nom=noms.get(pid, pid), quantite=quantite,
            prix_unitaires=prix_unitaires,
            meilleur_prix_unitaire=meilleur,
            meilleure_enseigne=meilleure_ens,
            raisons=raisons,
        ))

        for ens in ENSEIGNES:
            if prix_unitaires[ens] is not None:
                resultat.totaux[ens] = resultat.totaux.get(ens, 0.0) + prix_unitaires[ens] * quantite
                resultat.livraisons[ens] = (resultat.livraisons.get(ens, 0.0)
                                            + offres_prod[ens].livraison * quantite)
            else:
                resultat.manquantes.setdefault(ens, []).append(pid)

        if meilleur is not None:
            resultat.total_optimal += meilleur * quantite

    return resultat