# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
Fonction "generer_notice_lecture"
Date : 2026-09-08
Objectif : produire un fichier .txt d'aide à la lecture des résultats de
           caractérisation des populations d'EEE, spécifique à la zone
           traitée et régénéré à chaque exécution de SPRINGE.
═══════════════════════════════════════════════════════════════════

POURQUOI CETTE NOTICE (choix structurant CS-17) :

Ajouter des colonnes ne suffit pas à rendre l'information utilisable. Trois
choses conditionnent l'interprétation et ne peuvent pas tenir dans un nom de
colonne :
  1. les DÉFINITIONS -- ce qu'est une population, pourquoi ce n'est pas une
     densité, pourquoi le nombre de points ne mesure pas une quantité de
     plantes ;
  2. les HYPOTHÈSES assumées lors du calcul ;
  3. les TAUX DE MANQUANTS de la zone effectivement traitée, qui varient d'un
     gestionnaire à l'autre et déterminent la confiance à accorder.

ARTICULATION AVEC LE DOCUMENT DE PRÉSENTATION DE L'ALGORITHME (§ 8.1 du
cadrage) :

  0_SPRINGE_presentation_algorithme.docx  |  cette notice .txt
  ----------------------------------------|---------------------------------
  Spécification de référence, stable      |  Générée à chaque exécution
  Logique des calculs, choix structurants,|  Rappel des définitions et des
  définition ET justification des seuils  |  seuils + chiffres réels de la
                                          |  zone traitée
  « Comment SPRINGE calcule, et pourquoi  |  « Comment lire MES résultats, et
    ainsi ? »                             |    quelles précautions prendre ? »

La notice ne réexplique pas la construction des indicateurs : elle rappelle ce
qu'il faut avoir en tête pour interpréter, et renvoie au document Word pour la
méthode. Les seuils y figurent parce qu'un chiffre d'avertissement est
inintelligible sans son seuil de déclenchement, mais leur JUSTIFICATION reste
dans le Word.
"""

import datetime

# Nommage centralisé (2026-09-08) : la notice suit la même trame que le
# GeoPackage, le rapport et l'incident. Voir nommer_fichiers_sortie.py.
import nommer_fichiers_sortie


# ═════════════════════════════════════════════════════════════════════════
# SEUILS DE DÉCLENCHEMENT DES AVERTISSEMENTS
#
# Principe directeur : les seuils ne sont PAS choisis à vue. Ils sont calés
# sur les taux observés dans le jeu national de référence
# (Lot_PEE_du_20240101_4especes, 8 288 populations, recensement RRN 2018-2020).
#
# L'avertissement se déclenche donc quand la zone du gestionnaire est MOINS
# BIEN RENSEIGNÉE que la référence nationale. Cette logique rend chaque seuil
# justifiable et recalculable si un jeu national plus récent devient
# disponible : il suffit de recalculer les taux et de mettre à jour ce bloc.
#
# Deux seuils échappent à cette logique et sont justifiés autrement (voir
# leurs commentaires) : l'amplitude des années et les relevés incertains.
# ═════════════════════════════════════════════════════════════════════════

SEUILS = {
    # Taux national 17,8 % de compacité non renseignée.
    'compacite_nr': 18.0,
    # Taux national 15,5 % de largeur non renseignée.
    'largeur_nr': 16.0,
    # Taux national 2,7 % de longueur non renseignée.
    'longueur_nr': 3.0,
    # Taux national 47,7 % de populations en classe Inf5m, qui contribuent
    # 0 mètre au linéaire colonisé minimum.
    'longueur_Inf5m': 48.0,
    # Taux national 26,8 % d'écarts inférieurs à 50 m, mesuré PAR TRONÇON ×
    # CATÉGORIE, c'est-à-dire de la même façon que le module de calcul.
    # Ce n'est pas le taux de non-conformité réel au protocole (14,8 % en
    # distinguant le côté de chaussée) : le contrôle par tronçon agrège les
    # deux côtés, ce qui majore. On compare ici ce qui est calculé pareil.
    'ecarts_sous_50m': 27.0,
    # Taux national 56,0 % de couples (tronçon × catégorie) à une seule
    # population, pour lesquels les descripteurs de répartition sont
    # non calculables.
    'couples_une_population': 56.0,
    # NON calé sur la référence nationale : le protocole (§ IV.4) prévoit une
    # actualisation des données tous les 4 ans. Au-delà de cette amplitude,
    # deux tronçons de la zone relèvent de campagnes différentes et ne sont
    # plus comparables à état de colonisation égal.
    'amplitude_annees': 4,
    # NON calé sur la moyenne : le taux national de relevés déclarés incertains
    # est de 0,13 % seulement (11 populations sur 8 288). Un seuil calé sur
    # cette valeur se déclencherait en permanence. On retient 1 %, au-delà
    # duquel le taux signale une pratique de saisie différente de la référence.
    'evaluation_incertaine': 1.0,
}

# Taux de référence, affichés dans la notice à côté du taux de la zone : un
# gestionnaire comprend beaucoup mieux « 24 % chez vous, 17,8 % au national »
# qu'un « 24 % » isolé.
REFERENCE_NATIONALE = {
    'compacite_nr': 17.8,
    'largeur_nr': 15.5,
    'longueur_nr': 2.7,
    'longueur_Inf5m': 47.7,
    'ecarts_sous_50m': 26.8,
    'couples_une_population': 56.0,
    'evaluation_incertaine': 0.13,
}

LARGEUR_LIGNE = 78   # largeur des séparateurs, pour un affichage lisible


def _titre(texte, caractere="="):
    """Construit un titre encadré de séparateurs, pour structurer le .txt."""
    return f"\n{caractere * LARGEUR_LIGNE}\n{texte}\n{caractere * LARGEUR_LIGNE}\n"


def _construire_avertissements(diagnostic):
    """
    Construit la liste des avertissements conditionnels applicables à la zone.

    Chaque avertissement compare une valeur du diagnostic à son seuil. Ceux
    dont le seuil n'est pas franchi ne sont pas écrits : une notice où tous
    les avertissements figurent en permanence n'est plus lue.

    Retour : liste de chaînes déjà mises en forme.
    """
    avertissements = []

    def ajouter(cle_seuil, valeur, message):
        """Ajoute l'avertissement si la valeur dépasse le seuil correspondant."""
        if valeur is None:
            return
        seuil = SEUILS[cle_seuil]
        if valeur > seuil:
            reference = REFERENCE_NATIONALE.get(cle_seuil)
            complement = (f"\n    (seuil de déclenchement : {seuil} % — "
                          f"référence nationale : {reference} %)"
                          if reference is not None else
                          f"\n    (seuil de déclenchement : {seuil})")
            avertissements.append(f"  ⚠  {message}{complement}")

    ajouter(
        'compacite_nr', diagnostic.get('taux_compacite_nr'),
        f"L'information de compacité manque pour "
        f"{diagnostic.get('taux_compacite_nr')} % des populations de votre zone.\n"
        f"    Les comptages par compacité (isolées / taches / continues) "
        f"sous-estiment\n    donc toutes les modalités à la fois."
    )

    ajouter(
        'largeur_nr', diagnostic.get('taux_largeur_nr'),
        f"{diagnostic.get('taux_largeur_nr')} % des populations n'ont pas de "
        f"classe de largeur.\n"
        f"    La classe de taille dominante est calculée sur un sous-ensemble."
    )

    ajouter(
        'longueur_nr', diagnostic.get('taux_longueur_nr'),
        f"{diagnostic.get('taux_longueur_nr')} % des populations n'ont pas de "
        f"classe de longueur\n"
        f"    et ne contribuent donc pas au linéaire colonisé minimum."
    )

    ajouter(
        'longueur_Inf5m', diagnostic.get('taux_longueur_Inf5m'),
        f"Le linéaire colonisé minimum est très en deçà de la réalité sur votre "
        f"zone :\n"
        f"    {diagnostic.get('taux_longueur_Inf5m')} % des populations y "
        f"contribuent pour 0 mètre, car leur\n"
        f"    classe de longueur (moins de 5 m) a une borne basse nulle.\n"
        f"    À lire comme un ordre de grandeur PLANCHER, jamais comme une "
        f"estimation."
    )

    ajouter(
        'ecarts_sous_50m', diagnostic.get('taux_ecarts_sous_50m'),
        f"La règle d'agrégation des 50 m du protocole n'a pas été appliquée "
        f"uniformément :\n"
        f"    {diagnostic.get('taux_ecarts_sous_50m')} % des écarts entre "
        f"populations successives de même catégorie\n"
        f"    sont inférieurs à 50 m. Le nombre de populations est donc "
        f"légèrement majoré.\n"
        f"    Ce contrôle agrège les deux côtés de chaussée et majore donc la "
        f"non-conformité\n    réelle : deux populations face à face ont des "
        f"abscisses voisines sans\n    enfreindre le protocole."
    )

    ajouter(
        'couples_une_population', diagnostic.get('taux_couples_une_population'),
        f"{diagnostic.get('taux_couples_une_population')} % des couples "
        f"(tronçon × catégorie) ne comptent qu'une population.\n"
        f"    Les descripteurs de répartition (étendue occupée, écarts) ne sont\n"
        f"    calculables que pour une minorité de vos tronçons."
    )

    ajouter(
        'evaluation_incertaine', diagnostic.get('taux_evaluation_incertaine'),
        f"{diagnostic.get('taux_evaluation_incertaine')} % des déterminations "
        f"sont signalées incertaines\n"
        f"    par l'observateur, très au-dessus de la référence nationale."
    )

    # --- Amplitude des années de relevé -----------------------------------
    # Traité à part car ce n'est pas un pourcentage mais une durée.
    annees = diagnostic.get('annees_relevees') or []
    if len(annees) >= 2:
        amplitude = max(annees) - min(annees)
        if amplitude > SEUILS['amplitude_annees']:
            avertissements.append(
                f"  ⚠  Votre zone mélange des campagnes espacées de {amplitude} ans "
                f"({min(annees)} à {max(annees)}).\n"
                f"    Deux tronçons relevés à des dates différentes ne sont pas "
                f"comparables\n    à état de colonisation égal.\n"
                f"    (seuil : {SEUILS['amplitude_annees']} ans, durée du cycle "
                f"d'actualisation prévu au § IV.4 du protocole)"
            )

    # --- Ancienneté du relevé le plus récent ------------------------------
    if annees:
        annee_courante = datetime.date.today().year
        anciennete = annee_courante - max(annees)
        if anciennete > SEUILS['amplitude_annees']:
            avertissements.append(
                f"  ⚠  Votre relevé le plus récent date de {max(annees)}, soit "
                f"{anciennete} ans.\n"
                f"    Vos données ont dépassé le cycle d'actualisation de "
                f"{SEUILS['amplitude_annees']} ans prévu\n"
                f"    par le protocole (§ IV.4)."
            )

    # --- Dates forfaitaires ------------------------------------------------
    # Pas un seuil de qualité au sens des autres, mais une information de
    # fiabilité : une date tombant le 1er du mois est souvent une date de LOT
    # attribuée à un ensemble de relevés, pas une date de terrain.
    taux_premier = diagnostic.get('taux_dates_premier_du_mois')
    if taux_premier is not None and taux_premier > 30:
        avertissements.append(
            f"  ⚠  {taux_premier} % des dates de relevé tombent un 1er du mois.\n"
            f"    C'est souvent l'indice de dates forfaitaires attribuées à un lot\n"
            f"    entier plutôt que relevées sur le terrain. Les années restent\n"
            f"    exploitables, les dates précises beaucoup moins.\n"
            f"    (à titre de comparaison, le jeu national de référence est à 55,6 %)"
        )

    return avertissements


def generer_notice_lecture(diagnostic,
                           output_dir,
                           name,
                           DIR,
                           nom_fichier_gpkg,
                           NOM="utilisateur",
                           date_reference=None,
                           liste_avertissements=None):
    """
    Génère la notice de lecture au format .txt.

    Paramètres
    ----------
    diagnostic       : dict produit par caracteriser_populations_EEE.
    output_dir       : dossier de sortie (Path ou str).
    name             : intitulé du projet, affiché dans l'en-tête.
    DIR              : structure / DIR, entre dans le nom de fichier.
    NOM              : opérateur, entre dans le nom de fichier.
    date_reference   : date de début du run, pour que tous les fichiers d'une
                       même exécution portent la même date même si le run
                       franchit minuit. Par défaut, aujourd'hui.
    nom_fichier_gpkg : nom du GeoPackage auquel cette notice se rapporte.
    liste_avertissements : liste où pousser les avertissements, ou None.

    Retour
    ------
    Chemin du fichier écrit, ou None en cas d'échec (non bloquant).
    """
    from pathlib import Path

    print(f"\n{'='*74}")
    print("GÉNÉRATION DE LA NOTICE DE LECTURE")
    print(f"{'='*74}\n")

    # NOMMAGE CENTRALISÉ (2026-09-08). Trame :
    #     SPRINGE_version202609_<opérateur>_<structure>_<date>_NOTICE.txt
    # Écrasement assumé en cas de réexécution le même jour : la notice décrit
    # le GeoPackage du jour, les deux doivent rester en phase. Contrairement au
    # rapport et à l'incident, ce n'est pas un historique.
    nom_fichier = nommer_fichiers_sortie.nom_fichier_notice(NOM, DIR, date_reference)
    chemin = Path(output_dir) / nom_fichier

    lignes = []

    # ═════════════════════════════════════════════════════════════════════
    # EN-TÊTE
    # ═════════════════════════════════════════════════════════════════════
    lignes.append("=" * LARGEUR_LIGNE)
    lignes.append("SPRINGE — NOTICE DE LECTURE")
    lignes.append("Caractérisation des populations d'espèces exotiques envahissantes")
    lignes.append("=" * LARGEUR_LIGNE)
    lignes.append("")
    lignes.append(f"  Projet        : {name}")
    lignes.append(f"  DIR           : {DIR}")
    lignes.append(f"  Généré le     : "
                  f"{datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    lignes.append(f"  Se rapporte à : {nom_fichier_gpkg}")
    lignes.append("")
    lignes.append("  Cette notice est régénérée à chaque exécution et ne vaut que pour")
    lignes.append("  les résultats ci-dessus. Pour la méthode de calcul et la")
    lignes.append("  justification des choix, voir le document de présentation de")
    lignes.append("  l'algorithme SPRINGE.")

    # ═════════════════════════════════════════════════════════════════════
    # SECTION 1 — DÉFINITIONS
    # Placée en PREMIER, avant tout chiffre : un résultat lu sans ce cadre est
    # un résultat mal lu. C'est la décision explicite du 08/09/2026.
    # ═════════════════════════════════════════════════════════════════════
    lignes.append(_titre("1. CE QUE CES DONNÉES MESURENT — À LIRE EN PREMIER"))

    lignes.append("Les résultats de cette partie de SPRINGE ne mesurent NI une densité,")
    lignes.append("NI une abondance de plantes. Ce point est la source d'erreur")
    lignes.append("d'interprétation la plus fréquente.")
    lignes.append("")
    lignes.append("--- L'unité d'observation ---")
    lignes.append("")
    lignes.append("Vos données suivent le protocole national de recensement :")
    lignes.append("")
    lignes.append("    Albert, A. (coord.) 2017. Protocole d'acquisition de données sur")
    lignes.append("    les plantes exotiques envahissantes le long du réseau routier")
    lignes.append("    national. Fédération des Conservatoires botaniques nationaux,")
    lignes.append("    Montreuil, 24 p.")
    lignes.append("    https://especes-exotiques-envahissantes.fr/wp-content/uploads/")
    lignes.append("    2023/01/fcbn-dit_eee_protocolerecensement_25072017.pdf")
    lignes.append("")
    lignes.append("Ce protocole définit l'unité d'observation par une règle de distance :")
    lignes.append("deux individus ou deux taches d'une même espèce distants de moins de")
    lignes.append("50 mètres forment UNE SEULE population. Au-delà de 50 mètres, ce sont")
    lignes.append("deux populations distinctes.")
    lignes.append("")
    lignes.append("    >>> UN POINT = UNE POPULATION, PAS UNE PLANTE. <<<")
    lignes.append("")
    lignes.append("Conséquence contre-intuitive : une forte concentration de végétation")
    lignes.append("ne produit PAS un amas de points sur la carte, mais UN SEUL point")
    lignes.append("portant des attributs de taille et de compacité élevés.")

    lignes.append("")
    lignes.append("--- Vocabulaire ---")
    lignes.append("")
    lignes.append("  Population    Ensemble d'individus d'une même espèce dont aucun")
    lignes.append("                n'est distant de plus de 50 m du suivant. C'est")
    lignes.append("                l'unité comptée par SPRINGE.")
    lignes.append("")
    lignes.append("  Abondance     Nombre d'individus. NON MESURÉE : le protocole ne")
    lignes.append("                compte pas les plantes.")
    lignes.append("")
    lignes.append("  Densité       Nombre d'individus par unité de surface. NON MESURÉE,")
    lignes.append("                et même mal définie pour les espèces à multiplication")
    lignes.append("                végétative : une grande tache de renouée peut ne")
    lignes.append("                constituer qu'un seul individu porteur de milliers")
    lignes.append("                de tiges.")
    lignes.append("")
    lignes.append("  Compacité     Structure interne d'une population : individus isolés,")
    lignes.append("                taches discontinues, ou population continue. C'est ce")
    lignes.append("                que le protocole nomme « densité des individus de la")
    lignes.append("                population ». Appréciation visuelle ordinale, PAS une")
    lignes.append("                densité numérique.")
    lignes.append("")
    lignes.append("  Ampleur       Emprise d'une population, en classes de largeur et de")
    lignes.append("                longueur. Aucune surface en m² n'est calculée : les")
    lignes.append("                classes du protocole sont ouvertes aux extrémités")
    lignes.append("                (« plus de 3 m », « plus de 20 m »), donc toute")
    lignes.append("                conversion en m² supposerait d'inventer des bornes.")
    lignes.append("")
    lignes.append("  Fréquence     Proportion d'unités où l'espèce est présente. C'est,")
    lignes.append("                avec l'ampleur et la compacité, ce que SPRINGE mesure")
    lignes.append("                réellement.")

    lignes.append("")
    lignes.append("--- Ce que SPRINGE mesure réellement ---")
    lignes.append("")
    lignes.append("  1. La FRÉQUENCE des populations : combien de foyers distincts.")
    lignes.append("  2. Leur AMPLEUR : combien de foyers par classe de largeur et de")
    lignes.append("     longueur.")
    lignes.append("  3. Leur COMPACITÉ : isolés, en taches, ou continus.")
    lignes.append("  4. Leur RÉPARTITION le long de l'axe routier.")
    lignes.append("")
    lignes.append("Deux tronçons ne peuvent donc PAS être comparés en abondance. Ils")
    lignes.append("peuvent l'être en fréquence de foyers, en ampleur de ces foyers et en")
    lignes.append("compacité.")
    lignes.append("")
    lignes.append("Un tronçon portant 1 population continue de plus de 20 m peut porter")
    lignes.append("bien plus de végétation qu'un tronçon portant 8 populations")
    lignes.append("d'individus isolés de moins de 5 m.")

    # ═════════════════════════════════════════════════════════════════════
    # SECTION 2 — HYPOTHÈSES
    # ═════════════════════════════════════════════════════════════════════
    lignes.append(_titre("2. HYPOTHÈSES ASSUMÉES PAR LE CALCUL"))

    lignes.append("Ces choix sont détaillés et justifiés dans le document de présentation")
    lignes.append("de l'algorithme. Ils sont rappelés ici parce qu'ils déterminent la")
    lignes.append("lecture des résultats.")
    lignes.append("")
    lignes.append("  • Aucun score, aucun rang, aucun adjectif de valeur n'est produit.")
    lignes.append("    Une forte colonisation n'appelle pas mécaniquement une")
    lignes.append("    intervention : selon sa stratégie, un gestionnaire peut cibler les")
    lignes.append("    foyers denses ou au contraire les petits foyers isolés en front de")
    lignes.append("    colonisation. L'outil décrit, vous décidez.")
    lignes.append("")
    lignes.append("  • Aucune valeur manquante n'est remplacée. Une largeur ou une")
    lignes.append("    compacité absente est comptée comme « non renseigné », jamais")
    lignes.append("    ramenée à une classe par défaut, ce qui déplacerait toute la")
    lignes.append("    distribution.")
    lignes.append("")
    lignes.append("  • Aucune surface en m² n'est calculée (voir « Ampleur » ci-dessus).")
    lignes.append("")
    lignes.append("  • Aucun indice statistique d'agrégation n'est calculé. La question")
    lignes.append("    « les foyers sont-ils groupés ou étalés ? » est légitime, mais le")
    lignes.append("    nombre de populations par tronçon est trop faible pour qu'un tel")
    lignes.append("    indice ait un sens. Seules des mesures brutes sont fournies")
    lignes.append("    (étendue occupée, écarts entre populations).")
    lignes.append("")
    lignes.append("  • Une population à cheval sur deux tronçons est comptée sur chacun")
    lignes.append("    d'eux : la tache existe réellement sur les deux.")

    # ═════════════════════════════════════════════════════════════════════
    # SECTION 3 — QUALITÉ DES DONNÉES DE LA ZONE
    # ═════════════════════════════════════════════════════════════════════
    lignes.append(_titre("3. QUALITÉ DES DONNÉES DE VOTRE ZONE"))

    lignes.append("  --- Couverture ---")
    lignes.append("")
    lignes.append(f"  Tronçons de la zone d'étude          : "
                  f"{diagnostic.get('nb_troncons', '?')}")
    lignes.append(f"  dont sans observation enregistrée    : "
                  f"{diagnostic.get('nb_troncons_sans_observation', '?')} "
                  f"({diagnostic.get('taux_troncons_sans_observation', '?')} %)")
    lignes.append(f"  Populations de la couche source      : "
                  f"{diagnostic.get('nb_populations_source', '?')}")
    lignes.append(f"  Populations rattachées à un tronçon  : "
                  f"{diagnostic.get('nb_populations_rattachees', '?')}")

    if diagnostic.get('nb_hors_troncon'):
        lignes.append(f"  Populations hors de tout tronçon     : "
                      f"{diagnostic['nb_hors_troncon']} (ignorées)")
    if diagnostic.get('nb_rattachements_bordure'):
        lignes.append(f"  Rattachements de bordure ajoutés     : "
                      f"{diagnostic['nb_rattachements_bordure']}")
        lignes.append("     (populations à cheval, comptées sur chacun de leurs "
                      "tronçons —")
        lignes.append("      le total par tronçon dépasse donc l'effectif de la couche)")

    lignes.append("")
    lignes.append("  --- Populations par catégorie d'EEE ---")
    lignes.append("")
    for categorie, effectif in (diagnostic.get('populations_par_categorie') or {}).items():
        lignes.append(f"  {str(categorie):<32} {effectif}")

    lignes.append("")
    lignes.append("  --- Taux de non-renseigné ---")
    lignes.append("  (entre parenthèses : le taux du jeu national de référence)")
    lignes.append("")
    for libelle, cle, cle_ref in [
        ("Largeur", 'taux_largeur_nr', 'largeur_nr'),
        ("Longueur", 'taux_longueur_nr', 'longueur_nr'),
        ("Compacité", 'taux_compacite_nr', 'compacite_nr'),
        ("Localisation sur dépendance", 'taux_localisation_nr', None),
    ]:
        valeur = diagnostic.get(cle)
        if valeur is None:
            lignes.append(f"  {libelle:<32} colonne non fournie")
        else:
            reference = REFERENCE_NATIONALE.get(cle_ref) if cle_ref else None
            suffixe = f"   (national : {reference} %)" if reference else ""
            lignes.append(f"  {libelle:<32} {valeur} %{suffixe}")

    lignes.append("")
    lignes.append("  --- Indicateurs de structure ---")
    lignes.append("")
    for libelle, cle, cle_ref in [
        ("Populations de moins de 5 m", 'taux_longueur_Inf5m', 'longueur_Inf5m'),
        ("Couples à une seule population", 'taux_couples_une_population',
         'couples_une_population'),
        ("Linéaire minimum nul", 'taux_lineaire_minimum_nul', None),
        ("Écarts inférieurs à 50 m", 'taux_ecarts_sous_50m', 'ecarts_sous_50m'),
    ]:
        valeur = diagnostic.get(cle)
        if valeur is None:
            lignes.append(f"  {libelle:<32} non calculable")
        else:
            reference = REFERENCE_NATIONALE.get(cle_ref) if cle_ref else None
            suffixe = f"   (national : {reference} %)" if reference else ""
            lignes.append(f"  {libelle:<32} {valeur} %{suffixe}")

    if diagnostic.get('nb_doublons_position') is not None:
        lignes.append(f"  {'Populations à position identique':<32} "
                      f"{diagnostic['nb_doublons_position']}")
        lignes.append("     (signalées, jamais supprimées : deux populations réelles")
        lignes.append("      peuvent être saisies au même PR, l'une sur l'accotement")
        lignes.append("      et l'autre sur le talus)")

    annees = diagnostic.get('annees_relevees') or []
    if annees:
        lignes.append("")
        lignes.append("  --- Dates de relevé ---")
        lignes.append("")
        lignes.append(f"  Années rencontrées : {min(annees)} à {max(annees)}")
        if diagnostic.get('taux_dates_premier_du_mois') is not None:
            lignes.append(f"  Dates tombant un 1er du mois : "
                          f"{diagnostic['taux_dates_premier_du_mois']} %")

    # ═════════════════════════════════════════════════════════════════════
    # SECTION 4 — AVERTISSEMENTS
    # ═════════════════════════════════════════════════════════════════════
    lignes.append(_titre("4. AVERTISSEMENTS"))

    lignes.append("--- Avertissements permanents ---")
    lignes.append("")
    lignes.append("Ces trois points valent quelle que soit la qualité de vos données.")
    lignes.append("Ils ne dépendent d'aucun seuil parce que le risque de mauvaise")
    lignes.append("lecture, lui, est permanent.")
    lignes.append("")
    lignes.append("  ⚠  Un point représente une POPULATION au sens du protocole, pas une")
    lignes.append("     plante. Un tronçon portant plus de points porte plus de foyers")
    lignes.append("     distincts, pas nécessairement plus de végétation.")
    lignes.append("")
    lignes.append("  ⚠  Un tronçon sans observation enregistrée n'est PAS un tronçon sans")
    lignes.append("     EEE. SPRINGE ne dispose d'aucune information sur la couverture de")
    lignes.append("     prospection de votre zone : rien ne permet de distinguer")
    lignes.append("     « prospecté sans résultat » de « non prospecté » ou « non")
    lignes.append("     transmis ». C'est pourquoi ces tronçons portent la mention")
    lignes.append("     « aucune observation enregistrée » et non la valeur 0.")
    lignes.append("")
    lignes.append("  ⚠  Une population à cheval sur deux tronçons est comptée sur chacun")
    lignes.append("     d'eux. Le total des populations par tronçon dépasse donc")
    lignes.append("     légèrement l'effectif de la couche source. Ce n'est pas un")
    lignes.append("     doublon, c'est une double appartenance réelle.")

    avertissements_conditionnels = _construire_avertissements(diagnostic)
    lignes.append("")
    lignes.append("--- Avertissements propres à votre zone ---")
    lignes.append("")
    if avertissements_conditionnels:
        lignes.append("Ces avertissements se déclenchent quand vos données sont moins")
        lignes.append("bien renseignées que le jeu national de référence.")
        lignes.append("")
        for avertissement in avertissements_conditionnels:
            lignes.append(avertissement)
            lignes.append("")
    else:
        lignes.append("  Aucun. Sur tous les indicateurs contrôlés, vos données sont au")
        lignes.append("  moins aussi bien renseignées que le jeu national de référence.")

    # ═════════════════════════════════════════════════════════════════════
    # SECTION 5 — CE QU'ON NE PEUT PAS CONCLURE
    # ═════════════════════════════════════════════════════════════════════
    lignes.append(_titre("5. CE QUE CES DONNÉES NE PERMETTENT PAS DE CONCLURE"))

    lignes.append("  • Comparer l'abondance de plantes entre deux tronçons. La donnée")
    lignes.append("    porte sur des populations, pas sur des individus.")
    lignes.append("")
    lignes.append("  • Calculer une densité au sens écologique, en individus par unité de")
    lignes.append("    surface.")
    lignes.append("")
    lignes.append("  • Conclure à l'absence d'EEE sur un tronçon sans observation.")
    lignes.append("")
    lignes.append("  • Qualifier statistiquement l'agencement des populations d'un")
    lignes.append("    tronçon (« agrégé », « aléatoire », « régulier »).")
    lignes.append("")
    lignes.append("  • Estimer une surface à traiter en mètres carrés.")

    # ═════════════════════════════════════════════════════════════════════
    # SECTION 6 — OÙ TROUVER QUOI
    # ═════════════════════════════════════════════════════════════════════
    lignes.append(_titre("6. OÙ TROUVER LES RÉSULTATS"))

    lignes.append("Le GeoPackage contient deux objets pour cette partie :")
    lignes.append("")
    lignes.append("  1. La couche cartographique des tronçons, enrichie de champs de")
    lignes.append("     synthèse toutes catégories confondues :")
    lignes.append("       - statut_donnee            observations enregistrées ou non")
    lignes.append("       - nb_populations_total     toutes catégories confondues")
    lignes.append("       - nb_categories_presentes  de 0 à 5")
    lignes.append("       - synthese_EEE             résumé rédigé, lisible au clic")
    lignes.append("       - annee_releve_max         relevé le plus récent")
    lignes.append("")
    lignes.append("  2. La table 'caracterisation_EEE_par_troncon_espece', sans")
    lignes.append("     géométrie, qui porte le détail : une ligne par tronçon et par")
    lignes.append("     catégorie d'EEE, avec les comptages par classe de largeur, de")
    lignes.append("     longueur et de compacité, le linéaire colonisé minimum et les")
    lignes.append("     descripteurs de répartition.")
    lignes.append("")
    lignes.append("     Pour l'utiliser dans QGIS : Couche > Ajouter une couche > Couche")
    lignes.append("     vecteur, puis jointure sur le champ 'id_troncon'.")
    lignes.append("")
    lignes.append("Le détail de chaque champ figure dans le document de présentation de")
    lignes.append("l'algorithme SPRINGE.")

    lignes.append("")
    lignes.append("=" * LARGEUR_LIGNE)
    lignes.append("Fin de la notice")
    lignes.append("=" * LARGEUR_LIGNE)

    # ═════════════════════════════════════════════════════════════════════
    # ÉCRITURE
    # ═════════════════════════════════════════════════════════════════════
    try:
        # encoding utf-8 explicite : sous Windows, l'encodage par défaut de
        # Python peut être cp1252, qui ne sait pas écrire « ⚠ » ni certains
        # caractères de séparation, et lève alors une exception.
        with open(chemin, 'w', encoding='utf-8') as fichier:
            fichier.write("\n".join(lignes))

        print(f"✔️  Notice de lecture générée : {chemin}")
        print(f"    {len(avertissements_conditionnels)} avertissement(s) "
              f"conditionnel(s) déclenché(s)")
        print(f"\n{'='*74}\n")
        return chemin

    except Exception as erreur:
        message = (f"Notice de lecture : génération échouée — "
                   f"{str(erreur)[:150]}")
        print(f"⚠️  {message}")
        if liste_avertissements is not None:
            liste_avertissements.append(message)
        return None
