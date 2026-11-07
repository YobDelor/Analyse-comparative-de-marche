# -*- coding: utf-8 -*-
"""Résumé : les chiffres clés et les réponses principales."""
import streamlit as st

from vue.etat import obtenir_resultats
from vue.formats import fcfa, pct

res = obtenir_resultats()
s, panier, journal = res.synthese, res.panier_defaut, res.journal

st.title("Où acheter l'électronique à Abidjan ?")
st.markdown(":blue[**Marché Lagune**] (site) · :green[**Baobab Shop**] (application) · "
            ":orange[**Comptoir Ivoire**] (boutique) — comparés sur le prix réellement payé. "
            "Données fictives.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Produits au catalogue", len(res.catalogue))
c2.metric("Offres collectées", len(res.offres))
c3.metric("Produits comparables", s["nb_produits"],
          help="Disponibles, avec un prix exploitable, dans au moins deux enseignes.")
c4.metric("Anomalies traitées", journal.compter("avertissement") + journal.compter("critique"))

st.subheader("À retenir")
carte1, carte2, carte3 = st.columns(3)

victoires = s["victoires"]
champion = max(victoires, key=victoires.get)
with carte1.container(border=True):
    st.markdown("##### Prix le plus bas")
    st.write(f"**{champion}** est la moins chère sur {victoires[champion]} des "
             f"{s['nb_produits']} produits. Aucune enseigne ne gagne partout.")

with carte2.container(border=True):
    st.markdown("##### Panier de rentrée")
    meilleur = panier.meilleur_panier_complet()
    if meilleur:
        enseigne, total = meilleur
        st.write(f"**{fcfa(panier.total_optimal)}** en achetant chaque article au meilleur "
                 f"prix, contre {fcfa(total)} dans la meilleure enseigne unique "
                 f"({enseigne}) : {fcfa(total - panier.total_optimal)} d'économie.")
        avance = panier.avance_sur_suivante()
        if avance:
            st.caption(f"Avance de {enseigne} sur {avance['suivante']} : {fcfa(avance['avance'])}. "
                       f"À comparer aux frais de livraison de {avance['suivante']} "
                       f"({fcfa(avance['livraison_suivante'])}).")
    else:
        st.write(f"**{fcfa(panier.total_optimal)}** en achetant chaque article au meilleur prix.")

with carte3.container(border=True):
    st.markdown("##### Black Friday 2025")
    st.write("Prix de la semaine vs moyenne annuelle :")
    for r in res.bf.itertuples():
        st.write(f"- **{r.source}** : {pct(r.ecart_pct, signe=True)}")

with st.expander("Comment le « prix payé » est-il calculé ?"):
    st.markdown(
        "- **Marché Lagune** : prix affiché, livraison déjà incluse.\n"
        "- **Baobab Shop** : montant + frais de livraison.\n"
        "- **Comptoir Ivoire** : prix catalogue − remise, retrait en boutique.\n\n"
        "Un produit en rupture, sans prix ou au prix aberrant n'est jamais retenu "
        "comme « le moins cher ».")