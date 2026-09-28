# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
Fonction "calculer_seuil_tmja"
Date : 2026-09-28 (version 26.9.0)
Objectif : calculer UNE SEULE FOIS le seuil de « fort trafic » utilisé
           par les deux indicateurs qui mobilisent le TMJA : MS1b et P2.
═══════════════════════════════════════════════════════════════════

POURQUOI UN MODULE DÉDIÉ :
    Avant cette version, chaque indicateur avait son propre seuil :
        - MS1b : seuil fixe écrit en dur dans le lanceur (22 650 véh/j) ;
        - P2   : troisième quartile (Q3) recalculé à l'intérieur de
                 calculer_P2_impact.
    Deux seuils différents pour une même notion (« fort trafic ») rendaient
    les deux indicateurs incohérents entre eux. Décision de septembre 2026 :
    le mode Q3 s'applique PARTOUT. Pour garantir que MS1b et P2 utilisent
    strictement la même valeur, on la calcule ici, une seule fois, et le
    lanceur la transmet aux deux indicateurs.

POURQUOI LE TROISIÈME QUARTILE (Q3) PLUTÔT QU'UN SEUIL FIXE :
    Un seuil fixe (ex. 10 000 véh/j) est inadapté à des réseaux contrastés :
        - DIR rurale (trafic max ~8 000 véh/j) : aucun tronçon ne franchit
          10 000 → le bonus n'est jamais attribué ;
        - DIR périurbaine (trafic max ~30 000 véh/j) : la majorité des
          tronçons dépasse 10 000 → le bonus devient la norme et ne
          distingue plus rien.
    Le Q3 est la valeur sous laquelle se trouvent 75 % des valeurs de TMJA
    de la zone traitée. Retenir « TMJA > Q3 » revient à désigner comme
    « fort trafic » environ le quart des sections les plus chargées de la
    zone, quel que soit le niveau général de trafic du réseau.

LIMITE ASSUMÉE (à rappeler dans le document de présentation) :
    Le seuil est RELATIF à la zone traitée. Deux exécutions sur deux zones
    différentes n'ont donc pas le même seuil : un « fort trafic » en DIR
    rurale peut être un trafic moyen en DIR périurbaine. Le seuil retenu est
    écrit dans le rapport d'exécution pour que ce soit traçable.

SUR QUELLES VALEURS LE Q3 EST CALCULÉ :
    Sur les valeurs de TMJA des entités de la couche TMJA fournie, telle que
    chargée par le lanceur, c'est-à-dire DÉJÀ recadrée sur l'emprise de la
    zone d'étude (charger_couches_sig.charger_couches_utilisateur reçoit
    l'emprise). Les valeurs vides ou non numériques (« ND », « NA »...) sont
    écartées avant le calcul.

SORTIE :
    Un dictionnaire (ou None si le seuil n'est pas calculable) :
        {
          'colonne'    : nom de la colonne TMJA utilisée,
          'seuil'      : valeur du Q3 (float), en véh/j,
          'q1', 'q2', 'q3', 'p95', 'min', 'max' : statistiques descriptives,
          'nb_valeurs' : nombre de valeurs numériques exploitées,
        }
    Renvoyer None plutôt que lever une erreur permet au lanceur de
    neutraliser proprement MS1b et le bonus TMJA de P2 (score à 0) sans
    interrompre SPRINGE.
"""

import pandas as pd


# ═════════════════════════════════════════════════════════════════════
# CONSTANTE DU MODULE
# ═════════════════════════════════════════════════════════════════════
# Quantile retenu comme seuil de fort trafic. 0.75 = troisième quartile.
# Regroupé ici pour être modifiable en un seul endroit si la méthode
# évolue (ex. 0.70 pour « les 30 % de tronçons les plus fréquentés »).
QUANTILE_SEUIL_TMJA = 0.75

# Fragments de nom qui signalent une colonne de trafic. La comparaison se
# fait en minuscules, donc 'TMJA', 'Tmja_2023', 'trafic_moyen' sont tous
# reconnus. On cherche d'abord une colonne nommée EXACTEMENT 'tmja' (cas
# des données SI ROUTE), puis une colonne CONTENANT l'un de ces fragments.
FRAGMENTS_NOM_TMJA = ('tmja', 'trafic', 'traffic')


def detecter_colonne_tmja(gdf_tmja):
    """
    Identifie la colonne qui porte les valeurs de trafic dans la couche TMJA.

    Paramètre :
        gdf_tmja : GeoDataFrame de la couche TMJA.

    Retour :
        le nom de la colonne (str), ou None si aucune colonne ne convient.

    Principe : on privilégie le nom exact 'tmja' (convention SI ROUTE,
    c'était la seule colonne acceptée par l'ancien MS1b). À défaut, on
    prend la première colonne dont le nom contient un fragment de
    FRAGMENTS_NOM_TMJA (c'était la logique de l'ancien P2). Réunir les deux
    logiques ici garantit que MS1b et P2 lisent la MÊME colonne.
    """
    # Liste des colonnes hors géométrie : la géométrie ne peut pas porter
    # de valeur de trafic, inutile de la tester.
    colonnes = [c for c in gdf_tmja.columns if c != 'geometry']

    # 1er essai : nom exact 'tmja' (insensible à la casse).
    for c in colonnes:
        if c.lower() == 'tmja':
            return c

    # 2e essai : nom contenant un des fragments attendus.
    # any(...) renvoie True dès qu'un fragment est trouvé dans le nom.
    for c in colonnes:
        if any(fragment in c.lower() for fragment in FRAGMENTS_NOM_TMJA):
            return c

    # Aucune colonne reconnue : on laisse l'appelant décider quoi faire.
    return None


def calculer_seuil_tmja_q3(gdf_tmja, liste_avertissements=None):
    """
    Calcule le seuil de fort trafic (Q3 des valeurs de TMJA de la zone).

    Paramètres :
        gdf_tmja : GeoDataFrame TMJA, ou None si l'utilisateur n'a pas
                   fourni de données de trafic.
        liste_avertissements : liste (ex. _WARNINGS_SPRINGE) où écrire une
                   ligne de traçabilité ; si None, on se contente d'afficher.

    Retour :
        dict décrit dans l'en-tête du module, ou None si non calculable.
    """
    print(f"\n{'='*70}")
    print("SEUIL TMJA « FORT TRAFIC » (commun à MS1b et P2)")
    print(f"{'='*70}")

    # ── Cas 1 : pas de couche TMJA du tout ───────────────────────────
    # Le TMJA est une donnée optionnelle : son absence n'est pas une
    # erreur. Les indicateurs concernés seront simplement neutralisés.
    if gdf_tmja is None:
        print("   ℹ️  Aucune couche TMJA fournie → pas de seuil (MS1b et bonus P2 neutralisés).")
        return None

    # ── Cas 2 : couche fournie, mais aucune colonne de trafic reconnue ──
    col_tmja = detecter_colonne_tmja(gdf_tmja)
    if col_tmja is None:
        message = ("Seuil TMJA non calculé : aucune colonne de trafic reconnue "
                   "dans la couche TMJA (nom attendu : 'tmja', ou contenant "
                   "'tmja' / 'trafic'). MS1b et bonus TMJA de P2 neutralisés.")
        print(f"   ⚠️  {message}")
        if liste_avertissements is not None:
            liste_avertissements.append(message)
        return None

    # ── Conversion en nombres ─────────────────────────────────────────
    # pd.to_numeric(..., errors='coerce') transforme en NaN toute valeur
    # non numérique ('ND', 'NA', chaîne vide...), au lieu de planter.
    # .dropna() retire ensuite ces NaN : ils ne doivent pas peser sur le
    # calcul du quartile.
    valeurs = pd.to_numeric(gdf_tmja[col_tmja], errors='coerce').dropna()

    # ── Cas 3 : colonne trouvée, mais aucune valeur exploitable ───────
    if len(valeurs) == 0:
        message = (f"Seuil TMJA non calculé : la colonne '{col_tmja}' ne contient "
                   "aucune valeur numérique. MS1b et bonus TMJA de P2 neutralisés.")
        print(f"   ⚠️  {message}")
        if liste_avertissements is not None:
            liste_avertissements.append(message)
        return None

    # ── Cas nominal : calcul des statistiques ─────────────────────────
    # .quantile(q) renvoie la valeur sous laquelle se trouve la proportion
    # q des valeurs. Seul Q3 sert de seuil ; les autres quantiles sont
    # calculés uniquement pour l'affichage console, afin que l'utilisateur
    # voie où se situe le seuil dans la distribution de SA zone.
    infos = {
        'colonne':    col_tmja,
        'q1':         float(valeurs.quantile(0.25)),
        'q2':         float(valeurs.quantile(0.50)),   # médiane
        'q3':         float(valeurs.quantile(QUANTILE_SEUIL_TMJA)),
        'p95':        float(valeurs.quantile(0.95)),
        'min':        float(valeurs.min()),
        'max':        float(valeurs.max()),
        'nb_valeurs': int(len(valeurs)),
    }
    # Le seuil EST le Q3 : on le range sous une clé explicite pour que le
    # code appelant n'ait pas à savoir quelle méthode a été utilisée.
    infos['seuil'] = infos['q3']

    # ── Affichage console ─────────────────────────────────────────────
    # {x:>8.0f} : nombre aligné à droite sur 8 caractères, sans décimale.
    print(f"   • Colonne TMJA utilisée : '{col_tmja}'")
    print(f"   • Valeurs exploitées    : {infos['nb_valeurs']}")
    print(f"   • Min                   : {infos['min']:>8.0f} véh/j")
    print(f"   • Q1 (25e percentile)   : {infos['q1']:>8.0f} véh/j")
    print(f"   • Médiane               : {infos['q2']:>8.0f} véh/j")
    print(f"   • Q3 (75e percentile)   : {infos['q3']:>8.0f} véh/j  ← SEUIL")
    print(f"   • 95e percentile        : {infos['p95']:>8.0f} véh/j")
    print(f"   • Max                   : {infos['max']:>8.0f} véh/j")

    # ── Cas limite : distribution plate ───────────────────────────────
    # La règle est « TMJA STRICTEMENT supérieur au seuil ». Si Q3 est égal
    # au maximum (beaucoup de valeurs identiques en haut de distribution),
    # aucune section ne le dépasse et le bonus ne sera jamais attribué.
    # On le signale : ce n'est pas une erreur, mais le résultat surprendrait.
    if infos['q3'] >= infos['max']:
        message = (f"Seuil TMJA (Q3 = {infos['q3']:.0f} véh/j) égal au maximum de la "
                   "zone : aucune section ne le dépasse strictement, MS1b et le "
                   "bonus TMJA de P2 ne seront attribués à aucun tronçon.")
        print(f"   ⚠️  {message}")
        if liste_avertissements is not None:
            liste_avertissements.append(message)

    # ── Traçabilité dans le rapport d'exécution ───────────────────────
    # Le seuil change d'une zone à l'autre : il doit figurer dans le
    # rapport pour que les résultats de MS1b et P2 restent interprétables.
    # Le rapport n'a qu'une rubrique « avertissements » : on y écrit cette
    # ligne d'information, rédigée pour ne pas être lue comme une anomalie.
    if liste_avertissements is not None:
        liste_avertissements.append(
            f"Information — seuil « fort trafic » commun à MS1b et P2 : "
            f"Q3 des valeurs TMJA de la zone = {infos['seuil']:.0f} véh/j "
            f"(colonne '{col_tmja}', {infos['nb_valeurs']} valeurs)."
        )

    print(f"{'='*70}\n")
    return infos
