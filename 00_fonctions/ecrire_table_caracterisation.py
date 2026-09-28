# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
Fonction "ecrire_table_caracterisation"
Date : 2026-09-08
Objectif : écrire la table longue de caractérisation des populations d'EEE
           dans le GeoPackage de sortie, comme table attributaire SANS
           géométrie.
═══════════════════════════════════════════════════════════════════

POURQUOI UN MODULE SÉPARÉ :

preparer_couche_gpkg.py produit et écrit la couche cartographique (une ligne
par tronçon, avec sa géométrie). Les champs de SYNTHÈSE de la caractérisation
y arrivent tout seuls : caracteriser_populations_EEE les ajoute à df_scoring,
et preparer_couche_gpkg joint df_scoring à la géométrie. Aucune modification
de ce fichier n'est donc nécessaire.

En revanche, le DÉTAIL par (tronçon × catégorie) ne peut pas entrer dans cette
couche : il y a 5 lignes par tronçon, alors que la couche en a une seule. Il
faut donc un second objet dans le GeoPackage, écrit après coup — c'est l'objet
de ce module.

POURQUOI UNE TABLE LONGUE PLUTÔT QUE DES COLONNES SUFFIXÉES (choix CS-16) :

L'alternative aurait été d'ajouter à la couche cartographique une colonne par
métrique et par catégorie, soit 5 catégories × ~14 métriques ≈ 70 colonnes.
Dans ce format, l'écrasante majorité des cellules est vide ou nulle, et
retrouver « combien de renouées sur ce PR » impose de faire défiler des
dizaines de colonnes horizontalement.

Le défaut de la table longue — ne rien afficher quand on clique sur un tronçon
dans QGIS — est compensé par le champ 'synthese_EEE' de la couche
cartographique, qui donne le résumé rédigé sans jointure.

FORMAT : le standard GeoPackage (OGC) prévoit explicitement les "attribute
tables", c'est-à-dire des tables sans colonne de géométrie. QGIS les charge
via Couche > Ajouter une couche > Couche vecteur, et elles se joignent à la
couche cartographique par 'id_troncon'.
"""

import pandas as pd


# Nom de la table dans le GeoPackage. Sans accent ni espace : certains outils
# SIG tiers gèrent mal les identifiants de table accentués, et ce nom sert
# aussi de nom de couche affiché dans QGIS.
NOM_TABLE = "caracterisation_EEE_par_troncon_espece"

# Ordre d'affichage des colonnes dans la table attributaire.
# Il n'est pas alphabétique mais LOGIQUE : identification, puis effectif, puis
# les trois familles de descripteurs (ampleur, compacité, répartition), puis la
# traçabilité. Un gestionnaire qui ouvre la table doit pouvoir la lire de
# gauche à droite sans sauter de colonne en colonne.
ORDRE_COLONNES = [
    # -- Identification --
    'id_troncon',
    'categorie_EEE',
    'statut_donnee',
    'nb_populations',
    # -- Ampleur : classes de largeur --
    'nb_pop_largeur_Inf1m',
    'nb_pop_largeur_1a3m',
    'nb_pop_largeur_Sup3m',
    'nb_pop_largeur_nr',
    # -- Ampleur : classes de longueur --
    'nb_pop_longueur_Inf5m',
    'nb_pop_longueur_5a20m',
    'nb_pop_longueur_Sup20m',
    'nb_pop_longueur_nr',
    # -- Compacité (l'axe « diffus ou compact ») --
    'nb_pop_isolees',
    'nb_pop_taches',
    'nb_pop_continues',
    'nb_pop_compacite_nr',
    # -- Synthèses d'ampleur --
    'classe_taille_dominante',
    'lineaire_colonise_minimum_m',
    'nb_pop_longueur_non_majoree',
    # -- Répartition le long de l'axe --
    'repartition_calculable',
    'etendue_occupee_m',
    'part_troncon_occupee',
    'ecart_min_m',
    'ecart_median_m',
    # -- Contexte et traçabilité --
    'localisation_dominante',
    'nb_pop_evaluation_incertaine',
    'annee_releve_min',
    'annee_releve_max',
]


def ecrire_table_caracterisation(df_caracterisation,
                                 chemin_gpkg,
                                 liste_avertissements=None):
    """
    Écrit la table longue dans le GeoPackage existant.

    Paramètres
    ----------
    df_caracterisation : DataFrame produit par caracteriser_populations_EEE
                         (une ligne par tronçon × catégorie).
    chemin_gpkg        : chemin du GeoPackage déjà créé par
                         preparer_couche_gpkg. Le fichier DOIT exister : on
                         ajoute une table, on n'en crée pas un nouveau.
    liste_avertissements : liste où pousser les avertissements (ex.
                         _WARNINGS_SPRINGE), ou None.

    Retour
    ------
    bool : True si l'écriture a réussi, False sinon. L'échec n'est jamais
           bloquant — la couche cartographique et ses champs de synthèse sont
           déjà écrits à ce stade, donc l'essentiel du livrable est sauf.
    """
    print(f"\n{'='*74}")
    print("ÉCRITURE DE LA TABLE DE CARACTÉRISATION DANS LE GEOPACKAGE")
    print(f"{'='*74}\n")

    if df_caracterisation is None or len(df_caracterisation) == 0:
        print("ℹ️  Aucune donnée de caractérisation à écrire (table vide).")
        return False

    chemin_gpkg = str(chemin_gpkg)

    # --- Mise en ordre des colonnes ---------------------------------------
    # On ne garde de ORDRE_COLONNES que celles réellement présentes : selon les
    # champs facultatifs déclarés par le gestionnaire, certaines colonnes
    # n'existent pas (par exemple 'nb_pop_evaluation_incertaine' si la colonne
    # évaluation n'a pas été fournie).
    colonnes_presentes = [c for c in ORDRE_COLONNES if c in df_caracterisation.columns]

    # Filet de sécurité : si le module de calcul ajoutait un jour une colonne
    # sans qu'on pense à l'inscrire dans ORDRE_COLONNES, elle serait
    # silencieusement perdue. On récupère donc les oubliées et on les place à
    # la fin plutôt que de les jeter.
    colonnes_oubliees = [c for c in df_caracterisation.columns
                         if c not in colonnes_presentes]
    if colonnes_oubliees:
        print(f"ℹ️  Colonnes hors ordre prédéfini, placées en fin de table : "
              f"{colonnes_oubliees}")

    table = df_caracterisation[colonnes_presentes + colonnes_oubliees].copy()

    # --- Typage des colonnes de comptage ----------------------------------
    # Les comptages sont conceptuellement des entiers, mais pandas les stocke
    # en float dès qu'une valeur manquante apparaît (NaN n'existe pas dans les
    # entiers natifs). On utilise le type entier NULLABLE 'Int64' (avec un I
    # majuscule) : il accepte les valeurs manquantes tout en restant entier.
    #
    # Sans cela, la table attributaire afficherait "3.0" au lieu de "3" dans
    # QGIS, ce qui donne l'impression fausse d'une mesure continue là où il
    # s'agit d'un dénombrement.
    for colonne in table.columns:
        if colonne.startswith('nb_') or colonne.startswith('annee_') \
                or colonne == 'lineaire_colonise_minimum_m':
            table[colonne] = pd.to_numeric(table[colonne], errors='coerce').astype('Int64')

    # --- Écriture ----------------------------------------------------------
    try:
        # Import local plutôt qu'en tête de module : ce module peut être chargé
        # par le mécanisme d'auto-import de 00_fonctions/ dans un contexte où
        # les dépendances SIG ne sont pas encore initialisées. On ne les
        # sollicite qu'au moment de s'en servir.
        import geopandas as gpd

        # On passe par un GeoDataFrame sans géométrie : c'est la voie que
        # geopandas/pyogrio expose pour écrire une table attributaire dans un
        # GeoPackage. Le driver GPKG crée alors une "attribute table" au sens
        # du standard OGC, sans colonne géométrique ni entrée dans
        # gpkg_geometry_columns.
        gdf_sans_geometrie = gpd.GeoDataFrame(table)

        gdf_sans_geometrie.to_file(
            chemin_gpkg,
            layer=NOM_TABLE,
            driver="GPKG",
            # mode="a" : on AJOUTE une table au GeoPackage existant. Sans ce
            # paramètre, to_file écraserait le fichier entier et la couche
            # cartographique serait perdue.
            mode="a",
        )

        nb_lignes = len(table)
        nb_observes = int((table['nb_populations'].fillna(0) > 0).sum()) \
            if 'nb_populations' in table.columns else 0

        print(f"✔️  Table '{NOM_TABLE}' écrite dans le GeoPackage.")
        print(f"    {nb_lignes} ligne(s) — {len(table.columns)} colonne(s)")
        print(f"    dont {nb_observes} couple(s) (tronçon × catégorie) "
              f"avec observations")
        print(f"    Fichier : {chemin_gpkg}")
        print("\n    Pour l'utiliser dans QGIS : Couche > Ajouter une couche > "
              "Couche vecteur,\n    puis jointure sur 'id_troncon'.")
        print(f"\n{'='*74}\n")
        return True

    except Exception as erreur:
        # Échec non bloquant : le GeoPackage et ses champs de synthèse existent
        # déjà. On informe, on trace, et le run se termine normalement.
        message = (f"Table de caractérisation : écriture dans le GeoPackage "
                   f"échouée — {str(erreur)[:150]}")
        print(f"⚠️  {message}")
        print("    La couche cartographique et ses champs de synthèse "
              "(synthese_EEE, nb_populations_total…) sont bien présents.")
        if liste_avertissements is not None:
            liste_avertissements.append(message)

        # Repli : on écrit au moins un CSV à côté du GeoPackage, pour que le
        # détail ne soit pas perdu. Un CSV n'est pas le livrable prévu, mais
        # c'est mieux que rien et il se réimporte dans QGIS.
        try:
            chemin_csv = chemin_gpkg.replace('.gpkg', f'_{NOM_TABLE}.csv')
            # encoding utf-8-sig : ajoute un BOM que Excel reconnaît, sans quoi
            # les accents s'affichent en caractères parasites à l'ouverture.
            table.to_csv(chemin_csv, index=False, sep=';', encoding='utf-8-sig')
            print(f"    ↳ Repli : table exportée en CSV → {chemin_csv}")
            if liste_avertissements is not None:
                liste_avertissements.append(
                    f"Table de caractérisation : exportée en CSV de repli "
                    f"({chemin_csv})."
                )
        except Exception as erreur_csv:
            print(f"    ↳ Le repli CSV a également échoué : {erreur_csv}")

        return False
