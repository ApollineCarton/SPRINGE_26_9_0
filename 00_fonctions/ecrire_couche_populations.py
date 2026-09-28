# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
Fonction "ecrire_couche_populations"
Date : 2026-09-11
Objectif : écrire dans le GeoPackage de sortie la couche de points des
           populations d'EEE, HARMONISÉE : mêmes noms de colonnes et mêmes
           modalités quelle que soit la DIR qui a fourni la couche.
═══════════════════════════════════════════════════════════════════

POURQUOI CETTE COUCHE :

Les styles QGIS (.qml) désignent les colonnes par leur NOM et les valeurs par
leur orthographe EXACTE (« si "compacite" = 'Continue', rond plein »). Or la
couche de points fournie par chaque DIR a ses propres noms de colonnes
('densite', 'compacite', 'localisati' tronqué par le format shapefile...) :
un style construit sur une couche ne fonctionnerait pas sur celle d'une autre
DIR.

Le lanceur connaît déjà la correspondance, puisque les fenêtres
fenetre_mapping_especes et fenetre_mapping_colonnes_EEE demandent au
gestionnaire quelle colonne porte quelle information. Ce module applique
cette correspondance et écrit le résultat avec des noms FIXES : un seul style
fonctionne alors pour toutes les DIR.

QUAND CE MODULE EST APPELÉ :

Uniquement si la caractérisation des populations est active (données déclarées
conformes au protocole Albert 2017, colonnes validées). Sans caractérisation,
les colonnes largeur / longueur / compacité ne sont pas identifiées : il n'y
aurait aucune variable à représenter.

CHOIX DE CONTENU :

  1. UNE LIGNE PAR POPULATION, jamais une ligne par rattachement. Une
     population à cheval sur deux tronçons n'est pas dupliquée (sinon deux
     points identiques se superposeraient sur la carte) : ses tronçons sont
     listés dans 'id_troncons' et comptés dans 'nb_troncons'.

  2. POPULATIONS HORS TRONÇON EXCLUES. La jointure marque 'NA' les points de
     l'emprise qui ne tombent dans aucun tronçon. La caractérisation les
     ignore ; on les ignore aussi, pour que cette couche décrive exactement
     les populations prises en compte dans la table de caractérisation.

  3. SEULES LES COLONNES HARMONISÉES sont écrites (liste COLONNES_SORTIE),
     et elles sont TOUJOURS TOUTES présentes, même quand l'information
     facultative n'a pas été fournie. Motif : un style qui cherche une colonne
     absente ne s'affiche pas du tout. Deux cas sont distingués :
       - colonne facultative NON DÉCLARÉE par le gestionnaire → valeur vide
         (NULL) sur toutes les lignes : l'information n'existe pas ;
       - colonne déclarée mais case vide ou valeur hors protocole → 'nr'
         (non renseigné) : l'information existe mais manque pour ce point.

  4. MÊMES RÈGLES DE NORMALISATION QUE LA CARACTÉRISATION. On réutilise les
     fonctions et constantes de caracteriser_populations_EEE (modalités
     canoniques, gestion des accents et de la casse, 'nr') plutôt que de les
     recopier : la couche de points et la table de caractérisation ne peuvent
     pas diverger.

Nom de la couche dans le GeoPackage : 'caracterisation_population'.
"""

import pandas as pd

# Réutilisation des outils de normalisation du module de caractérisation.
# Ce module est dans le même dossier 00_fonctions/, déjà ajouté à sys.path par
# le lanceur : l'import fonctionne comme dans fenetre_mapping_colonnes_EEE.
import caracteriser_populations_EEE as cpe


# Nom de la couche. Sans accent ni espace (même motif que NOM_TABLE dans
# ecrire_table_caracterisation) : certains outils SIG gèrent mal les noms de
# couche accentués.
NOM_COUCHE = "caracterisation_population"

# Colonnes écrites, dans l'ordre d'affichage de la table attributaire QGIS :
# identification, rattachement, les trois variables obligatoires du protocole,
# puis les facultatives. 'geometry' est ajoutée par geopandas.
COLONNES_SORTIE = [
    'id_population',    # entier 1..n, attribué ici (voir étape 6)
    'espece',           # species_name_sci : 'Reynoutria sp', 'EEE autre'...
    'espece_libelle',   # libellé lisible : 'Renouées', 'Ailante'...
    'id_troncons',      # tronçon(s) de rattachement, ex. '35PR2D, 35PR2G'
    'nb_troncons',      # 1, ou 2 et plus pour une population de bordure
    'largeur',          # obligatoire : 'Inf1m' / '1a3m' / 'Sup3m' / 'nr'
    'longueur',         # obligatoire : 'Inf5m' / '5a20m' / 'Sup20m' / 'nr'
    'compacite',        # obligatoire : 'Isoles' / 'Taches' / 'Continue' / 'nr'
    'localisation',     # facultatif : valeur brute nettoyée, 'nr' ou NULL
    'evaluation',       # facultatif : 'Certain' / 'Incertain' / 'nr' ou NULL
    'date_releve',      # facultatif : date, ou NULL
    'annee_releve',     # facultatif : entier, ou NULL
    'abscisse_m',       # facultatif : abscisse curviligne en mètres, ou NULL
]


def _valeur_texte_ou_nr(serie):
    """
    Nettoie une colonne texte à valeurs libres (la localisation) : espaces de
    bord retirés, et toute case vide ramenée à 'nr'.

    Pourquoi ne pas faire simplement serie.astype(str) : pandas convertit alors
    une case vide (None ou NaN) en la CHAÎNE 'None' ou 'nan', qui passerait
    ensuite pour une vraie modalité. On repère donc les vides AVANT la
    conversion en texte.
    """
    # .isna() repère None et NaN ; on les garde de côté.
    vide = serie.isna()
    # Conversion en texte et nettoyage des espaces, sur toute la colonne.
    texte = serie.astype(str).str.strip()
    # Une chaîne réduite à rien après nettoyage est aussi un vide.
    vide = vide | (texte == '')
    # .where(condition, autre) garde la valeur là où la condition est vraie
    # et met 'autre' ailleurs : ici, 'nr' partout où la case était vide.
    return texte.where(~vide, cpe.NON_RENSEIGNE)


def ecrire_couche_populations(gdf_EEE,
                              mapping_colonnes,
                              chemin_gpkg,
                              crs_cible=None,
                              colonne_id='nom_plo_fi',
                              liste_avertissements=None):
    """
    Construit la couche harmonisée des populations et l'ajoute au GeoPackage.

    Paramètres
    ----------
    gdf_EEE : GeoDataFrame des points EEE APRÈS mapping des espèces (colonne
              'species_name_sci'), filtrage des espèces retenues et jointure
              aux tronçons (colonne colonne_id). C'est l'objet que le lanceur
              passe déjà à caracteriser_populations_EEE.
    mapping_colonnes : dict {information : nom de colonne ou None} renvoyé par
              fenetre_mapping_colonnes_EEE. Clés : largeur, longueur,
              compacite (obligatoires), abscisse, localisation, evaluation,
              date (facultatives).
    chemin_gpkg : GeoPackage déjà créé par preparer_couche_gpkg. On AJOUTE une
              couche, on ne crée pas de nouveau fichier.
    crs_cible : système de coordonnées de la couche des tronçons. Si les points
              sont dans un autre système, ils sont reprojetés pour se
              superposer exactement aux tronçons dans QGIS. None = pas de
              reprojection.
    colonne_id : nom interne de la colonne de rattachement ('nom_plo_fi').
    liste_avertissements : liste où pousser les avertissements
              (_WARNINGS_SPRINGE), ou None.

    Retour
    ------
    bool : True si la couche est écrite, False sinon. Jamais bloquant : la
           couche des tronçons et la table de caractérisation sont déjà écrites.
    """
    print(f"\n{'='*74}")
    print("ÉCRITURE DE LA COUCHE HARMONISÉE DES POPULATIONS DANS LE GEOPACKAGE")
    print(f"{'='*74}\n")

    try:
        import geopandas as gpd
        import shapely

        # ═════════════════════════════════════════════════════════════════
        # ÉTAPE 1 — Vérifications d'entrée
        # ═════════════════════════════════════════════════════════════════
        if gdf_EEE is None or len(gdf_EEE) == 0:
            print("ℹ️  Aucun point EEE : couche des populations non écrite.")
            return False

        for colonne in (colonne_id, 'species_name_sci'):
            if colonne not in gdf_EEE.columns:
                raise ValueError(f"colonne '{colonne}' introuvable dans gdf_EEE")

        # Les trois colonnes obligatoires doivent avoir été déclarées : c'est
        # déjà garanti quand la caractérisation est active, mais on revérifie
        # pour que le module reste sûr s'il est appelé ailleurs.
        for cle in ('largeur', 'longueur', 'compacite'):
            if not mapping_colonnes.get(cle):
                raise ValueError(f"colonne obligatoire '{cle}' non déclarée")

        # ═════════════════════════════════════════════════════════════════
        # ÉTAPE 2 — Retrait des populations hors tronçon
        # La jointure écrit la CHAÎNE 'NA' (pas une valeur vide) pour un point
        # sans tronçon : on compare donc au texte 'NA'.
        # ═════════════════════════════════════════════════════════════════
        rattache = gdf_EEE[colonne_id].astype(str) != 'NA'
        nb_hors_troncon = int((~rattache).sum())
        points = gdf_EEE[rattache].copy()

        if len(points) == 0:
            print("ℹ️  Aucune population rattachée à un tronçon : couche non écrite.")
            return False

        # ═════════════════════════════════════════════════════════════════
        # ÉTAPE 3 — Identification et rattachement
        # ═════════════════════════════════════════════════════════════════
        # On construit un DataFrame neuf, colonne par colonne, plutôt que de
        # renommer les colonnes de la couche source : ainsi aucune colonne
        # d'origine ne peut se glisser dans la sortie par accident.
        # index=points.index : les nouvelles colonnes s'alignent ligne à ligne
        # sur les points.
        sortie = pd.DataFrame(index=points.index)

        sortie['espece'] = points['species_name_sci']
        # .map(dict) traduit chaque code en libellé ; un code absent du
        # dictionnaire (ne devrait pas arriver) garde sa valeur d'origine
        # grâce à .fillna().
        sortie['espece_libelle'] = (
            points['species_name_sci'].map(cpe.CATEGORIES_SPRINGE)
                                      .fillna(points['species_name_sci'])
        )

        # La jointure produit déjà 'A, B' pour une population de bordure :
        # on garde ce texte tel quel (lisible au clic dans QGIS).
        sortie['id_troncons'] = points[colonne_id].astype(str)
        # Nombre de tronçons = nombre d'éléments séparés par une virgule.
        sortie['nb_troncons'] = (
            sortie['id_troncons'].str.split(',').str.len().astype('Int64')
        )

        # ═════════════════════════════════════════════════════════════════
        # ÉTAPE 4 — Variables obligatoires du protocole
        # _mapper_modalites (module de caractérisation) ramène chaque valeur
        # brute à une modalité canonique ('Isolés', 'ISOLES' → 'Isoles'), et
        # toute valeur vide ou inconnue à 'nr'. Il renvoie aussi des comptages
        # d'anomalies, déjà signalés par la caractérisation : on les ignore
        # ici (le « _ » reçoit les valeurs dont on ne se sert pas).
        # ═════════════════════════════════════════════════════════════════
        for cle, modalites in (('largeur', cpe.MODALITES_LARGEUR),
                               ('longueur', cpe.MODALITES_LONGUEUR),
                               ('compacite', cpe.MODALITES_COMPACITE)):
            sortie[cle], _, _ = cpe._mapper_modalites(
                points[mapping_colonnes[cle]], modalites
            )

        # ═════════════════════════════════════════════════════════════════
        # ÉTAPE 5 — Variables facultatives
        # Principe (voir en-tête) : colonne non déclarée → NULL partout ;
        # colonne déclarée → valeur harmonisée, 'nr' si la case est vide.
        # pd.NA est la valeur manquante « universelle » de pandas : elle est
        # écrite comme un vrai NULL dans le GeoPackage, quel que soit le type.
        # ═════════════════════════════════════════════════════════════════
        colonnes_non_fournies = []

        # --- Localisation : liste de modalités ouverte (les exports ajoutent
        # des valeurs au protocole), donc simple nettoyage.
        col = mapping_colonnes.get('localisation')
        if col:
            sortie['localisation'] = _valeur_texte_ou_nr(points[col])
        else:
            sortie['localisation'] = pd.Series(pd.NA, index=points.index, dtype='string')
            colonnes_non_fournies.append('localisation')

        # --- Évaluation : 2 modalités, normalisées comme les obligatoires.
        col = mapping_colonnes.get('evaluation')
        if col:
            sortie['evaluation'], _, _ = cpe._mapper_modalites(
                points[col], ['Certain', 'Incertain']
            )
        else:
            sortie['evaluation'] = pd.Series(pd.NA, index=points.index, dtype='string')
            colonnes_non_fournies.append('evaluation')

        # --- Date : même lecture que la caractérisation (JJ/MM/AAAA, d'où
        # dayfirst=True). errors='coerce' : une date illisible devient NaT
        # (« Not a Time », la valeur manquante des dates), écrite NULL.
        col = mapping_colonnes.get('date')
        if col:
            dates = pd.to_datetime(points[col], errors='coerce', dayfirst=True)
            # .dt.normalize() ramène l'heure à 00:00 : seul le jour a un sens.
            # On garde le type date-heure de pandas, que le GeoPackage stocke
            # dans un vrai champ date (triable, filtrable dans QGIS), et non
            # un texte. Les NaT sont écrits NULL.
            sortie['date_releve'] = dates.dt.normalize()
            sortie['annee_releve'] = dates.dt.year.astype('Int64')
        else:
            # Colonne de dates entièrement vide, mais du bon type : le champ
            # existe dans le GeoPackage avec le même type que pour une DIR
            # qui a fourni les dates.
            sortie['date_releve'] = pd.Series(pd.NaT, index=points.index, dtype='datetime64[ns]')
            sortie['annee_releve'] = pd.Series(pd.NA, index=points.index, dtype='Int64')
            colonnes_non_fournies.append('date')

        # --- Abscisse curviligne : numérique ; texte non convertible → NULL.
        col = mapping_colonnes.get('abscisse')
        if col:
            # .astype('Float64') : toujours un champ décimal, que la couche
            # source stocke l'abscisse en entiers ou en décimaux. Le type du
            # champ reste ainsi identique d'une DIR à l'autre.
            sortie['abscisse_m'] = pd.to_numeric(points[col], errors='coerce').astype('Float64')
        else:
            sortie['abscisse_m'] = pd.Series(pd.NA, index=points.index, dtype='Float64')
            colonnes_non_fournies.append('abscisse')

        # ═════════════════════════════════════════════════════════════════
        # ÉTAPE 6 — Identifiant de population
        # Numérotation 1..n dans l'ordre de la couche source. Aucune colonne
        # d'identifiant n'étant déclarée dans les fenêtres de mapping, on n'en
        # reprend pas : cet identifiant sert à désigner un point dans CE run
        # (il peut changer d'un run à l'autre).
        # ═════════════════════════════════════════════════════════════════
        sortie['id_population'] = pd.array(range(1, len(sortie) + 1), dtype='Int64')

        # ═════════════════════════════════════════════════════════════════
        # ÉTAPE 7 — Géométrie
        # shapely.force_2d retire l'altitude (Z) et la mesure (M) : certaines
        # couches SI ROUTE sont en « Point Z M », alors que seule la position
        # en plan sert ici. Une géométrie 2D s'écrit et s'affiche partout
        # sans surprise.
        # ═════════════════════════════════════════════════════════════════
        geometrie = gpd.GeoSeries(shapely.force_2d(points.geometry.values),
                                  index=points.index, crs=points.crs)

        couche = gpd.GeoDataFrame(sortie[COLONNES_SORTIE], geometry=geometrie, crs=points.crs)

        # Reprojection vers le système des tronçons si nécessaire. On ne
        # reprojette pas si l'un des deux systèmes est inconnu : on ne
        # saurait pas quoi convertir en quoi.
        if crs_cible is not None and couche.crs is not None and couche.crs != crs_cible:
            print(f"    Reprojection des points : {couche.crs.to_string()} → "
                  f"{gpd.GeoSeries([], crs=crs_cible).crs.to_string()}")
            couche = couche.to_crs(crs_cible)

        # ═════════════════════════════════════════════════════════════════
        # ÉTAPE 8 — Écriture
        # mode="a" : AJOUT au GeoPackage existant. Sans ce paramètre, le
        # fichier entier serait écrasé et la couche des tronçons perdue.
        # ═════════════════════════════════════════════════════════════════
        couche.to_file(str(chemin_gpkg), layer=NOM_COUCHE, driver="GPKG", mode="a")

        # ═════════════════════════════════════════════════════════════════
        # ÉTAPE 9 — Compte rendu console et avertissements
        # ═════════════════════════════════════════════════════════════════
        nb_bordure = int((sortie['nb_troncons'] > 1).sum())
        print(f"✔️  Couche '{NOM_COUCHE}' écrite : {len(couche)} population(s).")
        print(f"    dont {nb_bordure} population(s) de bordure (plusieurs tronçons), "
              f"non dupliquées")
        if nb_hors_troncon:
            print(f"    {nb_hors_troncon} point(s) hors de tout tronçon non écrit(s)")
        if colonnes_non_fournies:
            message = (f"Couche '{NOM_COUCHE}' : information(s) facultative(s) non "
                       f"fournie(s) → champ(s) laissé(s) vide(s) : "
                       f"{', '.join(colonnes_non_fournies)}.")
            print(f"ℹ️  {message}")
            if liste_avertissements is not None:
                liste_avertissements.append(message)
        print(f"    Fichier : {chemin_gpkg}")
        print(f"\n{'='*74}\n")
        return True

    except Exception as erreur:
        # Échec non bloquant : tronçons et table de caractérisation sont déjà
        # écrits. On informe et on trace pour le rapport d'exécution.
        message = (f"Couche '{NOM_COUCHE}' : écriture dans le GeoPackage échouée "
                   f"— {str(erreur)[:150]}")
        print(f"⚠️  {message}")
        if liste_avertissements is not None:
            liste_avertissements.append(message)
        return False
