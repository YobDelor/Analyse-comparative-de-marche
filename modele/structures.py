# -*- coding: utf-8 -*-
"""Structures de données du domaine (couche Modèle, sans dépendance à Streamlit)."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

#: Les trois enseignes, dans un ordre stable pour toute l'application.
ENSEIGNES = ["Marché Lagune", "Baobab Shop", "Comptoir Ivoire"]

#: Clés de colonnes internes (une par enseigne).
CLES = {"Marché Lagune": "ml", "Baobab Shop": "bb", "Comptoir Ivoire": "ci"}

#: Raisons possibles d'exclusion d'une offre.
RAISON_RUPTURE = "Rupture de stock"
RAISON_SUSPECT = "Prix aberrant"
RAISON_SUR_DEMANDE = "Prix sur demande"
RAISON_ABSENT = "Prix non renseigné"

#: Panier de rentrée imposé par l'énoncé (étape 6).
PANIER_RENTREE = [("P04", 1), ("P12", 1), ("P14", 2), ("P15", 1), ("P28", 1)]

#: Semaine du Black Friday 2025.
BF_DEBUT = "2025-11-24"
BF_FIN = "2025-11-30"


def format_nombre(valeur: float, decimales: int = 0) -> str:
    """Formate 20876 en « 20 876 » et 0.27 en « 0,27 » (à la française)."""
    return f"{valeur:,.{decimales}f}".replace(",", "\u00a0").replace(".", ",")


# ---------------------------------------------------------------------------
# Journal de nettoyage (étape 2)
# ---------------------------------------------------------------------------

@dataclass
class EntreeJournal:
    source: str      # enseigne ou étape du pipeline concerné
    gravite: str     # "info" | "avertissement" | "critique"
    ref: str         # référence de l'article, ou "—" pour une note globale
    probleme: str
    traitement: str


@dataclass
class Journal:
    entrees: list[EntreeJournal] = field(default_factory=list)

    def log(self, source: str, gravite: str, ref: str, probleme: str, traitement: str) -> None:
        self.entrees.append(EntreeJournal(source, gravite, ref, probleme, traitement))

    def compter(self, gravite: str) -> int:
        return sum(1 for e in self.entrees if e.gravite == gravite)

    def vers_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [(e.source, e.gravite, e.ref, e.probleme, e.traitement) for e in self.entrees],
            columns=["source", "gravite", "ref", "probleme", "traitement"],
        )


# ---------------------------------------------------------------------------
# Offre : un article vu dans une enseigne, après nettoyage
# ---------------------------------------------------------------------------

@dataclass
class Offre:
    """Structure commune aux trois sources.

    ``prix_paye`` est ce que le client paie réellement (FCFA) :
      * Marché Lagune  : prix affiché (livraison incluse) ;
      * Baobab Shop    : amount + delivery_fee ;
      * Comptoir Ivoire: prix catalogue × (1 − remise %).
    ``probleme`` explique pourquoi le prix n'est pas exploitable, sinon None.
    """
    enseigne: str
    ref: str
    designation: str
    prix_paye: float | None = None
    prix_affiche: float | None = None  # prix de la source avant livraison / remise
    disponible: bool = True
    stock: int | None = None           # quantité connue ; None si la source ne la donne pas
    livraison: float = 0.0             # frais de livraison par article (Baobab Shop)
    produit_id: str | None = None      # rempli par le rapprochement
    probleme: str | None = None

    def exploitable(self) -> bool:
        """Entre dans le comparatif : rapprochée, en stock, avec un prix sain."""
        return (self.produit_id is not None and self.disponible
                and self.prix_paye is not None and self.probleme is None)

    def raison_exclusion(self) -> str | None:
        if self.exploitable():
            return None
        if self.probleme is not None:
            return self.probleme
        if not self.disponible:
            return RAISON_RUPTURE
        if self.prix_paye is None:
            return RAISON_ABSENT
        return None


# ---------------------------------------------------------------------------
# Panier (étape 6)
# ---------------------------------------------------------------------------

@dataclass
class LignePanier:
    produit_id: str
    nom: str
    quantite: int
    prix_unitaires: dict[str, float | None]   # enseigne -> prix (None si non exploitable)
    meilleure_enseigne: str | None
    meilleur_prix_unitaire: float | None
    raisons: dict[str, str | None]            # enseigne -> raison d'exclusion


@dataclass
class ResultatPanier:
    lignes: list[LignePanier] = field(default_factory=list)
    totaux: dict[str, float] = field(default_factory=dict)          # enseigne -> total
    manquantes: dict[str, list[str]] = field(default_factory=dict)  # enseigne -> produits exclus
    livraisons: dict[str, float] = field(default_factory=dict)      # enseigne -> frais inclus dans le total
    total_optimal: float = 0.0   # chaque article acheté là où il est le moins cher

    def classement_complets(self) -> list[tuple[str, float]]:
        """Enseignes dont le panier est complet, du moins cher au plus cher."""
        complets = [(e, t) for e, t in self.totaux.items() if not self.manquantes.get(e)]
        return sorted(complets, key=lambda kv: kv[1])

    def avance_sur_suivante(self) -> dict | None:
        """Avance de la meilleure enseigne sur la suivante, et frais de livraison
        de la suivante : si l'avance est plus petite, le classement tient aux frais."""
        classement = self.classement_complets()
        if len(classement) < 2:
            return None
        (meilleure, total), (suivante, total_suivante) = classement[0], classement[1]
        return {"meilleure": meilleure, "total": total, "suivante": suivante,
                "avance": total_suivante - total,
                "livraison_suivante": self.livraisons.get(suivante, 0.0)}

    def meilleur_panier_complet(self) -> tuple[str, float] | None:
        """Enseigne au total le plus bas parmi celles qui ont tous les articles."""
        complets = {e: t for e, t in self.totaux.items() if not self.manquantes.get(e)}
        return min(complets.items(), key=lambda kv: kv[1]) if complets else None