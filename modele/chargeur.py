# -*- coding: utf-8 -*-
"""Chargement des trois sources (étape 1) : CSV, JSON, Excel -> liste d'``Offre``."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .nettoyage import (
    convertir_disponibilite,
    convertir_entier,
    convertir_prix,
    nettoyer_designation,
)
from .structures import (
    ENSEIGNES,
    Journal,
    Offre,
    RAISON_ABSENT,
    RAISON_SUR_DEMANDE,
    RAISON_SUSPECT,
    format_nombre,
)

ML, BB, CI = ENSEIGNES


def _fcfa(valeur: float) -> str:
    return f"{format_nombre(valeur)} FCFA"


def charger_catalogue(chemin: Path, journal: Journal) -> pd.DataFrame:
    df = pd.read_csv(chemin)
    df["produit_id"] = df["produit_id"].astype(str).str.strip()
    journal.log("Catalogue", "info", "—",
                f"{len(df)} produits de référence ({df['produit_id'].min()} à "
                f"{df['produit_id'].max()}), {df['categorie'].nunique()} catégories",
                "Chargé comme référence commune du rapprochement")
    return df


# ---------------------------------------------------------------------------
# Marché Lagune — CSV « Excel français »
# ---------------------------------------------------------------------------

def charger_marche_lagune(chemin: Path, journal: Journal) -> list[Offre]:
    brut = pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8-sig")
    attendu = ["reference", "designation", "prix", "ancien_prix", "disponibilite"]
    manquantes = [c for c in attendu if c not in brut.columns]
    if manquantes:
        journal.log(ML, "critique", "—", f"Colonnes absentes : {manquantes}", "Source ignorée")
        return []

    journal.log(ML, "info", "—",
                "CSV « Excel français » : séparateur « ; », UTF-8 avec BOM. Prix en texte "
                "(« 102 900 FCFA »), livraison déjà incluse dans le prix affiché",
                "Lu avec sep=';' et encoding='utf-8-sig' ; prix converti en nombre ; "
                "prix payé = prix affiché. Aucune quantité en stock n'est donnée : seule la "
                "mention de disponibilité est connue")

    offres: list[Offre] = []
    vues: set[str] = set()
    ruptures: list[str] = []

    for i, ligne in brut.iterrows():
        ref = nettoyer_designation(ligne["reference"])
        numero = i + 2  # +1 pour l'en-tête, +1 car la numérotation commence à 1

        if ref in vues:
            journal.log(ML, "avertissement", ref,
                        f"Doublon : référence déjà vue, seconde occurrence en ligne {numero}",
                        "Seule la première occurrence est conservée")
            continue
        vues.add(ref)

        designation = nettoyer_designation(ligne["designation"])
        if designation != str(ligne["designation"]):
            journal.log(ML, "info", ref,
                        f"Espaces parasites dans la désignation : « {ligne['designation']} »",
                        f"Normalisée en « {designation} »")

        prix, anomalie = convertir_prix(ligne["prix"])
        ancien, _ = convertir_prix(ligne["ancien_prix"])
        probleme = None

        if anomalie is not None:
            sur_demande = anomalie.lower() == "prix sur demande"
            journal.log(ML, "avertissement", ref,
                        f"Prix non chiffré : « {anomalie} »" if sur_demande
                        else f"Prix illisible : « {anomalie} »",
                        "Offre conservée pour le rapprochement, prix non exploitable")
            probleme = RAISON_SUR_DEMANDE if sur_demande else RAISON_ABSENT
        elif prix is None:
            journal.log(ML, "avertissement", ref, "Prix vide",
                        "Offre conservée pour le rapprochement, prix non exploitable")
            probleme = RAISON_ABSENT
        elif ancien and prix > 3 * ancien:
            journal.log(ML, "critique", ref,
                        f"Prix incohérent : {_fcfa(prix)} affichés pour un prix barré de "
                        f"{_fcfa(ancien)} (×{format_nombre(prix / ancien, 1)}) — erreur de saisie probable",
                        "Prix exclu comme « aberrant » : le corriger à la main reviendrait "
                        "à inventer une donnée")
            probleme = RAISON_SUSPECT

        disponible = convertir_disponibilite(ligne["disponibilite"], journal, ML, ref)
        if not disponible:
            ruptures.append(ref)

        offres.append(Offre(enseigne=ML, ref=ref, designation=designation,
                            prix_paye=prix, prix_affiche=prix, disponible=disponible,
                            probleme=probleme))

    if ruptures:
        journal.log(ML, "avertissement", "—",
                    f"{len(ruptures)} articles en rupture de stock ({', '.join(ruptures)})",
                    "Exclus du comparatif : une rupture ne peut pas être « la moins chère »")
    return offres


# ---------------------------------------------------------------------------
# Baobab Shop — JSON de l'API de l'application mobile
# ---------------------------------------------------------------------------

def charger_baobab(chemin: Path, journal: Journal) -> list[Offre]:
    with open(chemin, encoding="utf-8") as f:
        donnees = json.load(f)
    items = donnees.get("items", [])

    if donnees.get("count") != len(items):
        journal.log(BB, "avertissement", "—",
                    f"« count » annoncé ({donnees.get('count')}) ≠ articles lus ({len(items)})",
                    "La liste des items fait foi")
    journal.log(BB, "info", "—",
                f"JSON, devise {donnees.get('currency')} (= FCFA). Le client paie le "
                "montant + les frais de livraison",
                "Prix payé = amount + delivery_fee")

    offres: list[Offre] = []
    for i, it in enumerate(items, start=1):
        sku = str(it.get("sku", f"BB#{i}"))
        pricing = it.get("pricing") or {}
        montant = pricing.get("amount")
        livraison = pricing.get("delivery_fee") or 0

        probleme = None
        prix_paye = None
        if montant is None:
            journal.log(BB, "avertissement", sku, "Prix absent (amount = null)",
                        "Offre conservée pour le rapprochement, prix non exploitable")
            probleme = RAISON_ABSENT
        else:
            prix_paye = float(montant) + float(livraison)

        stock = int(it.get("stock") or 0)
        disponible = stock > 0
        if not disponible:
            journal.log(BB, "avertissement", sku, "Stock épuisé (stock = 0)",
                        "Exclu du comparatif (rupture de stock)")

        offres.append(Offre(enseigne=BB, ref=sku,
                            designation=nettoyer_designation(it.get("title", "")),
                            prix_paye=prix_paye,
                            prix_affiche=float(montant) if montant is not None else None,
                            disponible=disponible, stock=stock, livraison=float(livraison),
                            probleme=probleme))
    return offres


# ---------------------------------------------------------------------------
# Comptoir Ivoire — classeur Excel du gérant
# ---------------------------------------------------------------------------

def charger_comptoir_ivoire(chemin: Path, journal: Journal) -> list[Offre]:
    brut = pd.read_excel(chemin, sheet_name="Tarifs octobre 2026", header=2, dtype=object)

    journal.log(CI, "info", "—",
                "Excel : titre en ligne 1, en-têtes en ligne 3, données dès la ligne 4. "
                "Le client paie le prix catalogue moins la remise, en boutique (sans livraison)",
                "Lu avec header=2 ; prix payé = prix catalogue × (1 − remise / 100)")

    offres: list[Offre] = []
    for i, ligne in brut.iterrows():
        code = nettoyer_designation(ligne["Code"])
        numero = i + 4

        brut_prix = ligne["Prix catalogue (FCFA)"]
        prix, anomalie = convertir_prix(brut_prix)
        if anomalie is not None:
            journal.log(CI, "avertissement", code,
                        f"Prix catalogue illisible : « {anomalie} » (ligne {numero})",
                        "Offre ignorée")
            continue
        if isinstance(brut_prix, str):
            journal.log(CI, "info", code,
                        f"Prix catalogue stocké en texte : « {brut_prix} »",
                        f"Converti en {_fcfa(prix)}")

        remise = pd.to_numeric(ligne["Remise (%)"], errors="coerce")
        remise = 0.0 if pd.isna(remise) else float(remise)

        quantite = convertir_entier(ligne["Quantité en rayon"])
        disponible = bool(quantite and quantite > 0)
        if not disponible:
            journal.log(CI, "avertissement", code,
                        f"Rayon vide (quantité en rayon = {quantite})",
                        "Exclu du comparatif (rupture de stock)")

        prix_paye = round(prix * (1.0 - remise / 100.0)) if prix is not None else None
        offres.append(Offre(enseigne=CI, ref=code,
                            designation=nettoyer_designation(ligne["Article"]),
                            prix_paye=prix_paye, prix_affiche=prix, disponible=disponible,
                            stock=quantite or 0,
                            probleme=None if prix is not None else RAISON_ABSENT))
    return offres


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def charger_toutes_les_sources(dossier: Path, journal: Journal) -> list[Offre]:
    """Étape 1 : les trois enseignes dans une même liste d'``Offre``."""
    sources = [
        (charger_marche_lagune, "marche_lagune.csv"),
        (charger_baobab, "baobab_shop.json"),
        (charger_comptoir_ivoire, "comptoir_ivoire.xlsx"),
    ]
    offres: list[Offre] = []
    for fonction, fichier in sources:
        chemin = dossier / fichier
        if chemin.exists():
            offres.extend(fonction(chemin, journal))
        else:
            journal.log("Chargement", "critique", fichier, "Fichier introuvable", "Source ignorée")

    detail = ", ".join(f"{e} : {sum(o.enseigne == e for o in offres)}" for e in ENSEIGNES)
    journal.log("Chargement", "info", "—", f"{len(offres)} offres chargées ({detail})",
                "Trois formats fusionnés dans une structure commune (Offre)")
    return offres