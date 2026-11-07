# -*- coding: utf-8 -*-
"""Analyse de l'historique des prix (étape 7), vectorisée avec pandas."""
from __future__ import annotations

import pandas as pd

from .structures import BF_DEBUT, BF_FIN, Journal, Offre, RAISON_SUSPECT, format_nombre


def charger_historique(chemin, journal: Journal) -> pd.DataFrame:
    df = pd.read_csv(chemin, dtype={"produit_id": str, "source": str})
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")

    par_source = ", ".join(f"{s} : {format_nombre(n)}" for s, n in df["source"].value_counts().items())
    journal.log("Historique", "info", "—",
                f"{format_nombre(len(df))} relevés du {df['date'].min():%d/%m/%Y} au "
                f"{df['date'].max():%d/%m/%Y} ({par_source}). Comptoir Ivoire ne change ses "
                "prix qu'une fois par semaine, et ce sont des prix catalogue sans la remise",
                "Chargé en DataFrame ; comparaisons faites sur les prix affichés")
    return df


def _ecart_a_la_moyenne(hist: pd.DataFrame, masque: pd.Series) -> pd.Series:
    """Écart relatif (%) de la moyenne des lignes ``masque`` à la moyenne annuelle,
    calculé produit par produit pour ne pas mélanger les gammes de prix."""
    cles = ["source", "produit_id"]
    annee = hist.groupby(cles)["prix_fcfa"].mean()
    periode = hist[masque].groupby(cles)["prix_fcfa"].mean()
    return (periode / annee - 1.0) * 100.0


def analyse_black_friday(hist: pd.DataFrame) -> pd.DataFrame:
    """Par enseigne : écart moyen (%) des prix du Black Friday à la moyenne annuelle.
    Négatif = les prix étaient plus bas pendant le Black Friday."""
    ecart = _ecart_a_la_moyenne(hist, hist["date"].between(BF_DEBUT, BF_FIN)).dropna()
    return (ecart.groupby("source").agg(ecart_pct="mean", nb_produits="size")
            .reset_index().sort_values("ecart_pct").reset_index(drop=True))


def detail_black_friday_produit(hist: pd.DataFrame, produit_id: str) -> pd.DataFrame:
    """Prix moyen du Black Friday vs moyenne annuelle d'un produit, par enseigne."""
    h = hist[hist["produit_id"] == produit_id]
    bf = h[h["date"].between(BF_DEBUT, BF_FIN)].groupby("source")["prix_fcfa"].mean()
    annee = h.groupby("source")["prix_fcfa"].mean()
    out = pd.DataFrame({"prix_bf": bf, "prix_annee": annee}).dropna()
    out["ecart_pct"] = (out["prix_bf"] / out["prix_annee"] - 1.0) * 100.0
    return out.reset_index()


def meilleures_semaines(hist: pd.DataFrame) -> pd.DataFrame:
    """Semaine (lundi-dimanche) la moins chère de chaque enseigne, en écart (%)
    à la moyenne annuelle de chaque produit, moyenné sur les produits."""
    h = hist.assign(lundi=hist["date"] - pd.to_timedelta(hist["date"].dt.weekday, unit="D"))
    annee = h.groupby(["source", "produit_id"])["prix_fcfa"].transform("mean")
    h["ratio"] = h["prix_fcfa"] / annee
    par_semaine = h.groupby(["source", "lundi"])["ratio"].mean().reset_index()
    best = par_semaine.loc[par_semaine.groupby("source")["ratio"].idxmin()].copy()
    best["ecart_pct"] = (best["ratio"] - 1.0) * 100.0
    best["semaine_du"] = best["lundi"].dt.strftime("%d/%m/%Y")
    return best[["source", "semaine_du", "ecart_pct"]].reset_index(drop=True)


def courbe_produit(hist: pd.DataFrame, produit_id: str) -> pd.DataFrame:
    """Une colonne par enseigne, un prix par jour. Le prix de Comptoir Ivoire, relevé
    chaque semaine, est reporté sur les jours suivants (il reste valable jusqu'au
    prochain relevé)."""
    h = hist[hist["produit_id"] == produit_id]
    return h.pivot_table(index="date", columns="source", values="prix_fcfa").ffill()


def recouper_offres(hist: pd.DataFrame, offres: list[Offre], journal: Journal) -> None:
    """Compare le prix affiché de chaque offre au dernier relevé de l'historique.

    Un écart ne corrige rien : il est signalé. Pour une offre déjà exclue comme
    aberrante, l'historique sert de preuve que l'erreur vient bien du fichier.
    """
    dernier = {(l.source, l.produit_id): (l.date, l.prix_fcfa)
               for l in hist.sort_values("date").drop_duplicates(["source", "produit_id"], keep="last")
               .itertuples()}
    comparees = identiques = 0
    for o in offres:
        if o.produit_id is None or o.prix_affiche is None or (o.enseigne, o.produit_id) not in dernier:
            continue
        date, prix = dernier[(o.enseigne, o.produit_id)]
        comparees += 1
        if abs(o.prix_affiche - prix) <= 0.5:
            identiques += 1
            continue
        avant = f"{format_nombre(o.prix_affiche)} FCFA dans le fichier"
        apres = f"{format_nombre(prix)} FCFA au dernier relevé ({date:%d/%m/%Y})"
        if o.probleme == RAISON_SUSPECT:
            journal.log("Historique", "info", o.ref, f"{avant}, {apres} : l'erreur de saisie est confirmée",
                        "Offre toujours exclue : aucune correction automatique")
        else:
            journal.log("Historique", "avertissement", o.ref, f"{avant}, {apres}",
                        "Prix du fichier conservé ; à vérifier auprès de l'enseigne")
    journal.log("Historique", "info", "—",
                f"Recoupement des prix des fichiers avec le dernier relevé : {identiques} identiques "
                f"sur {comparees} comparés",
                "Les écarts éventuels sont listés ci-dessus")
