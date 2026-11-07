# -*- coding: utf-8 -*-
"""Étape 6 — panier de rentrée."""
import pandas as pd
import streamlit as st

from controleur.controleur import Controleur
from modele.structures import ENSEIGNES, PANIER_RENTREE
from vue.etat import obtenir_resultats
from vue.formats import entier, fcfa, surligner_min

res = obtenir_resultats()

st.title("Étape 6 · Panier de rentrée")
st.caption("1 Tecno Spark 20, 1 Lenovo IdeaPad 3, 2 clés USB SanDisk, 1 disque dur Seagate "
           "et 1 micro-ondes Samsung.")

# --- quantités (modifiables) ------------------------------------------------
defaut = dict(PANIER_RENTREE)
quantites = pd.DataFrame({
    "produit_id": res.catalogue["produit_id"],
    "Produit": res.catalogue["nom"],
    "Quantité": [defaut.get(pid, 0) for pid in res.catalogue["produit_id"]],
})
with st.expander("Modifier le panier"):
    quantites = st.data_editor(
        quantites, hide_index=True, disabled=["produit_id", "Produit"],
        column_config={"Quantité": st.column_config.NumberColumn(min_value=0, max_value=10, step=1)})

articles = [(r.produit_id, int(r.Quantité)) for r in quantites.itertuples() if r.Quantité > 0]
if not articles:
    st.info("Le panier est vide.")
    st.stop()
panier = Controleur.calculer_panier(articles, res)

# --- détail par article -----------------------------------------------------
def non_retenu(ligne) -> str:
    return " ; ".join(f"{e} : {r}" for e, r in ligne.raisons.items() if r)

detail = pd.DataFrame([{
    "Produit": f"{l.produit_id} · {l.nom}",
    "Qté": l.quantite,
    **{e: l.prix_unitaires[e] * l.quantite if l.prix_unitaires[e] is not None else None
       for e in ENSEIGNES},
    "Acheter chez": l.meilleure_enseigne or "—",
    "Offres non retenues": non_retenu(l),
} for l in panier.lignes])
st.dataframe(detail.style.apply(surligner_min, axis=1, subset=ENSEIGNES)
             .format(entier, subset=ENSEIGNES, na_rep="—"), hide_index=True)
st.caption("Montants = prix unitaire × quantité, en FCFA. En vert : l'enseigne la moins chère.")

# --- totaux -----------------------------------------------------------------
st.subheader("Total du panier")
colonnes = st.columns(len(ENSEIGNES) + 1)
for col, ens in zip(colonnes, ENSEIGNES):
    manquants = panier.manquantes.get(ens)
    total = panier.totaux.get(ens)
    col.metric(ens, fcfa(total) if total is not None else "—")
    if manquants:
        col.caption(f"Panier incomplet : {', '.join(manquants)} non retenu")
colonnes[-1].metric("Chaque article au meilleur prix", fcfa(panier.total_optimal))

meilleur = panier.meilleur_panier_complet()
avance = panier.avance_sur_suivante()
if avance:
    texte = (f"Meilleur panier dans une seule enseigne : **{avance['meilleure']}** "
             f"({fcfa(avance['total'])}), avec {fcfa(avance['avance'])} d'avance sur "
             f"{avance['suivante']}.")
    if avance["avance"] <= avance["livraison_suivante"]:
        st.warning(texte + f" Cette avance ne dépasse pas les frais de livraison de "
                   f"{avance['suivante']} ({fcfa(avance['livraison_suivante'])}) : le "
                   "classement dépend du mode de réception (livraison ou retrait).")
    else:
        st.success(texte)
elif meilleur:
    st.success(f"Seul panier complet : **{meilleur[0]}** ({fcfa(meilleur[1])}).")
if meilleur:
    st.write(f"En répartissant les achats : **{fcfa(panier.total_optimal)}**, soit "
             f"{fcfa(meilleur[1] - panier.total_optimal)} d'économie, à mettre en regard des "
             "déplacements et livraisons supplémentaires.")

frais = ", ".join(f"{e} {fcfa(v)}" for e, v in panier.livraisons.items() if v > 0)
st.caption(
    "Un total marqué « incomplet » n'est pas comparable aux autres : un article n'a pas de "
    "prix exploitable dans cette enseigne, ou son stock est inférieur à la quantité demandée. "
    f"Frais de livraison inclus dans les totaux : {frais or 'aucun'}. Marché Lagune : livraison "
    "comprise dans le prix affiché, mais aucune quantité en stock indiquée. Comptoir Ivoire : "
    "retrait en boutique, transport non compté.")