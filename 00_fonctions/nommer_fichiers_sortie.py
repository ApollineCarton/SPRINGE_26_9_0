# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
Module "nommer_fichiers_sortie"
Date : 2026-09-08
Objectif : produire, en un seul endroit, les noms de TOUS les fichiers
           que SPRINGE écrit sur disque.
═══════════════════════════════════════════════════════════════════

POURQUOI CE MODULE EXISTE

Avant ce module, chaque producteur de fichier fabriquait son nom dans son
coin : preparer_couche_gpkg pour le GeoPackage, generer_rapport pour le
rapport et l'incident, et le script principal RECONSTRUISAIT le nom du
GeoPackage à l'identique pour pouvoir le retrouver — avec un commentaire
« ⚠️ DOIT rester strictement cohérent » qui signale bien le danger.

Cette duplication a produit exactement le défaut qu'on attend d'elle. Le
nom du GeoPackage était :

    projet_SPRINGE_{name}_{DIR}_{date}

où `name` valait déjà "SPRINGE_modele_Version2026_{DIR}_{NOM}". Résultat pour
un opérateur "apo" de la structure "cbn" :

    projet_SPRINGE_SPRINGE_modele_Version2026_cbn_apo_cbn_20260724
           ~~~~~~~ ~~~~~~~                    ~~~     ~~~
           "SPRINGE" deux fois          "cbn" deux fois

Désormais, un seul endroit fabrique les noms. Changer de version, d'ordre ou
de séparateur se fait ici et se répercute partout.

────────────────────────── TRAME RETENUE ──────────────────────────

    <SOCLE_VERSION>_<opérateur>_<structure>_<date>[_<TYPE>].<ext>

    SPRINGE_version202609_apo_cbn_20260724.gpkg
    SPRINGE_version202609_apo_cbn_20260724_RAPPORT.txt
    SPRINGE_version202609_apo_cbn_20260724_INCIDENT.txt
    SPRINGE_version202609_apo_cbn_20260724_NOTICE.txt

Deux partis pris :

  1. SOCLE EN TÊTE, TYPE EN SUFFIXE. Tous les fichiers d'une même exécution
     se retrouvent côte à côte dans l'explorateur, triés ensemble. La
     convention inverse (RAPPORT_SPRINGE_..., INCIDENT_SPRINGE_...) triait
     par type de fichier et dispersait les livrables d'un même run.

  2. DATE SANS HEURE. Décision du 08/09/2026 : l'heure alourdit le nom sans
     apporter grand-chose au gestionnaire. Voir plus bas la gestion des
     collisions, qui en découle.

────────────────── COLLISIONS : DEUX COMPORTEMENTS ──────────────────

Sans l'heure, deux exécutions le même jour produisent le même nom. Les deux
familles de fichiers n'appellent pas la même réponse :

  - LIVRABLES (GeoPackage, notice) : ÉCRASEMENT. Ce sont des produits
    régénérables, et on veut que leur nom soit prévisible — c'est ce qui
    permet au gestionnaire de savoir à l'avance où chercher son résultat.
    C'était déjà le comportement du GeoPackage.

  - TRACES D'EXÉCUTION (rapport, incident) : SUFFIXE INCRÉMENTAL. Ce sont
    des historiques : écraser le rapport d'un crash parce qu'on relance
    dans la foulée ferait perdre l'information au moment précis où on en a
    besoin. Le suffixe n'apparaît QU'EN CAS de collision réelle, donc le
    premier fichier de la journée garde le nom canonique :

        ..._20260908_INCIDENT.txt
        ..._20260908_INCIDENT_02.txt
        ..._20260908_INCIDENT_03.txt

Ce module ne fait qu'une chose : fabriquer des noms. Il n'écrit aucun
fichier et ne crée aucun dossier.
"""

import unicodedata
from datetime import date as _date
from pathlib import Path


# ═════════════════════════════════════════════════════════════════════════
# À METTRE À JOUR À CHAQUE NOUVELLE VERSION DE SPRINGE
# ═════════════════════════════════════════════════════════════════════════
# Format retenu : SPRINGE_version<AAAAMM>, soit l'année et le mois de la
# version livrée. C'est la SEULE ligne à modifier pour renommer toutes les
# sorties de SPRINGE.
SOCLE_VERSION = "SPRINGE_version202609"


# Suffixes de type. Regroupés ici pour rester cohérents entre modules : si
# on renomme "RAPPORT" en "EXECUTION", ça se répercute partout.
SUFFIXE_RAPPORT = "RAPPORT"
SUFFIXE_INCIDENT = "INCIDENT"
SUFFIXE_NOTICE = "NOTICE"


def nettoyer_composant(valeur, defaut="inconnu"):
    """
    Rend une saisie utilisateur utilisable dans un nom de fichier.

    L'opérateur et la structure sont saisis à la main dans la fenêtre
    d'identification. Rien n'empêche d'y taper « DIR Ouest », « Conservatoire
    Botanique » ou « François ». Ces valeurs partent ensuite dans un nom de
    fichier ET dans un nom de couche GeoPackage, où les espaces, accents et
    caractères spéciaux posent des problèmes réels : couche illisible par
    certains outils SIG tiers, chemins à quoter, casse selon le système.

    Traitement appliqué :
      - suppression des accents (é -> e), pour éviter les soucis d'encodage
        entre Windows, QGIS et les outils tiers ;
      - remplacement par '-' de tout ce qui n'est ni lettre, ni chiffre, ni
        tiret ou underscore. On choisit '-' et non '_' parce que '_' est déjà
        notre séparateur de composants : « DIR Ouest » doit donner
        « DIR-Ouest » et non « DIR_Ouest », qui se lirait comme deux
        composants distincts ;
      - compactage des tirets consécutifs et rognage des tirets de bord ;
      - repli sur `defaut` si rien d'exploitable ne subsiste.

    La casse est CONSERVÉE : « DIRO » reste « DIRO ». Elle porte souvent du
    sens pour le gestionnaire, et les systèmes de fichiers courants la gèrent.
    """
    if valeur is None:
        return defaut

    texte = str(valeur).strip()
    if not texte:
        return defaut

    # Décomposition Unicode puis retrait des marques d'accentuation :
    # 'é' devient 'e' + accent combinant, dont on ne garde que le 'e'.
    decompose = unicodedata.normalize('NFD', texte)
    sans_accent = ''.join(c for c in decompose if unicodedata.category(c) != 'Mn')

    caracteres = [
        c if (c.isalnum() or c in '-_') else '-'
        for c in sans_accent
    ]
    nettoye = ''.join(caracteres)

    # Compactage : « DIR   Ouest » a produit « DIR---Ouest », on veut
    # « DIR-Ouest ».
    while '--' in nettoye:
        nettoye = nettoye.replace('--', '-')
    nettoye = nettoye.strip('-_')

    return nettoye if nettoye else defaut


def socle(NOM, DIR, date_reference=None):
    """
    Construit la partie commune à tous les noms de fichiers d'une exécution.

    Ordre des composants : OPÉRATEUR puis STRUCTURE, conformément à la
    décision du 08/09/2026 (« nom gestionnaire _ structure _ date »).

    Paramètres
    ----------
    NOM : nom de l'opérateur, saisi dans la fenêtre d'identification.
    DIR : structure / DIR, saisie dans la même fenêtre.
    date_reference : datetime.date ou datetime.datetime. Par défaut,
        aujourd'hui. Le paramètre existe pour que tous les fichiers d'un run
        démarré à 23h58 portent la même date, même si l'exécution franchit
        minuit : le script principal passe alors la date de DÉBUT.

    Retour : par exemple "SPRINGE_version202609_apo_cbn_20260724"
    """
    if date_reference is None:
        date_reference = _date.today()

    jour = date_reference.strftime('%Y%m%d')
    operateur = nettoyer_composant(NOM, defaut="utilisateur")
    structure = nettoyer_composant(DIR, defaut="structure")

    return f"{SOCLE_VERSION}_{operateur}_{structure}_{jour}"


def _premier_libre(dossier, base, extension):
    """
    Renvoie un nom de fichier qui n'existe pas encore dans le dossier.

    Essaie d'abord `base.extension`. S'il existe déjà, tente `base_02`,
    `base_03`, etc. Le premier fichier de la journée garde donc le nom
    canonique, sans suffixe parasite.

    Utilisé UNIQUEMENT pour les traces d'exécution (rapport, incident) —
    jamais pour les livrables, dont le nom doit rester prévisible.

    La borne à 99 est un garde-fou : si on en arrive là, quelque chose tourne
    en boucle et mieux vaut écraser que remplir le disque de variantes.
    """
    dossier = Path(dossier)

    candidat = f"{base}.{extension}"
    if not (dossier / candidat).exists():
        return candidat

    for compteur in range(2, 100):
        candidat = f"{base}_{compteur:02d}.{extension}"
        if not (dossier / candidat).exists():
            return candidat

    return f"{base}_99.{extension}"


# ═════════════════════════════════════════════════════════════════════════
# UN APPEL PAR TYPE DE SORTIE
# Chaque producteur de fichier appelle SA fonction et n'assemble jamais un
# nom lui-même.
# ═════════════════════════════════════════════════════════════════════════

def nom_couche_gpkg(NOM, DIR, date_reference=None):
    """
    Nom de la COUCHE à l'intérieur du GeoPackage — sans extension.

    Volontairement identique au nom du fichier : dans QGIS, la couche
    apparaît sous ce nom dans le panneau des couches, et le gestionnaire doit
    pouvoir faire le lien avec le fichier sans réfléchir.
    """
    return socle(NOM, DIR, date_reference)


def nom_fichier_gpkg(NOM, DIR, date_reference=None):
    """
    Nom du fichier GeoPackage.

    Écrasement assumé en cas de réexécution le même jour : c'est le livrable
    principal, régénérable, et son nom doit rester prévisible.
    """
    return f"{socle(NOM, DIR, date_reference)}.gpkg"


def nom_fichier_notice(NOM, DIR, date_reference=None):
    """
    Nom de la notice de lecture de la caractérisation des populations EEE.

    Écrasement assumé, même motif que le GeoPackage : la notice décrit le
    contenu du GeoPackage du jour, les deux doivent rester en phase.
    """
    return f"{socle(NOM, DIR, date_reference)}_{SUFFIXE_NOTICE}.txt"


def nom_fichier_rapport(output_dir, NOM, DIR, date_reference=None):
    """
    Nom du rapport d'exécution.

    Suffixe incrémental en cas de collision : c'est une trace d'exécution,
    pas un livrable. Deux runs dans la journée doivent laisser deux rapports.

    Nécessite `output_dir` pour vérifier ce qui existe déjà — d'où la
    signature différente des fonctions ci-dessus.
    """
    base = f"{socle(NOM, DIR, date_reference)}_{SUFFIXE_RAPPORT}"
    return _premier_libre(output_dir, base, "txt")


def nom_fichier_incident(output_dir, NOM, DIR, date_reference=None):
    """
    Nom du rapport d'incident.

    Suffixe incrémental, comme le rapport d'exécution, et pour une raison
    encore plus forte : pendant une séance de débogage, plusieurs crashs
    successifs sont la norme. Écraser le premier ferait perdre la trace de
    l'erreur d'origine, qui est souvent la seule intéressante.
    """
    base = f"{socle(NOM, DIR, date_reference)}_{SUFFIXE_INCIDENT}"
    return _premier_libre(output_dir, base, "txt")
