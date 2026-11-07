# Comparateur de prix de l'électronique à Abidjan

> Exercice *Analyse comparative de marché* (DA Python · L2 Informatique · séance 3).
> **Les données sont entièrement fictives** : Marché Lagune, Baobab Shop et Comptoir Ivoire n'existent pas.

Un client veut acheter de l'électronique à Abidjan et hésite entre trois enseignes. L'application collecte
leurs trois fichiers (CSV, JSON, Excel), les nettoie en consignant chaque anomalie, les rapproche d'un
catalogue de 30 produits, compare les **prix réellement payés**, calcule le panier de rentrée, étudie
un an d'historique (Black Friday compris) et mesure ses propres performances.

L'énoncé complet est dans [`LISEZ-MOI.md`](LISEZ-MOI.md).

## Sommaire

1. [Démarrage rapide](#démarrage-rapide)
2. [Les pages de l'application](#les-pages-de-lapplication)
3. [Architecture](#architecture)
4. [Fonctionnement du pipeline](#fonctionnement-du-pipeline)
5. [Les règles de calcul](#les-règles-de-calcul)
6. [Anomalies détectées](#anomalies-détectées)
7. [Résultats](#résultats)
8. [Performance et structures de données](#performance-et-structures-de-données)
9. [Limites et pistes d'amélioration](#limites-et-pistes-damélioration)
10. [Dépannage](#dépannage)

## Démarrage rapide

Python 3.10 ou plus récent.

```bash
pip install -r requirements.txt
streamlit run app.py
```

L'application s'ouvre sur <http://localhost:8501>. Le pipeline s'exécute au premier affichage (environ
0,4 s), puis son résultat est conservé en cache : la navigation entre les pages est instantanée.

Le tableau comparatif exigé par l'énoncé est aussi écrit dans `sorties/comparatif_prix.csv`
(séparateur `;`, UTF-8 avec BOM, pour s'ouvrir correctement dans un Excel français).

## Les pages de l'application

| Page | Étape | Contenu |
|---|---|---|
| **Résumé** | — | chiffres clés, trois conclusions (prix, panier, Black Friday), règles de calcul du prix payé |
| **Nettoyage** | 2 | journal de toutes les anomalies, filtrable par gravité et par source |
| **Comparatif** | 4 | prix payé chez chaque enseigne, meilleur prix en vert, écart, export CSV, produits non comparables |
| **Synthèse** | 5 | victoires par enseigne, écart moyen au meilleur prix, trois plus gros écarts |
| **Panier** | 6 | panier de rentrée par enseigne et au meilleur prix article par article, quantités modifiables |
| **Historique** | 7 | Black Friday vs moyenne annuelle, meilleure semaine, courbe de prix de chaque produit |
| **Performance** | 8 | temps par étage, liste contre dictionnaire, structures retenues |

Chaque enseigne garde la même couleur dans tous les graphiques : bleu pour Marché Lagune,
vert pour Baobab Shop, orange pour Comptoir Ivoire.

## Architecture

Le projet suit le modèle MVC. Chaque couche a un rôle strict.

```
comparateur-prix/
├── app.py                  navigation entre les pages
├── requirements.txt
├── .streamlit/config.toml  thème (couleurs)
│
├── modele/                 logique métier, sans aucune dépendance à Streamlit
│   ├── structures.py         Offre, Journal, ResultatPanier, constantes
│   ├── chargeur.py           étape 1 : lecture CSV, JSON, Excel
│   ├── nettoyage.py          étape 2 : conversions et contrôle de cohérence
│   ├── rapprochement.py      étape 3 : article -> produit_id
│   ├── comparaison.py        étapes 4, 5, 6 : comparatif, synthèse, panier
│   ├── historique.py         étape 7 : Black Friday, meilleures semaines
│   └── performance.py        étape 8 : benchmark liste vs dictionnaire
│
├── controleur/
│   └── controleur.py       exécute le pipeline, chronomètre, exporte le CSV
│
├── vue/                    affichage uniquement
│   ├── etat.py               exécution unique du pipeline (cache)
│   ├── formats.py            formats français, couleurs, styles de tableaux
│   ├── graphiques.py         barres aux couleurs des enseignes
│   └── pages/                une page par étape
│
├── donnees/                les 5 fichiers sources
└── sorties/                comparatif_prix.csv (généré)
```

| Couche | A le droit de | N'a pas le droit de |
|---|---|---|
| **Modèle** | lire `donnees/`, calculer, journaliser | importer Streamlit |
| **Contrôleur** | appeler le modèle, chronométrer, préparer les résultats | connaître l'interface |
| **Vue** | formater, afficher, relayer les actions de l'utilisateur | lire des fichiers, calculer |

Exemple : quand l'utilisateur change une quantité dans la page *Panier*, la vue appelle
`Controleur.calculer_panier()`, qui interroge le modèle et renvoie un `ResultatPanier` que la vue affiche.

## Fonctionnement du pipeline

```
 CSV ┐
JSON ├─► chargement ─► rapprochement ─► contrôle ─► comparatif ─► synthèse ─► panier
XLSX ┘   + nettoyage    (produit_id)     croisé       (23 produits)
                                                                      │
 historique_prix.csv ─► Black Friday + meilleures semaines            ▼
                                                              export CSV + pages
```

**Rapprochement.** Chaque enseigne écrit les noms à sa façon (« SAMSUNG GALAXY A15 (128GB) »,
« Galaxy A15 128GB - Samsung », « Samsun Galaxy A15 128Go »). Deux niveaux :
1. des motifs regex par produit (indice de modèle comme `a15`, `spark`, `m185`), sur un texte normalisé
   (minuscules, sans accents ni ponctuation) : déterministe et explicable ;
2. en secours, une similarité floue (`difflib`) avec les noms du catalogue, seuil 0,50.

Sur les données fournies, les 76 offres sont rapprochées par motif, sans recours au repli flou.

## Les règles de calcul

**Prix payé** (ce qui sort réellement du portefeuille du client) :

| Enseigne | Prix payé |
|---|---|
| Marché Lagune | prix affiché, livraison déjà incluse |
| Baobab Shop | `amount` + `delivery_fee` |
| Comptoir Ivoire | prix catalogue × (1 − remise / 100), retrait en boutique |

**Offre retenue ou non.** Une offre n'entre dans le classement que si elle est rapprochée, en stock,
avec un prix numérique et non aberrant. Sinon elle apparaît dans la colonne « Offres non retenues » avec
sa raison : rupture de stock, prix sur demande, prix non renseigné, prix aberrant.

**Prix aberrant.** Détecté de deux façons : prix supérieur à 3 fois le prix barré (Marché Lagune), ou
supérieur à 3 fois la médiane des autres enseignes. Il est **exclu et non corrigé** : deviner la bonne
valeur reviendrait à inventer une donnée.

**Stock.** Dans le panier, une offre n'est retenue que si le stock couvre la quantité demandée
(deux clés USB exigent un stock d'au moins 2). Marché Lagune ne donne aucune quantité, seulement
« En stock », « Stock limité » ou « Rupture » : la quantité n'y est donc pas vérifiable.

**Recoupement avec l'historique.** Le prix affiché de chaque offre est comparé au dernier relevé de
l'historique. Sur les données fournies, 72 prix sur 73 sont identiques ; l'écart restant est le Spark 20
de Marché Lagune (779 000 FCFA dans le fichier, 77 900 FCFA dans l'historique), ce qui confirme une
erreur de saisie. L'offre reste exclue : aucune correction automatique, l'écart est seulement consigné.

**Ex æquo.** Deux enseignes à moins de 0,5 FCFA l'une de l'autre sont comptées toutes les deux comme
« la moins chère ».

**Black Friday.** Pour chaque produit et chaque enseigne : prix moyen du 24 au 30 novembre 2025 comparé
au prix moyen de l'année entière, puis moyenne des écarts par enseigne (en pourcentage, pour ne pas
laisser les articles chers écraser les petits). Négatif = prix plus bas pendant le Black Friday.
Comptoir Ivoire change ses prix une fois par semaine et l'historique donne son prix catalogue, sans la remise.

## Anomalies détectées

Le journal complet (une trentaine d'entrées, avec le numéro de ligne) est consultable dans la page
*Nettoyage*. Les principales :

| Gravité | Source | Problème | Traitement |
|---|---|---|---|
| critique | Marché Lagune | Spark 20 à 779 000 FCFA pour un prix barré de 88 700 (×8,8) | exclu comme prix aberrant |
| avertissement | Marché Lagune | doublons ML-1000 et ML-1147 | première occurrence conservée |
| avertissement | Marché Lagune | « Prix sur demande » (écran 24") et prix vide (mixeur) | prix non exploitables |
| avertissement | Marché Lagune | 6 articles en rupture de stock | exclus du classement |
| avertissement | Baobab Shop | `amount = null` (fer Philips), 3 stocks à 0 | prix absent, ruptures exclues |
| avertissement | Comptoir Ivoire | 2 rayons vides (TV 43", ventilateur) | exclus du classement |
| info | Marché Lagune | prix en texte « 102 900 FCFA », espaces parasites | convertis et normalisés |
| info | Comptoir Ivoire | prix en texte « 279 300 », coquille « Samsun » | converti ; rapproché grâce à l'indice `A15` |
| info | Les trois sources | livraison incluse / ajoutée / remise déduite | règle du prix payé appliquée partout |
| info | Historique | Spark 20 : 779 000 FCFA dans le fichier, 77 900 au dernier relevé | erreur de saisie confirmée, offre toujours exclue |

## Résultats

Calculés sur les données fournies :

- **76 offres** collectées, **76 rapprochées**, **23 produits comparables** dans au moins deux enseignes.
- **Moins chère** : Comptoir Ivoire sur 10 produits, Baobab Shop sur 9, Marché Lagune sur 6
  (P16 et P27 sont des ex æquo).
- **Écart moyen au meilleur prix** : Baobab Shop ≈ 2 700 FCFA, Comptoir Ivoire ≈ 6 700, Marché Lagune ≈ 8 000.
- **Plus gros écarts** : HP 250 G9 (52 800 FCFA, 14,9 %), iPhone 13 (26 500), climatiseur LG (26 000).
- **Panier de rentrée** : 491 500 FCFA chez Baobab Shop, 484 075 chez Comptoir Ivoire, Marché Lagune
  incomplet (Spark 20 exclu). En achetant chaque article au meilleur prix : **477 575 FCFA**, soit
  6 500 FCFA de moins que le meilleur panier à enseigne unique.
- **Black Friday 2025** : Baobab Shop −11,7 %, Marché Lagune −11,3 %, **Comptoir Ivoire +3,8 %**.
  La meilleure semaine de Comptoir Ivoire est celle du 14/09/2026 (−5,2 %).

## Performance et structures de données

| Étage | Durée approximative |
|---|---|
| Chargement des 3 sources | 130 ms (dont l'import de pandas) |
| Rapprochement (76 désignations × 30 motifs) | 5 ms |
| Lecture des 20 876 lignes d'historique | 20 ms |
| Analyses de l'historique (`groupby`) | 25 ms |
| Benchmark liste contre dictionnaire | 150 ms |
| **Pipeline complet** | **≈ 0,4 s** |

| Besoin | Structure | Coût |
|---|---|---|
| Retrouver les offres d'un produit | `dict` produit → {enseigne → offre} | O(1) |
| Recherche ponctuelle dans l'historique | `dict` (source, produit, date) → prix | O(1) contre O(n) en balayant une liste |
| Moyennes sur tout l'historique | DataFrame pandas + `groupby` | O(n), sans boucle Python |
| Rapprochement | regex compilées une seule fois | pas de recompilation par désignation |

Sur ce jeu de données, chercher un prix dans une liste coûte environ 270 µs contre 0,3 µs avec un
dictionnaire (≈ ×900). Le compromis : le dictionnaire consomme plus de mémoire et coûte O(n) à construire,
il ne vaut la peine que si l'on interroge souvent les mêmes données.

## Limites et pistes d'amélioration

- Les dates de mise à jour de Comptoir Ivoire (du 03 au 31 octobre) et les notes clients ne sont pas utilisées.
- Le rapprochement repose sur des motifs écrits à la main pour 30 produits : un nouveau catalogue
  demanderait de nouvelles règles.
- Acheter dans plusieurs enseignes (panier malin) a un coût logistique que le calcul ignore :
  déplacements, livraisons séparées, délais.
- Le meilleur panier à enseigne unique est fragile : Comptoir Ivoire devance Baobab Shop de 7 425 FCFA,
  moins que les 8 500 FCFA de livraison de Baobab, et le retrait à Adjamé a un coût de transport non
  compté. La page *Panier* signale ce cas. Les frais de livraison sont comptés par article.
- Le prix de Comptoir Ivoire dans l'historique est le prix catalogue, sans la remise : la comparaison
  Black Friday le défavorise légèrement par rapport au prix réellement payé.
- Pistes : tests automatisés du modèle (`pytest`), gestion de plusieurs mois de fichiers, alerte quand un
  prix passe sous sa moyenne annuelle.

## Dépannage

| Symptôme | Cause probable |
|---|---|
| `ModuleNotFoundError: modele` | lancer `streamlit run app.py` **depuis la racine du projet** |
| « Fichier introuvable » dans le journal | un fichier manque dans `donnees/` |
| Accents mal affichés dans Excel | ouvrir le CSV en UTF-8 (il contient un BOM, Excel doit le reconnaître) |
| Résultats qui ne changent pas après modification des données | relancer l'application (le pipeline est en cache) |

---

*Exercice pédagogique — données fictives. Python · pandas · Streamlit.*