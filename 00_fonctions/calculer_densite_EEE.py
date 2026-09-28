# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Fonction "calculer_densite_EEE"
Date : 2026-07-07
Objectif : construire un AXE DESCRIPTIF de densité des points EEE par tronçon
═══════════════════════════════════════════════════════════════════════════

────────────────────────── PRINCIPE GÉNÉRAL ──────────────────────────
Cet indicateur ne modifie AUCUN score MS / N / P. Il ajoute un axe
d'information *descriptif et comparatif* : il dit "combien / quelle ampleur"
d'EEE il y a sur chaque tronçon, SANS jamais juger si c'est "bien" ou "mal",
ni s'il faut prioriser. C'est le gestionnaire qui décide du sens à donner.

Toute la logique repose sur UNE SEULE formule, commune aux deux voies :

        densite_EEE_valeur(tronçon) =  Σ  poids(point)
                                       sur les points EEE du tronçon

Seul le POIDS de chaque point change selon la source des données :

  • Voie A  (source = CamAlien uniquement, source_points='camalien')
        poids = niveau_taille (1 à 4), déduit de largeur × longueur.
        -> on tient compte de l'AMPLEUR (emprise) de chaque tache.

  • Voie B  (sources autres / multiples, source_points='autre')
        poids = 1.
        -> la somme vaut alors le simple NOMBRE de points : un comptage
           robuste, valable quelle que soit l'origine des données.

Les deux voies partagent EXACTEMENT le même traitement ensuite (agrégation
par tronçon, normalisation optionnelle par km, classement, étiquette). C'est
volontaire : on veut que les deux voies soient le plus similaires possible ;
la seule différence tient dans le poids (un "1" ou un "niveau_taille").

────────────────── POURQUOI largeur × longueur (voie A) ──────────────────
La couche CamAlien fournit, par point, une largeur et une longueur de tache
en classes. On les traduit en rangs (1..3) et on additionne les deux rangs :
la somme (2..6) est repliée en 4 niveaux de taille. C'est une mesure ORDINALE
(pas des m² littéraux) car les classes "Sup3m" / "Sup20m" sont ouvertes : on
ne peut pas calculer une surface exacte, seulement un ordre de grandeur.

On a délibérément écarté le champ "densite" (Isolés/Taches/Continue) : il est
plus souvent vide (~18 %) que largeur/longueur, et il décrit la concentration
DANS la tache, alors que largeur×longueur décrit la TAILLE de la tache (=
surface à traiter), plus parlant pour un gestionnaire.

──────────────────────── PARAMÈTRES ────────────────────────
  - gdf_EEE       : GeoDataFrame des points EEE, DÉJÀ joints aux tronçons
                    (colonne 'nom_plo_fi' remplie par join_num_troncon_a_gdf_EEE ;
                    un point de bordure peut porter "A, B" = deux tronçons).
                    Doit aussi contenir 'largeur' et 'longueur' (voie A).
  - df_scoring    : DataFrame de scoring, une ligne par tronçon (clé nom_plo_fi).
  - gdf_troncons  : GeoDataFrame des tronçons dédupliqués (gdf_troncons_copy),
                    contenant 'dist_deb'/'dist_fin' si la couche est du SI ROUTE.
  - source_points : 'camalien' (voie A, taille) ou 'autre' (voie B, comptage).
  - source_pr     : 'si_route' (longueur = dist_fin - dist_deb -> pts/km)
                    ou 'autre' (longueur non disponible -> valeur brute ; TODO).
  - colonne_id    : nom de la colonne identifiant les tronçons (déf. 'nom_plo_fi').
  - methode_seuil : découpage de l'étiquette compagnon ('quartiles' par défaut).
  - liste_avertissements : liste (ex. _WARNINGS_SPRINGE) où pousser les
                    avertissements de transparence ; si None, on affiche seulement.

──────────────────────── SORTIES (ajoutées à df_scoring) ────────────────────────
  - nb_points_EEE          : nombre de points EEE rattachés au tronçon.
  - densite_EEE_valeur     : Σ des poids (brut, non normalisé).
  - longueur_troncon       : longueur du tronçon en mètres (NaN si non SI ROUTE).
  - densite_EEE_par_km     : densite_EEE_valeur / (longueur/1000) (si SI ROUTE).
  - densite_EEE_categorie  : étiquette compagnon dont le nom EST son intervalle
                             chiffré (ex. "3.0–8.0"), jamais un adjectif de valeur.
  - rang_indicatif_densite : rang (pandas.rank method='min', ascending=False),
                             même convention que les 4 rangs existants. Le rang
                             est une POSITION relative (un fait), pas un jugement.

Le tout est cumulé toutes espèces confondues (par espèce = TODO).
"""

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────────────────────────────────
# Tables de correspondance (constantes du module, faciles à ajuster ici).
# ─────────────────────────────────────────────────────────────────────────
# Rang de la classe de largeur (petit -> grand).
RANG_LARGEUR = {'Inf1m': 1, '1a3m': 2, 'Sup3m': 3}
# Rang de la classe de longueur (petit -> grand).
RANG_LONGUEUR = {'Inf5m': 1, '5a20m': 2, 'Sup20m': 3}
# Repli des sommes de rangs (2..6) en 4 niveaux de taille (1..4).
# 2 -> 1 (≤5) | 3 -> 2 (5–20) | 4 -> 3 (20–60) | 5 et 6 -> 4 (>60)
SOMME_VERS_NIVEAU = {2: 1, 3: 2, 4: 3, 5: 4, 6: 4}
# Valeur "plancher" utilisée quand une dimension est manquante : on retient le
# MINIMUM RÉEL (Inf1m / Inf5m -> rang 1). Choix assumé : ne jamais inventer une
# dimension plus grande que ce qu'on sait ; le minimum est forcément réel.
RANG_PLANCHER = 1


def _pousser_avertissement(liste, message):
    """Affiche un avertissement et l'ajoute à la liste fournie (si elle existe)."""
    print(f"⚠️  {message}")
    if liste is not None:                 # liste = None -> on se contente d'afficher
        liste.append(message)


def _calculer_niveau_taille(df, liste_avertissements):
    """
    Voie A : calcule, pour chaque point, un 'niveau_taille' (1 à 4) à partir
    des colonnes 'largeur' et 'longueur'.

    Règle des trous : toute valeur absente ou non reconnue est ramenée au
    PLANCHER réel (rang 1 = Inf1m pour la largeur, Inf5m pour la longueur).
    On compte ces "planchers appliqués" et on les signale (transparence).
    """
    # --- Largeur : on mappe la classe vers son rang ; inconnu/vide -> plancher.
    #     .map() renvoie NaN pour les valeurs hors dictionnaire ; on repère ces
    #     NaN pour (a) les compter et (b) les remplacer par le plancher.
    rang_largeur = df['largeur'].map(RANG_LARGEUR)
    nb_largeur_plancher = int(rang_largeur.isna().sum())
    rang_largeur = rang_largeur.fillna(RANG_PLANCHER).astype(int)

    # --- Longueur : même principe.
    rang_longueur = df['longueur'].map(RANG_LONGUEUR)
    nb_longueur_plancher = int(rang_longueur.isna().sum())
    rang_longueur = rang_longueur.fillna(RANG_PLANCHER).astype(int)

    # --- Signalement de transparence sur les planchers appliqués.
    if nb_largeur_plancher > 0:
        _pousser_avertissement(
            liste_avertissements,
            f"Densité EEE (voie A) : {nb_largeur_plancher} point(s) sans largeur "
            f"ramené(s) au minimum réel 'Inf1m'."
        )
    if nb_longueur_plancher > 0:
        _pousser_avertissement(
            liste_avertissements,
            f"Densité EEE (voie A) : {nb_longueur_plancher} point(s) sans longueur "
            f"ramené(s) au minimum réel 'Inf5m'."
        )

    # --- Somme des rangs (2..6) puis repli en niveau de taille (1..4).
    somme = rang_largeur + rang_longueur
    niveau = somme.map(SOMME_VERS_NIVEAU).astype(int)
    return niveau


def _detecter_doublons(gdf_EEE, liste_avertissements, precision_m=1):
    """
    Détection NON DESTRUCTIVE de doublons potentiels : deux points à la même
    position (coordonnées arrondies au mètre) ET de la même espèce ('plante')
    sont probablement un doublon (ex. couche perso ré-importée via l'INPN).

    On ne supprime RIEN (deux vraies observations proches existent aussi) : on
    se contente d'un avertissement chiffré. Faiblesse connue et assumée.
    """
    # Récupération des coordonnées : on privilégie la géométrie, avec repli sur
    # d'éventuelles colonnes 'x'/'y' si la géométrie est absente.
    if 'geometry' in gdf_EEE.columns and gdf_EEE.geometry.notna().any():
        xs = gdf_EEE.geometry.x.round(precision_m)
        ys = gdf_EEE.geometry.y.round(precision_m)
    elif {'x', 'y'}.issubset(gdf_EEE.columns):
        xs = gdf_EEE['x'].round(precision_m)
        ys = gdf_EEE['y'].round(precision_m)
    else:
        return   # pas de coordonnées exploitables -> on ne peut pas détecter

    plante = gdf_EEE['plante'] if 'plante' in gdf_EEE.columns else ''
    # Clé de doublon = (x arrondi, y arrondi, espèce).
    cle = pd.DataFrame({'x': xs, 'y': ys, 'plante': plante})
    # duplicated(keep=False) marque TOUTES les lignes appartenant à un groupe
    # de doublons (pas seulement les répétitions), pour un comptage honnête.
    masque = cle.duplicated(keep=False)
    nb_en_doublon = int(masque.sum())
    if nb_en_doublon > 0:
        nb_groupes = cle[masque].drop_duplicates().shape[0]
        _pousser_avertissement(
            liste_avertissements,
            f"Densité EEE : {nb_en_doublon} point(s) partagent une position "
            f"(±{precision_m} m) et une espèce identiques ({nb_groupes} groupe(s)) "
            f"— doublons possibles entre sources. Aucun point supprimé."
        )


def _construire_categorie(valeurs, methode_seuil='quartiles'):
    """
    Construit l'étiquette compagnon 'densite_EEE_categorie'.
    Règle imposée : AUCUN mot de valeur ('faible', 'fort'...). Le nom de la
    classe EST son intervalle chiffré (ex. "3.0–8.0").

    - Les tronçons à valeur 0 (aucun point EEE) forment leur propre classe "0".
    - Les tronçons colonisés (valeur > 0) sont découpés par quartiles calculés
      SUR LE RUN COURANT (donc dépendants du périmètre de travail : deux runs
      sur des zones différentes ne sont pas comparables au seuil près).
    - Les valeurs non calculables (NaN, ex. longueur manquante en pts/km)
      reçoivent "non calculé".
    """
    categorie = pd.Series(index=valeurs.index, dtype='object')

    # a) Non calculé (NaN).
    masque_nan = valeurs.isna()
    categorie[masque_nan] = "non calculé"

    # b) Aucun point EEE (valeur exactement 0).
    masque_zero = (~masque_nan) & (valeurs == 0)
    categorie[masque_zero] = "0"

    # c) Tronçons colonisés : découpage en 4 classes par quartiles.
    masque_positif = (~masque_nan) & (valeurs > 0)
    valeurs_positives = valeurs[masque_positif]

    if valeurs_positives.empty:
        return categorie   # rien à découper

    if methode_seuil == 'quartiles':
        # qcut découpe en 4 groupes d'effectifs ~égaux. duplicates='drop' évite
        # un plantage si des bornes de quartiles se répètent (valeurs peu variées).
        try:
            classes = pd.qcut(valeurs_positives, q=4, duplicates='drop')
            # On remplace l'intervalle pandas "(a, b]" par un libellé "a–b" chiffré.
            libelles = classes.apply(
                lambda interval: f"{interval.left:.1f}–{interval.right:.1f}"
            )
            categorie[masque_positif] = libelles
        except Exception:
            # Repli ultra-robuste : si le découpage échoue (trop peu de valeurs
            # distinctes), on met la valeur brute arrondie comme étiquette.
            categorie[masque_positif] = valeurs_positives.round(1).astype(str)
    else:
        # Emplacement prévu pour un futur découpage à bornes fixes (ex. 5/20/60).
        # TODO : implémenter methode_seuil='fixes'.
        categorie[masque_positif] = valeurs_positives.round(1).astype(str)

    return categorie


def calculer_densite_EEE(gdf_EEE,
                         df_scoring,
                         gdf_troncons,
                         source_points='camalien',
                         source_pr='si_route',
                         colonne_id='nom_plo_fi',
                         methode_seuil='quartiles',
                         liste_avertissements=None):

    print(f"\n{'='*74}")
    print("CALCUL DENSITÉ EEE — axe descriptif (ne modifie aucun score MS/N/P)")
    print(f"{'='*74}\n")
    print(f"  Voie points   : {source_points}  "
          f"({'taille largeur×longueur' if source_points == 'camalien' else 'comptage'})")
    print(f"  Voie longueur : {source_pr}\n")

    # ── 0. Vérifications minimales ──────────────────────────────────────────
    if colonne_id not in gdf_EEE.columns:
        raise ValueError(f"❌ '{colonne_id}' introuvable dans gdf_EEE "
                         f"(la jointure points↔tronçons a-t-elle été faite ?).")
    if colonne_id not in df_scoring.columns:
        raise ValueError(f"❌ '{colonne_id}' introuvable dans df_scoring.")

    # ── 1. Détection (non destructive) des doublons potentiels ──────────────
    #    UNIQUEMENT en voie B (sources multiples) : c'est le seul cas où un
    #    doublon "entre sources" est possible (ex. couche perso ré-importée via
    #    l'INPN). En voie A (CamAlien seul = source unique), des points co-
    #    localisés de même espèce sont NORMAUX (plusieurs taches décrites au
    #    même point) et ne doivent pas être signalés comme doublons.
    #    Détection faite sur les points d'ORIGINE, avant éclatement de bordure.
    if source_points == 'autre':
        _detecter_doublons(gdf_EEE, liste_avertissements)

    # ── 2. Passage en DataFrame simple pour la suite ────────────────────────
    #    On n'a plus besoin de la géométrie ici ; travailler sur un DataFrame
    #    évite l'ambiguïté de GeoDataFrame.explode() (qui vise la géométrie).
    colonnes_utiles = [colonne_id]
    for c in ('largeur', 'longueur', 'plante'):
        if c in gdf_EEE.columns:
            colonnes_utiles.append(c)
    df = pd.DataFrame(gdf_EEE[colonnes_utiles]).copy()

    # ── 3. Retirer les points hors tronçon ('NA') ──────────────────────────
    nb_hors_troncon = int((df[colonne_id] == 'NA').sum())
    df = df[df[colonne_id] != 'NA'].copy()
    if nb_hors_troncon > 0:
        _pousser_avertissement(
            liste_avertissements,
            f"Densité EEE : {nb_hors_troncon} point(s) hors de tout tronçon (ignorés)."
        )

    # ── 4. Éclatement des points de bordure (option 1 validée) ─────────────
    #    Un point à cheval porte "A, B". On le duplique : une ligne par tronçon
    #    intersecté, car la tache existe réellement sur les deux. On compte le
    #    nombre de lignes gagnées pour information.
    nb_avant = len(df)
    df[colonne_id] = df[colonne_id].astype(str).str.split(',')     # "A, B" -> ["A", " B"]
    df = df.explode(colonne_id)                                    # une ligne par tronçon
    df[colonne_id] = df[colonne_id].str.strip()                    # nettoyage des espaces
    nb_bordure = len(df) - nb_avant
    if nb_bordure > 0:
        _pousser_avertissement(
            liste_avertissements,
            f"Densité EEE : {nb_bordure} rattachement(s) supplémentaire(s) issus de "
            f"points de bordure attribués à chacun de leurs tronçons."
        )
    # TODO (harmonisation) : les indicateurs MS/N/P actuels ne font PAS cet
    # éclatement (les points de bordure y tombent à la trappe au merge). À
    # harmoniser quand le reste sera stabilisé, pour un traitement identique.

    # ── 5. Poids de chaque point selon la voie ─────────────────────────────
    if source_points == 'camalien':
        # Voie A : poids = niveau_taille (1..4) issu de largeur × longueur.
        if not {'largeur', 'longueur'}.issubset(df.columns):
            raise ValueError("❌ Voie A demandée mais 'largeur'/'longueur' absentes "
                             "de gdf_EEE.")
        df['poids'] = _calculer_niveau_taille(df, liste_avertissements)
    else:
        # Voie B : poids = 1 -> la somme redonne le simple nombre de points.
        df['poids'] = 1

    # ── 6. Agrégation par tronçon : nombre de points et somme des poids ────
    agg = (
        df.groupby(colonne_id)
          .agg(nb_points_EEE=('poids', 'size'),      # size = nb de lignes = nb de points
               densite_EEE_valeur=('poids', 'sum'))  # Σ des poids = la valeur de densité
          .reset_index()
    )

    # ── 7. Fusion dans df_scoring (tous les tronçons) ──────────────────────
    #    Left merge : les tronçons SANS EEE ne sont pas dans 'agg' -> ils
    #    reçoivent NaN, qu'on remplace par 0 (aucun point, densité nulle).
    df_scoring = df_scoring.merge(agg, on=colonne_id, how='left')
    df_scoring['nb_points_EEE'] = df_scoring['nb_points_EEE'].fillna(0).astype(int)
    df_scoring['densite_EEE_valeur'] = df_scoring['densite_EEE_valeur'].fillna(0)

    # Information : des points rattachés à des tronçons absents de df_scoring
    # (ex. bordure vers un tronçon hors zone de travail) ont été ignorés au merge.
    troncons_agg = set(agg[colonne_id])
    troncons_scoring = set(df_scoring[colonne_id])
    nb_hors_zone = len(troncons_agg - troncons_scoring)
    if nb_hors_zone > 0:
        _pousser_avertissement(
            liste_avertissements,
            f"Densité EEE : {nb_hors_zone} tronçon(s) rattaché(s) à des points mais "
            f"absent(s) de la zone de travail (ignorés au calcul)."
        )

    # ── 8. Longueur des tronçons + normalisation par km (voie longueur) ────
    if source_pr == 'si_route' and {'dist_deb', 'dist_fin'}.issubset(gdf_troncons.columns):
        # Abscisses curvilignes SI ROUTE en MÈTRES : longueur = fin - début.
        # On agrège par tronçon de façon robuste (min début, max fin) au cas où
        # plusieurs fragments partagent le même identifiant.
        lg = (
            gdf_troncons.groupby(colonne_id)
                        .agg(_deb=('dist_deb', 'min'), _fin=('dist_fin', 'max'))
                        .reset_index()
        )
        lg['longueur_troncon'] = lg['_fin'] - lg['_deb']
        df_scoring = df_scoring.merge(lg[[colonne_id, 'longueur_troncon']],
                                      on=colonne_id, how='left')

        # Densité par km = valeur / (longueur en km). Garde-fou : longueur nulle
        # ou manquante -> pas de division (résultat NaN, signalé plus bas).
        longueur_km = df_scoring['longueur_troncon'] / 1000.0
        df_scoring['densite_EEE_par_km'] = np.where(
            (longueur_km.notna()) & (longueur_km > 0),
            df_scoring['densite_EEE_valeur'] / longueur_km,
            np.nan
        )
        # La valeur qui servira au CLASSEMENT est la densité par km.
        colonne_classement = 'densite_EEE_par_km'

        nb_sans_longueur = int(((df_scoring['longueur_troncon'].isna()) |
                                (df_scoring['longueur_troncon'] <= 0)).sum())
        if nb_sans_longueur > 0:
            _pousser_avertissement(
                liste_avertissements,
                f"Densité EEE : {nb_sans_longueur} tronçon(s) sans longueur valide "
                f"-> densité/km non calculée (rang vide pour ces tronçons)."
            )
    else:
        # Voie longueur 2 : couche non-SI ROUTE -> longueur indisponible (TODO).
        # On classe alors sur la valeur BRUTE (non normalisée), en le disant.
        df_scoring['longueur_troncon'] = np.nan
        df_scoring['densite_EEE_par_km'] = np.nan
        colonne_classement = 'densite_EEE_valeur'
        _pousser_avertissement(
            liste_avertissements,
            "Densité EEE : couche tronçons non déclarée SI ROUTE -> classement sur "
            "la valeur brute (non normalisée par km). TODO : obtenir la longueur "
            "autrement (voie longueur 2)."
        )

    # ── 9. Classement indicatif (même convention que les 4 rangs existants) ─
    #    method='min' : les ex æquo partagent le meilleur rang.
    #    ascending=False : plus la valeur est grande, meilleur (plus petit) le rang.
    #    Rappel : un rang est une POSITION relative (un fait), pas un jugement de
    #    priorité — l'interprétation reste au gestionnaire.
    df_scoring['rang_indicatif_densite'] = df_scoring[colonne_classement].rank(
        method='min', ascending=False
    )

    # ── 10. Étiquette compagnon (bornes chiffrées, jamais d'adjectif) ──────
    df_scoring['densite_EEE_categorie'] = _construire_categorie(
        df_scoring[colonne_classement], methode_seuil=methode_seuil
    )

    # ── 11. Statistiques de contrôle ───────────────────────────────────────
    nb_troncons = len(df_scoring)
    nb_colonises = int((df_scoring['densite_EEE_valeur'] > 0).sum())
    print("\nRésultats densité EEE :")
    print(f"  Tronçons total        : {nb_troncons}")
    print(f"  Tronçons colonisés    : {nb_colonises} "
          f"({100*nb_colonises/nb_troncons:.1f} %)")
    print(f"  Colonne de classement : {colonne_classement}")
    # Distribution de la valeur de classement sur les tronçons colonisés :
    # aide le gestionnaire à situer les valeurs lui-même (aucun seuil imposé).
    distrib = df_scoring.loc[df_scoring['densite_EEE_valeur'] > 0, colonne_classement]
    if not distrib.empty:
        print("  Distribution (tronçons colonisés) :")
        print(f"    min={distrib.min():.2f}  Q1={distrib.quantile(.25):.2f}  "
              f"méd={distrib.median():.2f}  Q3={distrib.quantile(.75):.2f}  "
              f"max={distrib.max():.2f}")
    print(f"\n{'='*74}\n")

    return df_scoring
