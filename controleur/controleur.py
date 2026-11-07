# -*- coding: utf-8 -*-
"""Contrôleur : exécute le pipeline du modèle et prépare les résultats pour la vue."""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from modele import chargeur, comparaison, historique, nettoyage, performance, rapprochement
from modele.structures import Journal, PANIER_RENTREE, ResultatPanier


@dataclass
class ResultatsAnalyse:
    """Tout ce que la vue a le droit d'afficher, déjà calculé."""
    catalogue: pd.DataFrame
    offres: list
    journal: Journal
    df_comparatif: pd.DataFrame
    df_hors_comparatif: pd.DataFrame
    synthese: dict
    panier_defaut: ResultatPanier
    historique: pd.DataFrame
    bf: pd.DataFrame
    meilleures_semaines: pd.DataFrame
    timings: dict            # étage -> durée en ms
    benchmark: dict
    chemin_export: Path


class Controleur:
    def __init__(self, racine: Path | None = None):
        self.racine = Path(racine) if racine else Path(__file__).resolve().parents[1]
        self.dossier_donnees = self.racine / "donnees"
        self.dossier_sorties = self.racine / "sorties"

    def executer(self) -> ResultatsAnalyse:
        timings: dict[str, float] = {}
        journal = Journal()

        @contextmanager
        def etage(nom: str):
            debut = time.perf_counter()
            yield
            timings[nom] = (time.perf_counter() - debut) * 1000.0

        with etage("Chargement des 3 sources"):
            offres = chargeur.charger_toutes_les_sources(self.dossier_donnees, journal)
            catalogue = chargeur.charger_catalogue(
                self.dossier_donnees / "catalogue_reference.csv", journal)

        with etage("Rapprochement"):
            rapprochement.rapprocher(offres, catalogue, journal)

        with etage("Contrôle de cohérence"):
            nettoyage.controler_coherence(offres, journal)

        with etage("Comparatif et synthèse"):
            df_comparatif, df_hors = comparaison.construire_comparatif(offres, catalogue)
            synthese = comparaison.synthese(df_comparatif)
            journal.log("Comparaison", "info", "—",
                        f"{synthese['nb_produits']} produits comparables (disponibles avec un "
                        "prix exploitable dans au moins deux enseignes)",
                        "Les produits en rupture ou sans prix exploitable sont exclus")
            ex = df_comparatif.loc[df_comparatif["ex_aequo"], "produit_id"].tolist()
            if ex:
                journal.log("Comparaison", "info", "—",
                            f"{len(ex)} ex æquo ({', '.join(ex)}) : deux enseignes au même prix",
                            "Les deux enseignes sont comptées « les moins chères »")

        with etage("Panier de rentrée"):
            panier = comparaison.calculer_panier(list(PANIER_RENTREE), offres, catalogue)

        with etage("Lecture de l'historique"):
            hist = historique.charger_historique(
                self.dossier_donnees / "historique_prix.csv", journal)

        with etage("Recoupement avec l'historique"):
            historique.recouper_offres(hist, offres, journal)

        with etage("Analyses de l'historique"):
            bf = historique.analyse_black_friday(hist)
            semaines = historique.meilleures_semaines(hist)

        with etage("Benchmark liste vs dictionnaire"):
            bench = performance.benchmark_recherche(hist)
        performance.journaliser_benchmark(bench, journal)

        with etage("Export CSV du comparatif"):
            chemin = self.exporter_comparatif(df_comparatif)

        return ResultatsAnalyse(
            catalogue=catalogue, offres=offres, journal=journal,
            df_comparatif=df_comparatif, df_hors_comparatif=df_hors, synthese=synthese,
            panier_defaut=panier, historique=hist, bf=bf, meilleures_semaines=semaines,
            timings=timings, benchmark=bench, chemin_export=chemin,
        )

    def exporter_comparatif(self, df: pd.DataFrame) -> Path:
        """Étape 4 : le tableau comparatif en CSV (« ; », UTF-8 avec BOM pour Excel)."""
        self.dossier_sorties.mkdir(parents=True, exist_ok=True)
        chemin = self.dossier_sorties / "comparatif_prix.csv"
        export = df.rename(columns={
            "prix_ml": "prix_marche_lagune_fcfa",
            "prix_bb": "prix_baobab_shop_fcfa",
            "prix_ci": "prix_comptoir_ivoire_fcfa",
            "prix_min": "prix_minimal_fcfa",
            "prix_max": "prix_maximal_fcfa",
            "moins_chere": "enseigne_la_moins_chere",
            "nb_offres": "nb_enseignes_comparees",
            "remarque_ml": "remarque_marche_lagune",
            "remarque_bb": "remarque_baobab_shop",
            "remarque_ci": "remarque_comptoir_ivoire",
        })
        export.to_csv(chemin, sep=";", index=False, encoding="utf-8-sig", float_format="%.1f")
        return chemin

    @staticmethod
    def calculer_panier(articles: list[tuple[str, int]], res: ResultatsAnalyse) -> ResultatPanier:
        """Service appelé par la vue quand l'utilisateur modifie le panier."""
        return comparaison.calculer_panier(articles, res.offres, res.catalogue)