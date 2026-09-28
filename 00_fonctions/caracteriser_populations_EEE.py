# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
Fonction "caracteriser_populations_EEE"
Date : 2026-09-08
Objectif : décrire, par tronçon et par catégorie d'EEE, les POPULATIONS
           recensées — leur nombre, leur ampleur, leur compacité et leur
           répartition le long de l'axe routier.

Remplace calculer_densite_EEE.py. Voir le document de cadrage
"SPRINGE — Caractérisation des populations d'EEE par tronçon" v0.3.
═══════════════════════════════════════════════════════════════════════════

────────────────────── CE QUE CE MODULE MESURE ──────────────────────
Il ne mesure NI une densité NI une abondance. Le mot "densité" a été banni
de ce module (choix structurant § 2.4 du cadrage) parce qu'il induit en
erreur : un gestionnaire lisant "densité" comprend "quantité de plantes",
ce que la donnée ne dit pas.

Ce qui est réellement mesuré, en quatre familles :
  1. la FRÉQUENCE des populations -> combien de foyers distincts ;
  2. leur AMPLEUR                  -> combien de foyers par classe de
                                      largeur et de longueur ;
  3. leur COMPACITÉ                -> isolés / taches / continus ;
  4. leur RÉPARTITION le long de l'axe routier.

────────────────── L'HYPOTHÈSE QUI CONDITIONNE TOUT ──────────────────
Les données sont supposées collectées selon :

    Albert, A. (coord.) 2017. Protocole d'acquisition de données sur les
    plantes exotiques envahissantes le long du réseau routier national.
    Fédération des Conservatoires botaniques nationaux, Montreuil. 24 p.

Ce protocole (§ II) définit l'unité d'observation par une règle de distance :
deux individus ou deux taches d'une même espèce distants de moins de 50 m
forment UNE SEULE population ; au-delà de 50 m, deux populations distinctes.

    => UN POINT = UNE POPULATION, PAS UNE PLANTE.

Conséquence contre-intuitive à garder en tête : une forte concentration de
végétation ne produit PAS un amas de points, mais UN SEUL point portant des
attributs de taille et de compacité élevés. Compter les points d'un tronçon
revient donc à compter des FOYERS DISTINCTS, pas de la biomasse.

Si la source n'est pas conforme à ce protocole, ce module ne doit pas être
appelé du tout (choix structurant CS-3 : un comptage de points dont on ignore
l'unité d'observation n'a pas de référent, donc pas de sens). La vérification
est faite en amont par fenetre_mapping_colonnes_EEE.py.

──────────────────────── PARAMÈTRES ────────────────────────
  - gdf_EEE          : GeoDataFrame des points EEE, DÉJÀ mappés (colonne
                       'species_name_sci' issue de fenetre_mapping_especes)
                       et DÉJÀ joints aux tronçons (colonne colonne_id
                       remplie par join_num_troncon_a_gdf_EEE ; un point de
                       bordure peut porter "A, B" = deux tronçons).
  - df_scoring       : DataFrame de scoring, une ligne par tronçon.
  - gdf_troncons     : GeoDataFrame des tronçons dédupliqués
                       (gdf_troncons_copy), avec 'dist_deb'/'dist_fin' si la
                       couche vient du SI ROUTE.
  - mapping_colonnes : dict produit par fenetre_mapping_colonnes_EEE, qui
                       associe chaque information attendue au nom réel de la
                       colonne dans la couche du gestionnaire. Clés :
                       'largeur', 'longueur', 'compacite' (requises),
                       'abscisse', 'localisation', 'evaluation', 'date'
                       (facultatives, valeur None si absentes).
  - categories_retenues : liste des species_name_sci à décrire. Par défaut,
                       les 5 catégories SPRINGE.
  - colonne_id       : nom de la colonne identifiant les tronçons.
  - source_pr        : 'si_route' (longueur de tronçon = dist_fin - dist_deb)
                       ou 'autre' (longueur indisponible).
  - liste_avertissements : liste (ex. _WARNINGS_SPRINGE) où pousser les
                       avertissements ; si None, on se contente d'afficher.

──────────────────────── SORTIES ────────────────────────
Un tuple de trois objets :

  1. df_scoring  : le DataFrame d'entrée enrichi des champs de SYNTHÈSE
                   (toutes catégories confondues), qui partiront dans la
                   couche cartographique via preparer_couche_gpkg.
  2. df_caracterisation : la table LONGUE, une ligne par
                   (tronçon × catégorie d'EEE). C'est le détail complet,
                   écrit ensuite dans le GeoPackage comme table attributaire
                   sans géométrie.
  3. diagnostic  : dict de chiffres de qualité, consommé par
                   generer_notice_lecture pour produire l'aide à la lecture.

Le module ne modifie AUCUN score MS / N / P et ne produit AUCUN rang,
AUCUN score, AUCUN adjectif de valeur (choix structurant CS-1).
"""

import unicodedata

import numpy as np
import pandas as pd


# ═════════════════════════════════════════════════════════════════════════
# CONSTANTES DU MODULE
# Regroupées ici pour être ajustables en un seul endroit.
# ═════════════════════════════════════════════════════════════════════════

# --- Modalités canoniques du protocole (tableau 4) -----------------------
# Ce sont les seules valeurs reconnues. Toute autre valeur est comptée en
# "non renseigné" (jamais devinée, jamais imputée : choix structurant CS-10).
MODALITES_LARGEUR = ['Inf1m', '1a3m', 'Sup3m']
MODALITES_LONGUEUR = ['Inf5m', '5a20m', 'Sup20m']
MODALITES_COMPACITE = ['Isoles', 'Taches', 'Continue']

# Libellé unique des valeurs absentes ou non reconnues. On utilise une chaîne
# plutôt que NaN pour pouvoir la compter comme une modalité à part entière.
NON_RENSEIGNE = 'nr'

# --- Bornes BASSES des classes de longueur, en mètres ---------------------
# Utilisées pour le linéaire colonisé MINIMUM (choix structurant CS-7).
#
# Pourquoi seulement les bornes basses : les classes extrêmes du protocole
# sont OUVERTES ('Sup3m', 'Sup20m'), donc aucune borne haute n'existe sans
# l'inventer. Et 'Inf5m' couvre [0 ; 5[, dont la borne basse est 0 : une
# population de cette classe contribue donc 0 mètre GARANTI.
#
# Le résultat est un MINORANT, jamais une estimation. C'est volontairement
# conservateur : sur le jeu national de référence, 44,9 % des couples
# (tronçon × catégorie) obtiennent 0. Le mot "minimum" dans le nom du champ
# porte cette sémantique, et la notice de lecture chiffre l'écart.
BORNE_BASSE_LONGUEUR_M = {'Inf5m': 0, '5a20m': 5, 'Sup20m': 20}

# --- Les 5 catégories d'EEE de SPRINGE ------------------------------------
# Clés = species_name_sci (produit par fenetre_mapping_especes, et clé de
#        jointure avec EEE_SHEET dans tout le pipeline).
# Valeurs = libellé court, utilisé uniquement pour le champ de synthèse
#           textuelle destiné à être lu par un humain dans QGIS.
CATEGORIES_SPRINGE = {
    'Reynoutria sp': 'Renouées',
    'Ailanthus altissima': 'Ailante',
    'Ambrosia artemisiifolia': 'Ambroisie',
    'Heracleum mantegazzianum': 'Berce du Caucase',
    'EEE autre': 'EEE autre',
}

# --- Libellés lisibles des modalités, pour le champ de synthèse ----------
# On privilégie la clarté sur la concision (décision du 2026-09-08) : une
# phrase développée se comprend plus vite qu'une notation abrégée qu'il faut
# décoder. Le champ de synthèse est fait pour être lu, pas pour être compact.
# Format compacité : (forme au singulier, forme au pluriel).
LIBELLE_COMPACITE = {
    'Isoles': ('en individus isolés', 'en individus isolés'),
    'Taches': ('en taches discontinues', 'en taches discontinues'),
    'Continue': ('continue', 'continues'),
    NON_RENSEIGNE: ('de compacité non renseignée', 'de compacité non renseignée'),
}
# Ces libellés ne commencent JAMAIS par « de » : le code qui les utilise
# préfixe déjà l'effectif d'un « de » (« 3 de 5 à 20 m »). Un libellé
# « de 5 à 20 m » produirait « 3 de de 5 à 20 m ».
LIBELLE_LONGUEUR = {
    'Inf5m': 'moins de 5 m',
    '5a20m': '5 à 20 m',
    'Sup20m': 'plus de 20 m',
    NON_RENSEIGNE: 'longueur non renseignée',
}
LIBELLE_LARGEUR = {
    'Inf1m': 'moins de 1 m',
    '1a3m': '1 à 3 m',
    'Sup3m': 'plus de 3 m',
    NON_RENSEIGNE: 'largeur non renseignée',
}


# ═════════════════════════════════════════════════════════════════════════
# OUTILS INTERNES
# Préfixés d'un "_" : usage interne au module, non destinés à être appelés
# depuis le script principal.
# ═════════════════════════════════════════════════════════════════════════

def _pousser_avertissement(liste, message):
    """
    Affiche un avertissement à l'écran et l'ajoute à la liste fournie.

    La liste est typiquement _WARNINGS_SPRINGE, collectée tout au long du run
    et restituée à la fin dans le rapport d'exécution. Si liste vaut None
    (appel isolé, test), on se contente de l'affichage.
    """
    print(f"⚠️  {message}")
    if liste is not None:
        liste.append(message)


def _normaliser_texte(valeur):
    """
    Ramène une valeur brute à une forme comparable : chaîne, sans espaces de
    bord, sans accents, en minuscules.

    Pourquoi cette normalisation : le protocole normalise les MODALITÉS, mais
    chaque export peut varier sur la casse ou les accents ('Isolés', 'isoles',
    'ISOLES' désignent la même chose). On compare donc sur une forme canonique
    plutôt que sur la chaîne littérale, pour ne pas jeter en "non renseigné"
    des valeurs parfaitement valides.

    Détail technique : unicodedata.normalize('NFD', ...) décompose les
    caractères accentués en (lettre de base + accent combinant) ; on retire
    ensuite tous les caractères de catégorie 'Mn' (Mark, nonspacing = les
    accents), ce qui transforme 'é' en 'e'.
    """
    if valeur is None:
        return ''
    texte = str(valeur).strip()
    decompose = unicodedata.normalize('NFD', texte)
    sans_accent = ''.join(c for c in decompose if unicodedata.category(c) != 'Mn')
    return sans_accent.lower()


def _mapper_modalites(serie, modalites_attendues):
    """
    Ramène une colonne brute aux modalités canoniques du protocole.

    Paramètres
    ----------
    serie : pandas.Series des valeurs brutes de la couche du gestionnaire.
    modalites_attendues : liste des modalités canoniques (ex. MODALITES_LARGEUR).

    Retour
    ------
    (serie_mappee, nb_non_reconnues, valeurs_non_reconnues)
      - serie_mappee : Series ne contenant QUE des modalités canoniques ou
        NON_RENSEIGNE ;
      - nb_non_reconnues : combien de lignes sont tombées en NON_RENSEIGNE ;
      - valeurs_non_reconnues : les valeurs brutes non vides concernées.

    Aucune imputation : une valeur absente ou inconnue devient NON_RENSEIGNE
    et sera COMPTÉE comme telle (choix structurant CS-10). L'ancienne logique
    ramenait ces cas au plancher de la classe ('Inf1m', 'Inf5m'), ce qui
    déplaçait silencieusement toute la distribution vers le bas.
    """
    # Table de correspondance {forme normalisée -> modalité canonique},
    # construite à partir des modalités attendues elles-mêmes : si on ajoute
    # une modalité à la constante en tête de module, elle est automatiquement
    # reconnue ici, sans autre modification.
    correspondance = {_normaliser_texte(m): m for m in modalites_attendues}

    normalisee = serie.map(_normaliser_texte)
    mappee = normalisee.map(correspondance)

    # .isna() repère les valeurs qui n'ont trouvé aucune correspondance.
    masque_inconnu = mappee.isna()
    nb_non_reconnues = int(masque_inconnu.sum())

    # On mémorise les valeurs brutes non reconnues, en excluant les chaînes
    # vides : un trou de saisie est normal, alors qu'une valeur non vide et
    # non reconnue signale probablement la mauvaise colonne ou un autre
    # référentiel. Les deux cas méritent des messages différents.
    valeurs_non_reconnues = sorted(
        set(serie[masque_inconnu & (normalisee != '')].astype(str))
    )

    mappee = mappee.fillna(NON_RENSEIGNE)
    return mappee, nb_non_reconnues, valeurs_non_reconnues


def _compter_par_modalite(groupe, colonne, modalites):
    """
    Compte, dans un groupe de populations, combien relèvent de chaque modalité.

    Retourne un dict {modalité: effectif} incluant systématiquement toutes les
    modalités attendues plus NON_RENSEIGNE — y compris celles à zéro.

    Pourquoi inclure les zéros : la table de sortie doit avoir exactement les
    mêmes colonnes pour toutes ses lignes. Une modalité absente d'un tronçon
    doit valoir 0, pas manquer.
    """
    comptes = groupe[colonne].value_counts()
    return {m: int(comptes.get(m, 0)) for m in list(modalites) + [NON_RENSEIGNE]}


def _calculer_repartition(abscisses, longueur_troncon_m):
    """
    Décrit la répartition des populations le long de l'axe routier, à partir
    de leurs abscisses curvilignes (en mètres).

    Ce sont des MESURES BRUTES, pas des inférences (choix structurants CS-8 et
    CS-9). Aucun indice de dispersion n'est calculé et le semis n'est jamais
    qualifié d'"agrégé" ou d'"aléatoire" : sur le jeu national de référence,
    56 % des couples (tronçon × catégorie) ne comptent qu'UNE population,
    effectif sur lequel tout indice statistique produirait un nombre ayant
    l'apparence d'un résultat sans en être un.

    Retour : dict des quatre descripteurs + un statut explicite.

    Pourquoi ce statut : dans un GeoPackage, une colonne numérique ne peut pas
    contenir le texte "non calculable" — elle contient NULL. Or NULL peut
    vouloir dire "aucune donnée" ou "calcul impossible". La colonne texte
    'repartition_calculable' lève l'ambiguïté et dit LAQUELLE des deux.
    """
    resultat = {
        'etendue_occupee_m': np.nan,
        'part_troncon_occupee': np.nan,
        'ecart_min_m': np.nan,
        'ecart_median_m': np.nan,
        'repartition_calculable': 'non (abscisse curviligne indisponible)',
    }

    # Cas 1 : pas d'abscisse du tout (colonne non fournie par le gestionnaire,
    # ou entièrement vide). Les quatre descripteurs sont perdus, mais le reste
    # du calcul se poursuit normalement — champ facultatif (CS-5).
    if abscisses is None:
        return resultat

    # On retire les valeurs manquantes avant de mesurer quoi que ce soit.
    # errors='coerce' transforme en NaN tout ce qui n'est pas numérique, au
    # lieu de lever une exception : une colonne d'abscisses mal typée dégrade
    # le résultat mais ne fait pas planter le run.
    valeurs = pd.to_numeric(pd.Series(abscisses), errors='coerce').dropna().values

    # Cas 2 : une seule population. L'étendue d'un point unique est nulle et
    # les écarts n'existent pas. On ne renvoie surtout PAS 0, qui se lirait
    # comme "toutes les populations au même endroit".
    if len(valeurs) < 2:
        resultat['repartition_calculable'] = 'non (une seule population)'
        return resultat

    # Cas 3 : calcul possible.
    valeurs_triees = np.sort(valeurs)
    etendue = float(valeurs_triees[-1] - valeurs_triees[0])
    # np.diff renvoie les écarts entre éléments consécutifs d'un tableau trié :
    # pour [10, 50, 200] il donne [40, 150].
    ecarts = np.diff(valeurs_triees)

    resultat['etendue_occupee_m'] = round(etendue, 1)
    resultat['ecart_min_m'] = round(float(ecarts.min()), 1)
    resultat['ecart_median_m'] = round(float(np.median(ecarts)), 1)
    resultat['repartition_calculable'] = 'oui'

    # La part du tronçon occupée n'a de sens que si on connaît sa longueur.
    # On borne à 1.0 : une étendue légèrement supérieure à la longueur
    # déclarée peut apparaître quand une population de bordure appartient aux
    # deux tronçons voisins. Ce n'est pas une erreur, mais afficher 1,07
    # serait incompréhensible pour le gestionnaire.
    if longueur_troncon_m and longueur_troncon_m > 0:
        resultat['part_troncon_occupee'] = round(
            min(etendue / longueur_troncon_m, 1.0), 3
        )

    return resultat


def _construire_synthese_troncon(lignes_troncon):
    """
    Construit le texte lisible du champ 'synthese_EEE' de la couche
    cartographique, pour UN tronçon.

    Objectif : qu'un gestionnaire qui clique sur un tronçon dans QGIS voie
    immédiatement ce qu'il porte, sans avoir à joindre la table longue.

    Parti pris assumé : clarté plutôt que concision. Le texte peut paraître
    long, mais il se lit sans décodage — plus rapide au total qu'une notation
    compacte à interpréter.

    Paramètre : DataFrame des lignes de la table longue pour ce tronçon
    (une ligne par catégorie), déjà filtré.
    """
    # Cas du tronçon sans aucune observation. Message explicite qui rappelle la
    # précaution centrale (choix structurant CS-11). Ne JAMAIS écrire
    # "aucune EEE" : rien dans la donnée ne permet de l'affirmer, puisque rien
    # n'établit que le tronçon a été prospecté.
    if (lignes_troncon['nb_populations'].fillna(0) == 0).all():
        return ("Aucune observation enregistrée sur ce tronçon. "
                "Attention : cela ne signifie pas qu'il est indemne d'EEE "
                "— voir la notice de lecture.")

    morceaux = []

    # On ne mentionne que les catégories effectivement présentes : afficher
    # "Berce du Caucase : 0 population" sur chaque tronçon noierait
    # l'information utile.
    for _, ligne in lignes_troncon.iterrows():
        nb = ligne['nb_populations']
        if pd.isna(nb) or nb == 0:
            continue

        nb = int(nb)
        libelle_categorie = CATEGORIES_SPRINGE.get(
            ligne['categorie_EEE'], ligne['categorie_EEE']
        )
        mot_population = "population" if nb == 1 else "populations"

        # --- Détail de compacité, par effectif décroissant de gravité ------
        # Ordre volontaire : continues d'abord, car c'est l'information la
        # plus structurante pour un gestionnaire qui planifie une intervention.
        details_compacite = []
        correspondance_colonnes = {
            'Continue': 'nb_pop_continues',
            'Taches': 'nb_pop_taches',
            'Isoles': 'nb_pop_isolees',
            NON_RENSEIGNE: 'nb_pop_compacite_nr',
        }
        for modalite in ['Continue', 'Taches', 'Isoles', NON_RENSEIGNE]:
            colonne = correspondance_colonnes[modalite]
            valeur = ligne.get(colonne, 0)
            effectif = int(valeur) if not pd.isna(valeur) else 0
            if effectif > 0:
                singulier, pluriel = LIBELLE_COMPACITE[modalite]
                libelle = singulier if effectif == 1 else pluriel
                details_compacite.append((effectif, libelle))

        if nb == 1 and details_compacite:
            # Une seule population : "1 population continue" se lit mieux que
            # "1 population, dont 1 continue".
            phrase = (f"{libelle_categorie} : 1 population "
                      f"{details_compacite[0][1]}")
        elif details_compacite:
            # Énumération française correcte : virgules entre les éléments et
            # « et » avant le dernier. Un simple " et ".join produirait
            # « 4 continues et 1 en taches et 1 isolée et 28 non renseignées »,
            # illisible dès trois modalités.
            elements = [f"{eff} {lib}" for eff, lib in details_compacite]
            if len(elements) == 1:
                detail = elements[0]
            else:
                detail = ", ".join(elements[:-1]) + " et " + elements[-1]
            phrase = (f"{libelle_categorie} : {nb} {mot_population}, "
                      f"dont {detail}")
        else:
            phrase = f"{libelle_categorie} : {nb} {mot_population}"

        # --- Détail des longueurs, de la plus grande à la plus petite ------
        details_longueur = []
        for modalite, colonne in [('Sup20m', 'nb_pop_longueur_Sup20m'),
                                  ('5a20m', 'nb_pop_longueur_5a20m'),
                                  ('Inf5m', 'nb_pop_longueur_Inf5m')]:
            valeur = ligne.get(colonne, 0)
            effectif = int(valeur) if not pd.isna(valeur) else 0
            if effectif > 0:
                details_longueur.append(f"{effectif} de {LIBELLE_LONGUEUR[modalite]}")

        if details_longueur:
            phrase += ". Longueurs : " + ", ".join(details_longueur)

        # --- Année du relevé le plus récent -------------------------------
        annee = ligne.get('annee_releve_max', np.nan)
        if not pd.isna(annee):
            phrase += f". Relevé {int(annee)}"

        morceaux.append(phrase + ".")

    return " ".join(morceaux)


def _controler_regle_50m(df, colonne_id, col_abscisse):
    """
    Contrôle non bloquant de l'application de la règle des 50 m du protocole.

    Principe : sur chaque tronçon et pour chaque catégorie, on trie les
    abscisses curvilignes et on mesure les écarts entre populations
    successives. Le protocole impose qu'ils dépassent tous 50 m — en deçà, les
    deux observations auraient dû être fusionnées en une seule population.

    LIMITE CONNUE ET ASSUMÉE : le regroupement se fait par tronçon, sans
    distinguer le côté de chaussée — SPRINGE ne demande pas cette colonne. Or
    deux populations situées face à face de part et d'autre d'une chaussée ont
    des abscisses curvilignes voisines sans enfreindre le protocole. Le taux
    calculé ici MAJORE donc la non-conformité réelle.

    Ordre de grandeur mesuré sur le jeu national de référence :
      - regroupement par (tronçon × catégorie), méthode d'ici : 26,8 %
      - regroupement par (route × chaussée × côté × catégorie)  : 14,8 %
    C'est la première valeur qui sert de référence aux seuils de la notice,
    pour comparer ce qui est calculé de la même façon.

    Un taux élevé n'invalide pas les résultats : il signifie que le nombre de
    populations est légèrement majoré. Les causes vraisemblables sur le jeu
    national sont l'intégration de données héritées antérieures au protocole
    (il contient des relevés de 1988) et les saisies multiples au même PR sur
    des parties différentes de la dépendance.

    Retour : dict de deux valeurs, ou valeurs None si l'abscisse n'est pas
    disponible — le contrôle est alors impossible, ce qui n'empêche rien.
    """
    if not col_abscisse:
        return {'taux_ecarts_sous_50m': None, 'nb_doublons_position': None}

    ecarts = []
    for _, groupe in df.groupby([colonne_id, 'species_name_sci']):
        valeurs = groupe['_abscisse'].dropna().values
        if len(valeurs) < 2:
            continue
        ecarts.append(np.diff(np.sort(valeurs)))

    if not ecarts:
        return {'taux_ecarts_sous_50m': None, 'nb_doublons_position': None}

    # np.concatenate colle bout à bout les tableaux d'écarts de tous les
    # groupes, pour calculer un taux global.
    tous_ecarts = np.concatenate(ecarts)
    return {
        'taux_ecarts_sous_50m': round(100 * float((tous_ecarts < 50).mean()), 1),
        # Un écart nul = deux populations de même catégorie à la même abscisse.
        # On les signale sans JAMAIS les supprimer (choix structurant CS-15) :
        # deux populations réellement distinctes peuvent être saisies au même
        # PR, par exemple l'une sur l'accotement et l'autre sur le talus.
        'nb_doublons_position': int((tous_ecarts == 0).sum()),
    }


# ═════════════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ═════════════════════════════════════════════════════════════════════════

def caracteriser_populations_EEE(gdf_EEE,
                                 df_scoring,
                                 gdf_troncons,
                                 mapping_colonnes,
                                 categories_retenues=None,
                                 colonne_id='nom_plo_fi',
                                 source_pr='si_route',
                                 liste_avertissements=None):

    print(f"\n{'='*74}")
    print("CARACTÉRISATION DES POPULATIONS D'EEE")
    print("axe descriptif — ne modifie aucun score MS/N/P, ne produit aucun rang")
    print(f"{'='*74}\n")

    # ═════════════════════════════════════════════════════════════════════
    # ÉTAPE 0 — Vérifications d'entrée
    # On échoue tôt et explicitement plutôt que de produire une sortie vide
    # que personne ne remarquerait.
    # ═════════════════════════════════════════════════════════════════════
    if colonne_id not in gdf_EEE.columns:
        raise ValueError(
            f"❌ '{colonne_id}' introuvable dans gdf_EEE. "
            "La jointure points ↔ tronçons (join_num_troncon_a_gdf_EEE) "
            "a-t-elle bien été faite avant l'appel ?"
        )
    if colonne_id not in df_scoring.columns:
        raise ValueError(f"❌ '{colonne_id}' introuvable dans df_scoring.")

    # Ce module consomme 'species_name_sci' et ne contient AUCUN dictionnaire
    # de mapping d'espèces. C'est délibéré : au 2026-09-08, MS1, MS2, MS3, N2
    # et P1 embarquent chacun leur propre copie d'un dict figé sur la colonne
    # 'plante', ce qui neutralise le travail de fenetre_mapping_especes. On
    # n'ajoute pas un sixième exemplaire à ce copié-collé.
    if 'species_name_sci' not in gdf_EEE.columns:
        raise ValueError(
            "❌ 'species_name_sci' introuvable dans gdf_EEE. "
            "fenetre_mapping_especes.mapping_interactif_especes() doit être "
            "appelée avant ce module."
        )

    for cle in ('largeur', 'longueur', 'compacite'):
        if not mapping_colonnes.get(cle):
            raise ValueError(
                f"❌ La colonne '{cle}' est requise et n'a pas été déclarée. "
                "Sans elle, la caractérisation perdrait son objet "
                "(voir choix structurant CS-5 du document de cadrage)."
            )

    if categories_retenues is None:
        categories_retenues = list(CATEGORIES_SPRINGE.keys())

    # Récupération des noms RÉELS des colonnes dans la couche du gestionnaire.
    # AUCUN nom n'est codé en dur ici (choix structurant CS-4) : le protocole
    # normalise les modalités, pas les noms de colonnes, qui varient d'une DIR
    # et d'un export à l'autre. Un nom codé en dur provoquerait soit un
    # plantage, soit — plus grave — un calcul silencieusement vide.
    col_largeur = mapping_colonnes['largeur']
    col_longueur = mapping_colonnes['longueur']
    col_compacite = mapping_colonnes['compacite']
    col_abscisse = mapping_colonnes.get('abscisse')
    col_localisation = mapping_colonnes.get('localisation')
    col_evaluation = mapping_colonnes.get('evaluation')
    col_date = mapping_colonnes.get('date')

    print("  Colonnes déclarées par le gestionnaire :")
    print(f"    largeur      : {col_largeur}")
    print(f"    longueur     : {col_longueur}")
    print(f"    compacité    : {col_compacite}")
    print(f"    abscisse     : {col_abscisse or '(non fournie)'}")
    print(f"    localisation : {col_localisation or '(non fournie)'}")
    print(f"    évaluation   : {col_evaluation or '(non fournie)'}")
    print(f"    date         : {col_date or '(non fournie)'}\n")

    # Dictionnaire de diagnostic : rempli au fil du calcul, transmis ensuite à
    # generer_notice_lecture pour produire l'aide à la lecture. On y met les
    # chiffres de QUALITÉ de la donnée, pas les résultats eux-mêmes.
    diagnostic = {'colonnes_utilisees': dict(mapping_colonnes)}

    # ═════════════════════════════════════════════════════════════════════
    # ÉTAPE 1 — Extraction d'un DataFrame de travail
    # On abandonne la géométrie : tous les calculs qui suivent sont des
    # comptages et des mesures d'abscisse. Travailler sur un DataFrame simple
    # évite notamment l'ambiguïté de GeoDataFrame.explode(), qui vise la
    # géométrie et non une colonne.
    # ═════════════════════════════════════════════════════════════════════
    colonnes_a_garder = [colonne_id, 'species_name_sci',
                         col_largeur, col_longueur, col_compacite]
    for colonne in (col_abscisse, col_localisation, col_evaluation, col_date):
        if colonne:
            colonnes_a_garder.append(colonne)

    manquantes = [c for c in colonnes_a_garder if c not in gdf_EEE.columns]
    if manquantes:
        raise ValueError(
            f"❌ Colonne(s) déclarée(s) mais absente(s) de gdf_EEE : {manquantes}"
        )

    df = pd.DataFrame(gdf_EEE[colonnes_a_garder]).copy()
    diagnostic['nb_populations_source'] = len(df)

    # ═════════════════════════════════════════════════════════════════════
    # ÉTAPE 2 — Retrait des populations hors tronçon
    # join_num_troncon_a_gdf_EEE marque 'NA' les points qui ne tombent dans
    # aucun tronçon de la zone d'étude. Ils sont hors périmètre.
    # ═════════════════════════════════════════════════════════════════════
    nb_hors_troncon = int((df[colonne_id].astype(str) == 'NA').sum())
    df = df[df[colonne_id].astype(str) != 'NA'].copy()
    diagnostic['nb_hors_troncon'] = nb_hors_troncon
    if nb_hors_troncon > 0:
        _pousser_avertissement(
            liste_avertissements,
            f"Caractérisation EEE : {nb_hors_troncon} population(s) hors de tout "
            f"tronçon de la zone d'étude (ignorées)."
        )

    # ═════════════════════════════════════════════════════════════════════
    # ÉTAPE 3 — Éclatement des populations de bordure
    # Une population à cheval sur deux tronçons porte "A, B" dans colonne_id.
    # On la duplique : une ligne par tronçon intersecté, car la tache existe
    # réellement sur les deux et les deux gestionnaires sont concernés
    # (choix structurant CS-14).
    #
    # Conséquence à assumer ET à signaler : la somme des populations sur tous
    # les tronçons dépasse légèrement l'effectif de la couche source. Ce n'est
    # pas un doublon, c'est une double appartenance réelle.
    # ═════════════════════════════════════════════════════════════════════
    nb_avant_eclatement = len(df)
    # "A, B" -> ["A", " B"], puis une ligne par élément de la liste.
    df[colonne_id] = df[colonne_id].astype(str).str.split(',')
    df = df.explode(colonne_id)
    df[colonne_id] = df[colonne_id].str.strip()   # nettoie l'espace après la virgule
    nb_rattachements_bordure = len(df) - nb_avant_eclatement
    diagnostic['nb_rattachements_bordure'] = nb_rattachements_bordure
    if nb_rattachements_bordure > 0:
        _pousser_avertissement(
            liste_avertissements,
            f"Caractérisation EEE : {nb_rattachements_bordure} rattachement(s) "
            f"supplémentaire(s) issus de populations de bordure, comptées sur "
            f"chacun de leurs tronçons."
        )

    # ═════════════════════════════════════════════════════════════════════
    # ÉTAPE 4 — Normalisation des modalités
    # Chaque colonne descriptive est ramenée aux modalités canoniques du
    # protocole, ou à NON_RENSEIGNE. Aucune imputation (CS-10).
    # ═════════════════════════════════════════════════════════════════════
    df['_largeur'], nb_larg_nr, valeurs_larg_inconnues = _mapper_modalites(
        df[col_largeur], MODALITES_LARGEUR
    )
    df['_longueur'], nb_long_nr, valeurs_long_inconnues = _mapper_modalites(
        df[col_longueur], MODALITES_LONGUEUR
    )
    df['_compacite'], nb_comp_nr, valeurs_comp_inconnues = _mapper_modalites(
        df[col_compacite], MODALITES_COMPACITE
    )

    nb_lignes = max(len(df), 1)   # garde-fou contre une division par zéro
    diagnostic['taux_largeur_nr'] = round(100 * nb_larg_nr / nb_lignes, 1)
    diagnostic['taux_longueur_nr'] = round(100 * nb_long_nr / nb_lignes, 1)
    diagnostic['taux_compacite_nr'] = round(100 * nb_comp_nr / nb_lignes, 1)

    # Des valeurs brutes NON VIDES mais non reconnues sont un signal fort : ce
    # n'est pas un trou de saisie, c'est probablement la mauvaise colonne ou un
    # référentiel différent. On alerte distinctement d'un simple manque.
    for nom_champ, valeurs in [('largeur', valeurs_larg_inconnues),
                               ('longueur', valeurs_long_inconnues),
                               ('compacité', valeurs_comp_inconnues)]:
        if valeurs:
            apercu = ', '.join(f"'{v}'" for v in valeurs[:5])
            suite = ' …' if len(valeurs) > 5 else ''
            _pousser_avertissement(
                liste_avertissements,
                f"Caractérisation EEE : modalité(s) non conforme(s) au protocole "
                f"dans la colonne {nom_champ} : {apercu}{suite}. "
                f"Comptée(s) en 'non renseigné'."
            )

    # --- Localisation sur la dépendance (facultative) ---------------------
    # Pas de liste fermée de modalités ici : le protocole en prévoit une, mais
    # les exports en ajoutent (InterieurEch, AireFrequentee, TablierOA...). On
    # conserve donc la valeur brute nettoyée et on prendra la plus fréquente.
    if col_localisation:
        df['_localisation'] = (
            df[col_localisation].astype(str).str.strip().replace('', NON_RENSEIGNE)
        )
    else:
        df['_localisation'] = NON_RENSEIGNE

    # --- Évaluation du relevé (facultative) -------------------------------
    # Ne sert qu'à une information de traçabilité : aucun comptage, aucune
    # agrégation, aucun calcul géométrique n'en dépend. C'est précisément
    # pourquoi son absence ne bloque rien (choix structurant CS-5).
    if col_evaluation:
        evaluation_normalisee = df[col_evaluation].map(_normaliser_texte)
        df['_incertain'] = (evaluation_normalisee == 'incertain').astype(int)
        nb_incertains = int(df['_incertain'].sum())
        diagnostic['taux_evaluation_incertaine'] = round(
            100 * nb_incertains / nb_lignes, 2
        )
    else:
        df['_incertain'] = np.nan
        diagnostic['taux_evaluation_incertaine'] = None

    # --- Date de relevé (facultative) -------------------------------------
    if col_date:
        # dayfirst=True : le protocole et les exports français utilisent
        # JJ/MM/AAAA. Sans ce paramètre, pandas interpréterait 06/09/2018
        # comme le 9 juin au lieu du 6 septembre.
        dates = pd.to_datetime(df[col_date], errors='coerce', dayfirst=True)
        df['_annee'] = dates.dt.year
        diagnostic['annees_relevees'] = sorted(
            int(a) for a in df['_annee'].dropna().unique()
        )
        # Part de dates tombant un 1er du mois : indice de dates FORFAITAIRES,
        # attribuées à un lot entier plutôt que relevées sur le terrain. Sur le
        # jeu national de référence, ce taux atteint 55,6 %.
        jours = dates.dt.day
        diagnostic['taux_dates_premier_du_mois'] = round(
            100 * float((jours == 1).sum()) / nb_lignes, 1
        )
    else:
        df['_annee'] = np.nan
        diagnostic['annees_relevees'] = []
        diagnostic['taux_dates_premier_du_mois'] = None

    # --- Abscisse curviligne (facultative) --------------------------------
    if col_abscisse:
        df['_abscisse'] = pd.to_numeric(df[col_abscisse], errors='coerce')
    else:
        df['_abscisse'] = np.nan

    # --- Linéaire colonisé minimum, population par population -------------
    # .map() sur les bornes basses ; les NON_RENSEIGNE tombent en NaN, qu'on
    # ramène à 0 : une population dont la longueur est inconnue ne peut pas
    # contribuer à un MINORANT garanti.
    df['_lineaire_min'] = df['_longueur'].map(BORNE_BASSE_LONGUEUR_M).fillna(0)

    # ═════════════════════════════════════════════════════════════════════
    # ÉTAPE 5 — Longueur des tronçons
    # Nécessaire pour 'part_troncon_occupee'. Les abscisses curvilignes du
    # SI ROUTE sont en mètres : longueur = dist_fin - dist_deb.
    # ═════════════════════════════════════════════════════════════════════
    longueurs_troncons = {}
    if source_pr == 'si_route' and {'dist_deb', 'dist_fin'}.issubset(gdf_troncons.columns):
        # min du début et max de la fin : robuste au cas où plusieurs fragments
        # partageraient le même identifiant de tronçon.
        agrege = (
            gdf_troncons.groupby(colonne_id)
                        .agg(_deb=('dist_deb', 'min'), _fin=('dist_fin', 'max'))
        )
        longueurs_troncons = (agrege['_fin'] - agrege['_deb']).to_dict()
    else:
        _pousser_avertissement(
            liste_avertissements,
            "Caractérisation EEE : longueur des tronçons indisponible "
            "(couche non SI ROUTE ou colonnes dist_deb/dist_fin absentes) "
            "→ 'part_troncon_occupee' non calculée."
        )

    # ═════════════════════════════════════════════════════════════════════
    # ÉTAPE 6 — Agrégation par (tronçon × catégorie)
    # Cœur du module : une ligne de sortie par couple observé.
    # ═════════════════════════════════════════════════════════════════════
    lignes_resultat = []

    # groupby sur les deux clés : chaque groupe rassemble les populations
    # d'une catégorie donnée sur un tronçon donné.
    for (id_troncon, categorie), groupe in df.groupby([colonne_id, 'species_name_sci']):

        # On ignore les catégories hors référentiel retenu — par exemple si le
        # gestionnaire n'a coché que 2 espèces sur 5 dans la fenêtre de
        # sélection.
        if categorie not in categories_retenues:
            continue

        comptes_largeur = _compter_par_modalite(groupe, '_largeur', MODALITES_LARGEUR)
        comptes_longueur = _compter_par_modalite(groupe, '_longueur', MODALITES_LONGUEUR)
        comptes_compacite = _compter_par_modalite(groupe, '_compacite', MODALITES_COMPACITE)

        # --- Classe de taille dominante ----------------------------------
        # Le croisement largeur × longueur est conservé comme ÉTIQUETTE
        # ORDINALE, sans aucune arithmétique (choix structurant CS-6) : les
        # classes du protocole étant ouvertes aux deux extrémités, aucun m² ne
        # peut être calculé sans inventer des bornes.
        croisement = groupe['_largeur'] + ' x ' + groupe['_longueur']
        # .mode() renvoie la ou les valeurs les plus fréquentes ; en cas
        # d'égalité pandas les trie et on prend la première — arbitraire mais
        # sans conséquence, puisqu'il s'agit d'une étiquette descriptive.
        modes = croisement.mode()
        if len(modes) > 0:
            largeur_dom, longueur_dom = modes.iloc[0].split(' x ')
            classe_dominante = (
                f"largeur {LIBELLE_LARGEUR.get(largeur_dom, largeur_dom)}"
                f" x longueur {LIBELLE_LONGUEUR.get(longueur_dom, longueur_dom)}"
            )
        else:
            classe_dominante = 'non renseigné'

        # --- Localisation dominante --------------------------------------
        if col_localisation:
            # On exclut les non-renseignés du calcul du mode : sinon, sur une
            # couche à 60 % de trous, la "localisation dominante" serait
            # "non renseigné", ce qui n'apprend rien.
            localisations = groupe.loc[groupe['_localisation'] != NON_RENSEIGNE,
                                       '_localisation']
            modes_loc = localisations.mode()
            localisation_dominante = (
                modes_loc.iloc[0] if len(modes_loc) > 0 else 'non renseigné'
            )
        else:
            localisation_dominante = 'non renseigné'

        # --- Répartition le long de l'axe --------------------------------
        abscisses = groupe['_abscisse'] if col_abscisse else None
        repartition = _calculer_repartition(
            abscisses, longueurs_troncons.get(id_troncon)
        )

        # --- Années de relevé --------------------------------------------
        annees = groupe['_annee'].dropna()
        annee_min = int(annees.min()) if len(annees) > 0 else np.nan
        annee_max = int(annees.max()) if len(annees) > 0 else np.nan

        ligne = {
            'id_troncon': id_troncon,
            'categorie_EEE': categorie,
            'statut_donnee': 'observations enregistrees',
            'nb_populations': len(groupe),

            'nb_pop_largeur_Inf1m': comptes_largeur['Inf1m'],
            'nb_pop_largeur_1a3m': comptes_largeur['1a3m'],
            'nb_pop_largeur_Sup3m': comptes_largeur['Sup3m'],
            'nb_pop_largeur_nr': comptes_largeur[NON_RENSEIGNE],

            'nb_pop_longueur_Inf5m': comptes_longueur['Inf5m'],
            'nb_pop_longueur_5a20m': comptes_longueur['5a20m'],
            'nb_pop_longueur_Sup20m': comptes_longueur['Sup20m'],
            'nb_pop_longueur_nr': comptes_longueur[NON_RENSEIGNE],

            'nb_pop_isolees': comptes_compacite['Isoles'],
            'nb_pop_taches': comptes_compacite['Taches'],
            'nb_pop_continues': comptes_compacite['Continue'],
            'nb_pop_compacite_nr': comptes_compacite[NON_RENSEIGNE],

            'classe_taille_dominante': classe_dominante,
            'lineaire_colonise_minimum_m': int(groupe['_lineaire_min'].sum()),
            # Les populations en classe ouverte 'Sup20m' contribuent 20 m au
            # minorant, mais leur longueur réelle est inconnue vers le haut.
            # Ce compteur dit au gestionnaire à quel point le minorant est
            # susceptible d'être en deçà de la réalité.
            'nb_pop_longueur_non_majoree': comptes_longueur['Sup20m'],

            'etendue_occupee_m': repartition['etendue_occupee_m'],
            'part_troncon_occupee': repartition['part_troncon_occupee'],
            'ecart_min_m': repartition['ecart_min_m'],
            'ecart_median_m': repartition['ecart_median_m'],
            'repartition_calculable': repartition['repartition_calculable'],

            'localisation_dominante': localisation_dominante,
            'annee_releve_min': annee_min,
            'annee_releve_max': annee_max,
        }

        # Champ produit UNIQUEMENT si la colonne évaluation a été fournie. On
        # ne crée pas une colonne vide qui laisserait croire que zéro relevé
        # est incertain, alors que l'information n'existe simplement pas.
        if col_evaluation:
            ligne['nb_pop_evaluation_incertaine'] = int(groupe['_incertain'].sum())

        lignes_resultat.append(ligne)

    df_caracterisation = pd.DataFrame(lignes_resultat)

    # ═════════════════════════════════════════════════════════════════════
    # ÉTAPE 7 — Complétion : tous les tronçons × toutes les catégories
    # Le groupby ci-dessus n'a produit des lignes que pour les couples
    # OBSERVÉS. Il faut ajouter les couples absents avec le statut qui
    # convient — et surtout PAS des zéros (choix structurant CS-11).
    #
    # Rappel du motif : aucune donnée ne permet d'établir qu'un tronçon a été
    # prospecté. Sur le jeu national de référence, 107 CEI sur 219 seulement
    # apparaissent ; pour les autres, rien ne distingue "prospecté sans
    # résultat" de "non prospecté" ou "non transmis". Écrire 0 serait une
    # affirmation d'absence que la donnée ne soutient pas.
    # ═════════════════════════════════════════════════════════════════════
    tous_troncons = df_scoring[colonne_id].astype(str).unique()

    # pd.MultiIndex.from_product génère toutes les combinaisons possibles
    # (produit cartésien) tronçons × catégories, puis .to_frame() en fait un
    # DataFrame à deux colonnes.
    index_complet = pd.MultiIndex.from_product(
        [tous_troncons, categories_retenues],
        names=['id_troncon', 'categorie_EEE']
    ).to_frame(index=False)

    if len(df_caracterisation) > 0:
        # On force le type texte des deux côtés avant le merge : si un côté est
        # en object et l'autre en category (ou en int), pandas ne rapproche
        # rien et le résultat serait silencieusement vide.
        df_caracterisation['id_troncon'] = df_caracterisation['id_troncon'].astype(str)
        df_caracterisation = index_complet.merge(
            df_caracterisation, on=['id_troncon', 'categorie_EEE'], how='left'
        )
    else:
        # Aucune observation du tout dans la zone : on crée quand même les
        # colonnes attendues, vides, pour que la structure de sortie reste
        # identique quoi qu'il arrive.
        df_caracterisation = index_complet.copy()
        for colonne in ['statut_donnee', 'nb_populations',
                        'lineaire_colonise_minimum_m', 'annee_releve_max']:
            df_caracterisation[colonne] = np.nan

    # Un tronçon dont aucune catégorie n'a d'observation reçoit le statut
    # "aucune observation enregistrée". Un tronçon qui porte des renouées mais
    # pas d'ailante reçoit, pour sa ligne ailante, le même statut : la nuance
    # (prospecté ou non) reste hors de portée de la donnée dans les deux cas.
    df_caracterisation['statut_donnee'] = df_caracterisation['statut_donnee'].fillna(
        'aucune observation enregistree'
    )

    # ═════════════════════════════════════════════════════════════════════
    # ÉTAPE 8 — Champs de synthèse pour la couche cartographique
    # Ils sont ajoutés à df_scoring, donc embarqués automatiquement par
    # preparer_couche_gpkg lors de la jointure avec la géométrie. Aucune
    # modification de preparer_couche_gpkg n'est nécessaire.
    # ═════════════════════════════════════════════════════════════════════
    synthese_par_troncon = []
    for id_troncon, lignes_troncon in df_caracterisation.groupby('id_troncon'):
        nb_total = lignes_troncon['nb_populations'].fillna(0).sum()
        nb_categories = int((lignes_troncon['nb_populations'].fillna(0) > 0).sum())
        annees = lignes_troncon['annee_releve_max'].dropna() \
            if 'annee_releve_max' in lignes_troncon.columns else pd.Series(dtype=float)

        synthese_par_troncon.append({
            colonne_id: id_troncon,
            'statut_donnee': ('observations enregistrees' if nb_total > 0
                              else 'aucune observation enregistree'),
            'nb_populations_total': int(nb_total),
            'nb_categories_presentes': nb_categories,
            'synthese_EEE': _construire_synthese_troncon(lignes_troncon),
            'annee_releve_max': int(annees.max()) if len(annees) > 0 else np.nan,
        })

    df_synthese = pd.DataFrame(synthese_par_troncon)

    # Merge sur une clé de même type des deux côtés (texte), sinon pandas ne
    # rapproche rien silencieusement.
    df_scoring = df_scoring.copy()
    df_scoring[colonne_id] = df_scoring[colonne_id].astype(str)
    df_scoring = df_scoring.merge(df_synthese, on=colonne_id, how='left')

    # ═════════════════════════════════════════════════════════════════════
    # ÉTAPE 9 — Diagnostic pour la notice de lecture
    # ═════════════════════════════════════════════════════════════════════
    nb_troncons = len(tous_troncons)
    nb_troncons_sans_obs = int(
        (df_scoring['statut_donnee'] == 'aucune observation enregistree').sum()
    )
    couples_observes = df_caracterisation[
        df_caracterisation['nb_populations'].fillna(0) > 0
    ]
    nb_couples = max(len(couples_observes), 1)   # garde-fou division par zéro

    diagnostic.update({
        'nb_troncons': nb_troncons,
        'nb_troncons_sans_observation': nb_troncons_sans_obs,
        'taux_troncons_sans_observation': round(
            100 * nb_troncons_sans_obs / max(nb_troncons, 1), 1
        ),
        'nb_populations_rattachees': len(df),
        'nb_couples_observes': len(couples_observes),
        'populations_par_categorie': df['species_name_sci'].value_counts().to_dict(),
        'taux_longueur_Inf5m': round(
            100 * float((df['_longueur'] == 'Inf5m').sum()) / nb_lignes, 1
        ),
        'taux_couples_une_population': (
            round(100 * float((couples_observes['nb_populations'] == 1).sum())
                  / nb_couples, 1) if len(couples_observes) > 0 else None
        ),
        'taux_lineaire_minimum_nul': (
            round(100 * float((couples_observes['lineaire_colonise_minimum_m'] == 0).sum())
                  / nb_couples, 1) if len(couples_observes) > 0 else None
        ),
        'taux_localisation_nr': (
            round(100 * float((df['_localisation'] == NON_RENSEIGNE).sum()) / nb_lignes, 1)
            if col_localisation else None
        ),
    })

    # Contrôle de QUALITÉ de la donnée source, pas de résultat : la règle des
    # 50 m du protocole a-t-elle été appliquée uniformément ?
    diagnostic.update(_controler_regle_50m(df, colonne_id, col_abscisse))

    # ═════════════════════════════════════════════════════════════════════
    # ÉTAPE 10 — Récapitulatif console
    # ═════════════════════════════════════════════════════════════════════
    print("Résultats de la caractérisation :")
    print(f"  Tronçons de la zone d'étude            : {nb_troncons}")
    print(f"  dont sans observation enregistrée      : {nb_troncons_sans_obs} "
          f"({diagnostic['taux_troncons_sans_observation']} %)")
    print(f"  Populations rattachées                 : {len(df)}")
    print(f"  Couples (tronçon × catégorie) observés : {len(couples_observes)}")
    print("\n  Populations par catégorie :")
    for categorie, effectif in diagnostic['populations_par_categorie'].items():
        libelle = CATEGORIES_SPRINGE.get(categorie, categorie)
        print(f"    {libelle:<20} {effectif}")
    print("\n  Taux de non-renseigné :")
    print(f"    largeur   : {diagnostic['taux_largeur_nr']} %")
    print(f"    longueur  : {diagnostic['taux_longueur_nr']} %")
    print(f"    compacité : {diagnostic['taux_compacite_nr']} %")
    print(f"\n{'='*74}\n")

    return df_scoring, df_caracterisation, diagnostic
