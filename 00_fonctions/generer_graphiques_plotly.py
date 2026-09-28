# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
Module : generer_graphiques_plotly.py
Projet : SPRINGE (Système de PRiorisation des INterventions de Gestion des EEE)
Version : septembre 2026
═══════════════════════════════════════════════════════════════════════════════

OBJECTIF
--------
Produire UN SEUL fichier HTML interactif et autonome, qui présente les
résultats de SPRINGE dans l'ordre des questions que se pose un gestionnaire
au moment de décider où intervenir :

    1. AMPLEUR      — y a-t-il un problème, avec quelle espèce, à quel volume ?
    2. ENJEUX       — sur quel enjeu mon réseau se distingue-t-il ?
    3. RECOUVREMENT — le choix de l'enjeu change-t-il la liste des tronçons ?
    4. NUAGE        — score et ampleur, tronçon par tronçon
    5. POPULATIONS  — quelle forme prennent les foyers sur le terrain ?

L'ordre suit la décision, pas la structure du calcul. Il n'y a volontairement
aucun graphique par indicateur (MS1, MS2... P4) : à cette échelle, une
distribution de notes 0-5 ne se traduit pas en choix de gestion.

PRINCIPE DE CONCEPTION REPRIS DU RESTE DE SPRINGE
-------------------------------------------------
Les graphiques DÉCRIVENT le réseau, ils ne priorisent pas à la place du
gestionnaire. Concrètement, dans tout ce fichier :
  - on écrit « tronçons dont le score est le plus élevé », jamais « tronçons
    prioritaires » ni « les mieux notés » ;
  - aucun quadrant, aucune zone du nuage n'est étiquetée « à traiter » ;
  - les seuils affichés sur le nuage sont des faits arithmétiques de cumul
    d'enjeux (voir _seuils_cumul), pas des recommandations d'action.

DEUX NIVEAUX DE TEXTE
---------------------
  - DANS la figure (donc dans le SVG téléchargé) : titre, sous-titre de
    périmètre, note de lecture condensée, ligne de traçabilité. La figure
    reste ainsi compréhensible seule, une fois collée dans un rapport Word.
  - AUTOUR de la figure, dans la page HTML : le texte pédagogique long — ce
    que le graphique montre, comment le lire, ce qu'il ne dit pas.
La redondance entre les deux niveaux est assumée : ce sont deux usages.

AUTONOMIE DU FICHIER
--------------------
La bibliothèque JavaScript de Plotly est EMBARQUÉE dans le fichier (elle est
incluse une seule fois, avec la première figure). La page pèse de ce fait
environ 3 à 4 Mo, mais s'ouvre sans accès internet — indispensable sur un
poste DIR ou sur une page transmise par clé USB.

EXPORT DES FIGURES
------------------
Chaque figure porte un bouton « Télécharger cette figure (SVG) ». L'export est
fait par Plotly côté navigateur, en JavaScript : aucune dépendance Python
supplémentaire (pas de `kaleido` à installer dans l'environnement QGIS).

COMPATIBILITÉ
-------------
Écrit avec `plotly.graph_objects` uniquement, sans `plotly.express`, pour
rester compatible des versions 5.x comme 6.x/7.x de Plotly.
"""

import datetime
import html as html_module
from pathlib import Path

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ═══════════════════════════════════════════════════════════════════════════
# 1. CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════

# ── Enjeux ─────────────────────────────────────────────────────────────────
# Une couleur par enjeu, tenue à l'identique dans TOUTES les figures : c'est
# ce qui permet au lecteur de relier deux graphiques sans relire la légende.
COULEURS_ENJEUX = {
    "MS": "#C1440E",   # Maintenance et sécurité — terre de Sienne
    "N":  "#2E6E4E",   # Protection des milieux naturels — vert forêt
    "P":  "#1F4E79",   # Propagation             — bleu profond
}

# Les sigles MS / N / P ne parlent qu'aux personnes déjà formées à SPRINGE :
# on affiche systématiquement le libellé développé.
LIBELLES_ENJEUX = {
    "MS": "Maintenance et sécurité",
    # CORRIGÉ 2026-09-28 : « Naturalité » remplacé par le libellé officiel de
    # l'enjeu, celui du document de présentation de l'algorithme (1.3).
    "N":  "Protection des milieux naturels",
    "P":  "Propagation",
}

# ── Couleurs neutres ───────────────────────────────────────────────────────
COULEUR_NEUTRE       = "#5B6770"   # gris ardoise — barres sans code couleur
COULEUR_NEUTRE_CLAIR = "#C8CDD1"   # gris clair   — « absence », fond de barre
COULEUR_ACCENT       = "#B00020"   # rouge        — repères statistiques
COULEUR_TEXTE        = "#2B3238"
COULEUR_TEXTE_DOUX   = "#6B747C"

# ── Maxima théoriques par indicateur ───────────────────────────────────────
# CORRIGÉ 2026-09-28.
# AVANT : un maximum forfaitaire PAR ENJEU (5 par indicateur MS et N, 4 par
# indicateur P), multiplié par le nombre de colonnes *_impact détectées.
# Problème : les indicateurs « bonus » (MS1b, P1 notés 0/1 ; P3 noté 0/1/2)
# étaient comptés comme des indicateurs pleins. Résultat affiché : MS = 20,
# P = 16, total = 46, alors que le barème documenté est MS = 16, N = 10,
# P = 12, total = 38 (document de présentation, 2.1.1 et section 4).
#
# MAINTENANT : un maximum PAR INDICATEUR, repris du barème de chaque
# fonction calculer_XX_impact. Le maximum d'un enjeu est la SOMME des maxima
# de ses indicateurs présents dans df_scoring. Un indicateur neutralisé dont
# la colonne existe (0 partout) compte quand même : c'est le barème qui est
# décrit, pas la valeur atteinte sur la zone.
MAX_PAR_COLONNE = {
    "MS1_impact":  5,   # grille 0-5
    "MS1b_impact": 1,   # bonus trafic 0/+1
    "MS2_impact":  5,   # grille 0-5
    "MS3_impact":  5,   # grille 0-5
    "N1_impact":   5,   # grille 0-5
    "N2_impact":   5,   # grille 0-5
    "P1_impact":   1,   # bonus potentiel invasif 0/+1
    "P2_impact":   5,   # cumul de bonus plafonné à 5
    "P3_impact":   2,   # bonus 0/+1/+2
    "P4_impact":   4,   # grille 0-4
}

# Valeur de repli pour une colonne *_impact absente du dictionnaire (nouvel
# indicateur ajouté plus tard sans mise à jour de ce module). 5 = échelle
# standard des indicateurs principaux. Un message console signale l'oubli.
MAX_PAR_DEFAUT = 5

# ── Seuils de cumul d'enjeux ───────────────────────────────────────────────
# CORRIGÉ 2026-09-28 : les bornes ne sont plus écrites en dur (16 / 31 / 41,
# calculées sur l'ancien barème faux). Elles sont DÉDUITES des maxima par la
# fonction _seuils_cumul(maxima), plus bas. Raisonnement, inchangé :
#
#   - L'enjeu le plus lourd plafonne à M1 points (MS = 16 avec le barème
#     actuel). Jusqu'à M1, un seul enjeu peut expliquer tout le score.
#   - Les DEUX enjeux les plus lourds réunis plafonnent à M1 + M2 (MS 16 +
#     P 12 = 28). Au-delà de M1, aucun enjeu seul ne suffit : au moins deux
#     enjeux sont NÉCESSAIREMENT engagés.
#   - Au-delà de M1 + M2, les trois enjeux sont NÉCESSAIREMENT engagés
#     (jusqu'au total, 38).
#
# Ce sont des garanties de cumul, démontrables sur le barème. Les libellés
# relèvent d'une interprétation métier assumée ; la note de lecture du nuage
# rappelle toujours le fait arithmétique sous-jacent.
HABILLAGE_CUMUL = [
    {
        "libelle": "Pas de problématique apparente",
        "fait": "aucun cumul garanti — un seul enjeu peut expliquer tout le score",
        "couleur": "#F2F5F3",
    },
    {
        "libelle": "Problématique potentielle",
        "fait": "cumul d'au moins 2 enjeux garanti",
        "couleur": "#FDF0E4",
    },
    {
        "libelle": "Problématique avérée",
        "fait": "cumul des 3 enjeux garanti",
        "couleur": "#F7DFD8",
    },
]


def _seuils_cumul(maxima):
    """
    Construit les trois bandes de cumul à partir des maxima par enjeu.

    Paramètre : maxima = {"MS": 16, "N": 10, "P": 12} (sortie de
    _calculer_maxima).
    Retour : liste de dicts {min, max, libelle, fait, couleur}, même format
    que l'ancienne constante SEUILS_CUMUL : le code du nuage garde sa logique.

    Les scores étant entiers, chaque bande commence à « borne précédente + 1 ».
    """
    # Maxima rangés du plus grand au plus petit ; complétés par des 0 pour
    # que m1 et m2 existent même si un enjeu manque (run partiel).
    valeurs = sorted(maxima.values(), reverse=True) + [0, 0]
    m1, m2 = valeurs[0], valeurs[1]
    total = sum(maxima.values())
    bornes = [(0, m1), (m1 + 1, m1 + m2), (m1 + m2 + 1, total)]
    # zip associe chaque couple de bornes à son habillage (libellé, couleur).
    # Une bande vide (min > max, si un enjeu vaut 0) est ignorée.
    return [dict(min=lo, max=hi, **habillage)
            for (lo, hi), habillage in zip(bornes, HABILLAGE_CUMUL)
            if lo <= hi]


# ── Catégories d'EEE ───────────────────────────────────────────────────────
# Reprise à l'identique de `caracteriser_populations_EEE.CATEGORIES_SPRINGE`.
# Dupliquée ici plutôt qu'importée pour que le module graphiques reste
# utilisable même si la caractérisation n'a pas été activée sur le run.
LIBELLES_CATEGORIES = {
    "Reynoutria sp":            "Renouées",
    "Reynoutria sp.":           "Renouées",
    "Ailanthus altissima":      "Ailante",
    "Ambrosia artemisiifolia":  "Ambroisie",
    "Heracleum mantegazzianum": "Berce du Caucase",
    "EEE autre":                "EEE autre",
}

# ── Compacité des populations ──────────────────────────────────────────────
# Ordre imposé, du plus diffus au plus compact. Sans cet ordre, pandas range
# les modalités alphabétiquement (Continue, Isoles, Taches), ce qui casse la
# progression que le lecteur attend dans une barre empilée.
ORDRE_COMPACITE = ["Isoles", "Taches", "Continue", "nr"]

LIBELLES_COMPACITE = {
    "Isoles":   "Individus isolés",
    "Taches":   "Taches discontinues",
    "Continue": "Population continue",
    "nr":       "Compacité non renseignée",
}

COULEURS_COMPACITE = {
    "Isoles":   "#9DC6A0",
    "Taches":   "#4E9A6B",
    "Continue": "#1D5232",
    "nr":       "#C8CDD1",
}

# Colonnes de `df_caracterisation` portant le comptage de populations par
# classe de compacité. Noms repris de la table longue produite par
# `caracteriser_populations_EEE` (étape 6).
COLONNES_COMPACITE = {
    "Isoles":   "nb_pop_isolees",
    "Taches":   "nb_pop_taches",
    "Continue": "nb_pop_continues",
    "nr":       "nb_pop_compacite_nr",
}

# ── Part du réseau retenue pour l'analyse de recouvrement ──────────────────
# 10 % : valeur validée. Elle définit, pour chaque enjeu, le sous-ensemble des
# tronçons dont le score est le plus élevé. Le seuil n'a pas de signification
# écologique, c'est une convention de lecture — la note le dit explicitement.
PART_TETE_DE_CLASSEMENT = 0.10

# ── Mise en forme commune des figures ──────────────────────────────────────
POLICE = "Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"

# Dimensions de l'image exportée quand l'utilisateur clique sur le bouton de
# téléchargement. Fixées ici pour que TOUTES les figures d'un même rapport
# aient la même largeur, quelle que soit la taille de la fenêtre au moment du
# clic. 1200 px de large correspond à une pleine largeur de page A4.
EXPORT_LARGEUR = 1200
EXPORT_HAUTEUR = 700


# ═══════════════════════════════════════════════════════════════════════════
# 2. UTILITAIRES DE MISE EN FORME
# ═══════════════════════════════════════════════════════════════════════════

def _nb(valeur):
    """
    Met en forme un entier à la française : séparateur de milliers par espace
    fine insécable (1 234), et non par virgule comme le fait Python.
    """
    try:
        return f"{int(valeur):,}".replace(",", "\u202f")
    except (TypeError, ValueError):
        return "—"


def _pc(valeur, decimales=1):
    """Met en forme un pourcentage, avec la virgule décimale française."""
    if valeur is None or (isinstance(valeur, float) and np.isnan(valeur)):
        return "—"
    return f"{valeur:.{decimales}f}".replace(".", ",") + " %"


def _dec(valeur, decimales=2):
    """Met en forme un nombre décimal avec la virgule française."""
    if valeur is None or (isinstance(valeur, float) and np.isnan(valeur)):
        return "—"
    return f"{valeur:.{decimales}f}".replace(".", ",")


def _libelle_categorie(nom_scientifique):
    """
    Traduit un `species_name_sci` en libellé lisible (« Renouées » plutôt que
    « Reynoutria sp »). Repli sur le nom d'origine si la catégorie est
    inconnue : mieux vaut afficher un nom scientifique qu'une case vide.
    """
    return LIBELLES_CATEGORIES.get(str(nom_scientifique), str(nom_scientifique))


def _echapper(texte):
    """
    Neutralise les caractères spéciaux HTML (`<`, `&`, `"`...) avant insertion
    dans la page. Sans cela, un nom de projet contenant une esperluette ou un
    chevron casserait silencieusement la structure du document.
    """
    return html_module.escape(str(texte if texte is not None else ""))


def _construire_pied(name, DIR, NOM, date_reference, version_springe):
    """
    Construit la ligne de traçabilité, reprise à la fois en pied de chaque
    figure (donc dans le SVG exporté) et en pied de page HTML.

    Objectif : qu'une figure extraite du rapport, transmise par mail ou
    retrouvée deux ans plus tard, reste rattachable à une exécution précise.
    """
    # On accepte un datetime (cas normal, `_DATE_DEBUT_SPRINGE`) comme une
    # chaîne déjà mise en forme, par souplesse si le lanceur évolue.
    if isinstance(date_reference, (datetime.datetime, datetime.date)):
        date_txt = date_reference.strftime("%d/%m/%Y à %H:%M")
    elif date_reference is None:
        date_txt = "date non renseignée"
    else:
        date_txt = str(date_reference)

    outil = "SPRINGE" if not version_springe else f"SPRINGE v{version_springe}"

    # Les éléments non renseignés sont retirés plutôt que laissés vides : sans
    # ce filtrage, un DIR absent produirait un séparateur orphelin « — — ».
    elements = [
        f"Graphique issu de {outil}, exécuté le {date_txt}",
        f"DIR {DIR}" if DIR else None,
        f"projet « {name} »" if name else None,
        f"opérateur : {NOM}" if NOM else None,
    ]
    return "   |   ".join([e for e in elements if e])


def _envelopper(texte, largeur=145):
    """
    Coupe un texte en lignes de longueur maîtrisée, séparées par des <br>.

    POURQUOI CETTE FONCTION EXISTE : contrairement au HTML, une annotation
    Plotly ne revient JAMAIS à la ligne toute seule. Une note de lecture de
    trois phrases s'afficherait donc sur une seule ligne, qui déborderait
    largement de la figure et serait tronquée à l'export.

    Les <br> déjà présents dans le texte sont respectés comme des sauts de
    paragraphe : chaque bloc est enveloppé séparément.
    """
    import textwrap

    lignes = []
    for bloc in str(texte).split("<br>"):
        bloc = bloc.strip()
        if not bloc:
            continue
        # `break_long_words=False` : on ne coupe jamais un mot en deux, quitte
        # à dépasser légèrement la largeur cible sur un nom scientifique long.
        lignes.extend(textwrap.wrap(bloc, width=largeur,
                                    break_long_words=False) or [""])
    return lignes


def _habiller_figure(fig, titre, sous_titre, note_lecture, pied,
                     hauteur=560, marge_basse=150, marge_gauche=80):
    """
    Applique à une figure Plotly l'habillage textuel qui la rend autonome une
    fois exportée en SVG.

    Trois niveaux de texte sont inscrits DANS la figure :
      - le titre, en gras, et le sous-titre de périmètre juste en dessous ;
      - la note de lecture, condensée, sous la zone de tracé ;
      - la ligne de traçabilité, tout en bas, en petit.

    Paramètres de mise en page
    --------------------------
    hauteur : int
        Hauteur souhaitée de la figure en pixels. Elle est AUGMENTÉE
        automatiquement si la note de lecture occupe plus de place que la
        marge basse demandée : la zone de tracé conserve ainsi sa taille au
        lieu d'être écrasée par le texte.
    marge_basse : int
        Marge basse minimale en pixels. La valeur réellement appliquée est le
        maximum entre cette valeur et la place nécessaire au texte.

    Note technique : les annotations utilisent `xref="paper"` et
    `yref="paper"`, c'est-à-dire des coordonnées relatives à la ZONE DE TRACÉ
    (0 = bord bas/gauche, 1 = bord haut/droit) et non aux données. Elles
    restent donc en place quels que soient le zoom et les valeurs tracées.
    """
    # ── Titre et sous-titre ──
    # Plotly n'a qu'un seul champ de titre : le sous-titre est ajouté sur une
    # seconde ligne via une balise <br>, avec une taille et une couleur
    # réduites par un <span> (Plotly interprète un HTML minimal).
    titre_complet = f"<b>{titre}</b>"
    if sous_titre:
        for i, ligne in enumerate(_envelopper(sous_titre, 120)):
            balise = "<br>" if i == 0 else "<br>"
            titre_complet += (
                f"{balise}<span style='font-size:13px;"
                f"color:{COULEUR_TEXTE_DOUX}'>{ligne}</span>"
            )
    # Chaque ligne de sous-titre pousse la zone de tracé vers le bas.
    nb_lignes_sous_titre = len(_envelopper(sous_titre, 120)) if sous_titre else 0
    marge_haute = 60 + 20 * nb_lignes_sous_titre

    # ── Calcul de la place nécessaire en bas ──
    # De bas en haut : le titre de l'axe des abscisses (~45 px), puis la note
    # de lecture (16 px par ligne), puis la ligne de traçabilité (~26 px).
    lignes_note = _envelopper(note_lecture) if note_lecture else []
    hauteur_note = 16 * len(lignes_note)
    marge_necessaire = 45 + hauteur_note + 30
    marge_reelle = max(marge_basse, marge_necessaire)

    # Si la note demande plus de place que prévu, on agrandit la figure au
    # lieu de rogner le graphique.
    hauteur_reelle = hauteur + max(0, marge_reelle - marge_basse)

    # Hauteur de la seule zone de tracé, qui sert de référence aux
    # coordonnées "paper" : y = -50/zone_tracee signifie 50 px sous l'axe.
    zone_tracee = max(hauteur_reelle - marge_haute - marge_reelle, 1)

    annotations = list(fig.layout.annotations or ())

    if lignes_note:
        annotations.append(dict(
            text="<br>".join(lignes_note),
            xref="paper", yref="paper",
            x=0, y=-45 / zone_tracee,
            xanchor="left", yanchor="top",
            showarrow=False, align="left",
            font=dict(size=11.5, color="#4A5259", family=POLICE),
        ))

    if pied:
        annotations.append(dict(
            text=pied,
            xref="paper", yref="paper",
            x=0, y=-(45 + hauteur_note + 14) / zone_tracee,
            xanchor="left", yanchor="top",
            showarrow=False,
            font=dict(size=9.5, color="#9AA3AA", family=POLICE),
        ))

    fig.update_layout(
        title=dict(text=titre_complet, x=0, xanchor="left",
                   font=dict(size=17, color=COULEUR_TEXTE, family=POLICE)),
        annotations=annotations,
        height=hauteur_reelle,
        margin=dict(l=marge_gauche, r=40, t=marge_haute, b=marge_reelle),
        # Fond blanc explicite : par défaut Plotly produit un fond
        # transparent, dont le rendu devient imprévisible sur une diapositive
        # ou une page de rapport à fond coloré.
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family=POLICE, size=12, color=COULEUR_TEXTE),
        # `hovermode="closest"` : l'infobulle suit le point le plus proche du
        # curseur, comportement attendu sur un nuage de points.
        hovermode="closest",
    )
    return fig


def _style_axes(fig, grille_x=False, grille_y=True):
    """
    Applique le style d'axes commun : pas de cadre, grille discrète sur le
    seul axe des valeurs. Moins d'encre pour la même information.
    """
    fig.update_xaxes(
        showgrid=grille_x, gridcolor="#E8EAEC", zeroline=False,
        linecolor="#B8BEC3", ticks="outside", tickcolor="#B8BEC3",
    )
    fig.update_yaxes(
        showgrid=grille_y, gridcolor="#E8EAEC", zeroline=False,
        linecolor="#B8BEC3", ticks="outside", tickcolor="#B8BEC3",
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# 3. PRÉPARATION DES DONNÉES
# ═══════════════════════════════════════════════════════════════════════════

def _colonnes_impact_par_enjeu(df_scoring):
    """
    Regroupe les colonnes `*_impact` par enjeu, selon la même détection par
    préfixe que `calculer_score_final.py`.

    L'enchaînement `if / elif` garantit qu'une colonne ne peut pas être
    comptée dans deux enjeux à la fois si de nouveaux préfixes apparaissent.
    """
    colonnes = [c for c in df_scoring.columns if c.endswith("_impact")]
    groupes = {"MS": [], "N": [], "P": []}
    for col in colonnes:
        if col.startswith("MS"):
            groupes["MS"].append(col)
        elif col.startswith("N"):
            groupes["N"].append(col)
        elif col.startswith("P"):
            groupes["P"].append(col)
    return groupes


def _calculer_maxima(df_scoring, maxima_forces=None):
    """
    Calcule le score maximal atteignable par enjeu.

    Indispensable pour comparer MS, N et P : ces enjeux n'ont ni le même
    nombre d'indicateurs ni la même échelle. Comparer leurs scores bruts
    reviendrait à comparer des mètres et des kilos. On rapporte chaque score à
    son maximum pour obtenir un taux de saturation, lui comparable.
    """
    if maxima_forces:
        return dict(maxima_forces)
    groupes = _colonnes_impact_par_enjeu(df_scoring)
    maxima = {}
    for enjeu, colonnes in groupes.items():
        total = 0
        for col in colonnes:
            # .get(col) renvoie None si la colonne n'est pas au barème connu.
            maxi = MAX_PAR_COLONNE.get(col)
            if maxi is None:
                print(f"  ⚠️  Colonne '{col}' absente du barème MAX_PAR_COLONNE : "
                      f"maximum supposé à {MAX_PAR_DEFAUT}. Mettre à jour le module.")
                maxi = MAX_PAR_DEFAUT
            total += maxi
        maxima[enjeu] = total
    return maxima


def _agreger_caracterisation(df_caracterisation, colonne_id):
    """
    Réduit la table longue de caractérisation (une ligne par couple
    tronçon × catégorie) à UNE ligne par tronçon.

    Trois informations en sortie :
      - `lineaire_colonise_total_m` : somme du linéaire colonisé minimum,
        toutes catégories confondues ;
      - `nb_populations_carac`      : nombre total de populations ;
      - `compacite_dominante`       : classe de compacité la plus représentée
        sur le tronçon, en nombre de populations.

    Renvoie None si la table est absente ou inexploitable — les figures qui
    en dépendent se rabattent alors sur les champs de synthèse de df_scoring.

    ⚠️ Rappel de sémantique : `lineaire_colonise_minimum_m` est un MINORANT,
    pas une estimation. Les classes de longueur du protocole sont ouvertes
    vers le haut ('Sup20m'), donc seule la borne basse est garantie. Une
    population de classe 'Inf5m' contribue 0 mètre. Ce point est rappelé dans
    les notes de lecture de toutes les figures qui utilisent ce champ.
    """
    if df_caracterisation is None or len(df_caracterisation) == 0:
        return None
    if "id_troncon" not in df_caracterisation.columns:
        return None

    df = df_caracterisation.copy()
    df["id_troncon"] = df["id_troncon"].astype(str)

    # ── Somme des champs numériques par tronçon ──
    colonnes_a_sommer = [
        c for c in (["nb_populations", "lineaire_colonise_minimum_m"]
                    + list(COLONNES_COMPACITE.values()))
        if c in df.columns
    ]
    if not colonnes_a_sommer:
        return None

    # `fillna(0)` avant la somme : dans la table longue, un couple non observé
    # porte NaN (choix structurant CS-11 — on n'écrit jamais 0 pour une
    # absence non démontrée). Pour un TOTAL par tronçon, en revanche, traiter
    # ces NaN comme 0 est correct : on additionne ce qui est observé.
    agrege = df.groupby("id_troncon")[colonnes_a_sommer].sum(min_count=0)
    agrege = agrege.fillna(0)

    # ── Compacité dominante ──
    colonnes_compacite_presentes = {
        classe: col for classe, col in COLONNES_COMPACITE.items()
        if col in agrege.columns
    }
    if colonnes_compacite_presentes:
        table_compacite = agrege[list(colonnes_compacite_presentes.values())]
        # `idxmax(axis=1)` renvoie le NOM de la colonne du maximum de chaque
        # ligne. On le retraduit ensuite en nom de classe.
        nom_vers_classe = {v: k for k, v in colonnes_compacite_presentes.items()}
        dominante = table_compacite.idxmax(axis=1).map(nom_vers_classe)
        # Un tronçon sans aucune population n'a pas de classe dominante :
        # idxmax renverrait arbitrairement la première colonne, ce qui serait
        # une affirmation fausse. On force donc la valeur à None.
        aucune_population = table_compacite.sum(axis=1) == 0
        dominante[aucune_population] = None
        agrege["compacite_dominante"] = dominante

    agrege = agrege.rename(columns={
        "lineaire_colonise_minimum_m": "lineaire_colonise_total_m",
        "nb_populations": "nb_populations_carac",
    })
    agrege.index.name = colonne_id
    return agrege.reset_index()


def _preparer_table_troncons(df_scoring, colonne_id, df_caracterisation):
    """
    Construit la table de travail : une ligne par tronçon, enrichie des
    agrégats de caractérisation quand ils existent.

    On travaille sur une COPIE : le module de graphiques ne doit jamais
    modifier le df_scoring du lanceur, qui part ensuite dans le GeoPackage.
    """
    table = df_scoring.copy()
    table[colonne_id] = table[colonne_id].astype(str)

    agrege = _agreger_caracterisation(df_caracterisation, colonne_id)
    if agrege is not None:
        # `how="left"` : on garde tous les tronçons du scoring, même ceux qui
        # n'apparaissent pas dans la caractérisation.
        # `suffixes` : si une colonne de même nom existe des deux côtés, la
        # version issue de la caractérisation reçoit un suffixe explicite au
        # lieu d'écraser silencieusement celle du scoring.
        table = table.merge(agrege, on=colonne_id, how="left",
                            suffixes=("", "_carac"))
    return table


def _troncons_colonises(gdf_EEE, colonne_id):
    """
    Renvoie l'ensemble des identifiants de tronçons portant au moins un point
    d'occurrence d'EEE.

    ⚠️ Point de méthode important. Dans `gdf_EEE`, chaque ligne est un POINT.
    Après la jointure spatiale, `colonne_id` vaut l'identifiant du tronçon, ou
    la chaîne 'NA' quand le point n'a pu être rattaché à aucun tronçon.
    Compter les lignes reviendrait à donner 30 fois plus de poids à un tronçon
    portant 30 relevés : il faut compter des identifiants DISTINCTS.
    """
    if colonne_id not in gdf_EEE.columns:
        return set(), pd.DataFrame()

    rattaches = gdf_EEE[
        gdf_EEE[colonne_id].notna() & (gdf_EEE[colonne_id].astype(str) != "NA")
    ].copy()
    rattaches[colonne_id] = rattaches[colonne_id].astype(str)
    return set(rattaches[colonne_id].unique()), rattaches


# ═══════════════════════════════════════════════════════════════════════════
# 4. SECTION 1 — AMPLEUR DE LA COLONISATION
# ═══════════════════════════════════════════════════════════════════════════
# Lecture en entonnoir, en trois temps :
#   1a. Y a-t-il un problème ?          → présence / absence sur le réseau
#   1b. Avec quelle espèce ?            → nombre de tronçons par espèce cible
#   1c. À quel volume ?                 → populations et linéaire par espèce
# ═══════════════════════════════════════════════════════════════════════════

def _figure_1a_presence(table, gdf_EEE, colonne_id, pied):
    """
    FIGURE 1a — Part du réseau où au moins une EEE est enregistrée.

    Une barre horizontale unique, coupée en deux. Une seule barre proportion-
    nelle se lit plus vite que deux barres côte à côte : la proportion est
    perçue directement, sans comparaison d'longueurs.
    """
    total = table[colonne_id].nunique()
    ids_colonises, _ = _troncons_colonises(gdf_EEE, colonne_id)
    # Intersection avec le réseau : un point peut pointer vers un identifiant
    # absent du périmètre final (tronçon écarté après déduplication).
    nb_colonises = len(ids_colonises & set(table[colonne_id].unique()))
    nb_indemnes = total - nb_colonises
    part = 100 * nb_colonises / total if total else 0

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=["Réseau étudié"], x=[nb_colonises], orientation="h",
        name="Au moins une EEE enregistrée",
        marker=dict(color=COULEUR_NEUTRE),
        text=[f"{_nb(nb_colonises)} tronçons — {_pc(part)}"],
        textposition="inside", insidetextanchor="middle",
        textfont=dict(color="white", size=14),
        hovertemplate="Au moins une EEE enregistrée<br>"
                      "%{x} tronçons<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        y=["Réseau étudié"], x=[nb_indemnes], orientation="h",
        name="Aucune EEE enregistrée",
        marker=dict(color=COULEUR_NEUTRE_CLAIR),
        text=[f"{_nb(nb_indemnes)} — {_pc(100 - part)}"],
        textposition="inside", insidetextanchor="middle",
        textfont=dict(color=COULEUR_TEXTE, size=13),
        hovertemplate="Aucune EEE enregistrée<br>"
                      "%{x} tronçons<extra></extra>",
    ))

    fig.update_layout(
        barmode="stack",
        showlegend=True,
        legend=dict(orientation="h", y=1.02, x=0, yanchor="bottom"),
        bargap=0.55,
    )
    fig.update_xaxes(title="Nombre de tronçons")
    fig.update_yaxes(showticklabels=False)
    _style_axes(fig, grille_x=True, grille_y=False)

    _habiller_figure(
        fig,
        titre="Part du réseau où une espèce exotique envahissante est enregistrée",
        sous_titre=f"{_nb(total)} tronçons analysés",
        note_lecture=(
            "Un tronçon est compté dès qu'au moins un point d'occurrence y est rattaché. "
            "L'absence d'enregistrement ne démontre pas l'absence de l'espèce : elle traduit "
            "l'état des relevés disponibles, sans qu'on puisse distinguer un tronçon prospecté "
            "sans résultat d'un tronçon non prospecté."
        ),
        pied=pied,
        hauteur=330, marge_basse=130, marge_gauche=40,
    )
    return fig, dict(total=total, colonises=nb_colonises, part=part)


def _figure_1b_par_espece(table, gdf_EEE, colonne_id, pied):
    """
    FIGURE 1b — Nombre de tronçons concernés, par espèce cible.

    Deuxième temps de l'entonnoir : une fois établi qu'une partie du réseau
    est concernée, savoir PAR QUOI. L'information est directement
    opérationnelle : les protocoles d'intervention, les périodes et les coûts
    diffèrent selon l'espèce.
    """
    total = table[colonne_id].nunique()
    _, rattaches = _troncons_colonises(gdf_EEE, colonne_id)

    if len(rattaches) == 0 or "species_name_sci" not in rattaches.columns:
        return None, None

    # `nunique()` et non `size()` : on compte des tronçons distincts par
    # espèce, pas des points.
    par_espece = (rattaches.groupby("species_name_sci")[colonne_id]
                  .nunique().sort_values(ascending=True))

    libelles = [_libelle_categorie(nom) for nom in par_espece.index]
    parts = [100 * v / total if total else 0 for v in par_espece.values]

    fig = go.Figure(go.Bar(
        y=libelles, x=par_espece.values, orientation="h",
        marker=dict(color=COULEUR_NEUTRE),
        text=[f"{_nb(v)}  ({_pc(p)})" for v, p in zip(par_espece.values, parts)],
        textposition="outside",
        hovertemplate="%{y}<br>%{x} tronçons concernés<extra></extra>",
    ))

    # Marge à droite pour que les étiquettes placées à l'extérieur des barres
    # ne soient pas tronquées par le bord du graphique.
    fig.update_xaxes(title="Nombre de tronçons où l'espèce est enregistrée",
                     range=[0, max(par_espece.values) * 1.25])
    _style_axes(fig, grille_x=True, grille_y=False)
    fig.update_layout(showlegend=False)

    _habiller_figure(
        fig,
        titre="Espèces enregistrées sur le réseau, par nombre de tronçons concernés",
        sous_titre=f"Sur {_nb(total)} tronçons analysés",
        note_lecture=(
            "La somme des barres peut dépasser le nombre de tronçons colonisés : un même "
            "tronçon porte souvent plusieurs espèces et compte alors dans plusieurs barres. "
            "Ce ne sont pas des parts d'un tout."
        ),
        pied=pied,
        hauteur=max(360, 150 + 55 * len(par_espece)),
        marge_basse=125, marge_gauche=170,
    )
    return fig, None


def _figure_1c_ampleur(table, colonne_id, df_caracterisation, pied):
    """
    FIGURE 1c — Ampleur de la colonisation, par espèce : nombre de populations
    et linéaire colonisé minimum.

    Troisième temps de l'entonnoir. Les deux mesures ne se recouvrent pas et
    c'est la raison de les afficher côte à côte :
      - le NOMBRE DE POPULATIONS dit la fragmentation, donc le nombre de
        foyers distincts à traiter et le temps de déplacement entre eux ;
      - le LINÉAIRE dit le volume de matière à gérer.
    Un tronçon avec 12 foyers isolés et un tronçon avec 2 linéaires continus
    peuvent totaliser le même linéaire pour un chantier très différent.

    Nécessite la table de caractérisation : renvoie None si elle est absente.
    """
    if df_caracterisation is None or len(df_caracterisation) == 0:
        return None, None
    if "categorie_EEE" not in df_caracterisation.columns:
        return None, None

    colonnes_utiles = [c for c in ("nb_populations", "lineaire_colonise_minimum_m")
                       if c in df_caracterisation.columns]
    if not colonnes_utiles:
        return None, None

    par_categorie = (df_caracterisation.groupby("categorie_EEE")[colonnes_utiles]
                     .sum(min_count=0).fillna(0))
    # Tri sur le nombre de populations, pour que les deux panneaux partagent
    # le même ordre de lecture.
    if "nb_populations" in par_categorie.columns:
        par_categorie = par_categorie.sort_values("nb_populations", ascending=True)

    # On écarte les catégories totalement absentes : afficher une barre à zéro
    # pour une espèce jamais enregistrée alourdit sans rien apprendre.
    par_categorie = par_categorie[par_categorie.sum(axis=1) > 0]
    if len(par_categorie) == 0:
        return None, None

    libelles = [_libelle_categorie(nom) for nom in par_categorie.index]

    fig = make_subplots(
        rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.10,
        subplot_titles=("Nombre de populations recensées",
                        "Linéaire colonisé minimum (m)"),
    )

    if "nb_populations" in par_categorie.columns:
        valeurs = par_categorie["nb_populations"].values
        fig.add_trace(go.Bar(
            y=libelles, x=valeurs, orientation="h",
            marker=dict(color=COULEUR_NEUTRE),
            text=[_nb(v) for v in valeurs], textposition="outside",
            hovertemplate="%{y}<br>%{x} populations<extra></extra>",
            showlegend=False,
        ), row=1, col=1)
        fig.update_xaxes(range=[0, max(valeurs) * 1.25], row=1, col=1)

    if "lineaire_colonise_minimum_m" in par_categorie.columns:
        valeurs = par_categorie["lineaire_colonise_minimum_m"].values
        fig.add_trace(go.Bar(
            y=libelles, x=valeurs, orientation="h",
            marker=dict(color="#7C8A94"),
            text=[f"{_nb(v)} m" for v in valeurs], textposition="outside",
            hovertemplate="%{y}<br>au moins %{x} m colonisés<extra></extra>",
            showlegend=False,
        ), row=1, col=2)
        borne = max(max(valeurs), 1) * 1.28
        fig.update_xaxes(range=[0, borne], row=1, col=2)

    _style_axes(fig, grille_x=True, grille_y=False)

    _habiller_figure(
        fig,
        titre="Ampleur de la colonisation par espèce : fragmentation et volume",
        sous_titre="Populations au sens du protocole national de recensement "
                   "(Albert coord., 2017) — règle des 50 m",
        note_lecture=(
            "Les deux panneaux mesurent deux choses différentes : à gauche le nombre de foyers "
            "distincts à traiter, à droite le volume de matière. Un même linéaire peut "
            "correspondre à un seul chantier continu ou à une dizaine d'interventions dispersées.<br>"
            "Le linéaire affiché est un MINORANT, jamais une estimation : les classes de longueur "
            "du protocole sont ouvertes vers le haut, seule leur borne basse est garantie, et une "
            "population de moins de 5 m contribue 0 mètre. La réalité de terrain est donc "
            "nécessairement supérieure — voir la notice de lecture pour l'écart mesuré sur la zone."
        ),
        pied=pied,
        hauteur=max(420, 200 + 55 * len(par_categorie)),
        marge_basse=170, marge_gauche=170,
    )
    return fig, None


# ═══════════════════════════════════════════════════════════════════════════
# 5. SECTION 2 — QUEL ENJEU DOMINE LE RÉSEAU
# ═══════════════════════════════════════════════════════════════════════════

def _figure_2_enjeux(table, pied, maxima):
    """
    FIGURE 2 — Poids relatif des trois enjeux sur le réseau.

    Deux panneaux complémentaires, parce qu'aucun des deux ne suffit :

      - à GAUCHE, le TAUX DE SATURATION (score moyen ÷ maximum théorique).
        C'est ce qui rend MS, N et P comparables : sans cette normalisation,
        l'enjeu comptant le plus d'indicateurs sortirait mécaniquement en
        tête, pour une raison de barème et non de terrain.

      - à DROITE, les scores BRUTS en boîtes à moustaches, avec le maximum
        théorique en repère. C'est ce qui montre la DISPERSION : un enjeu
        faible en moyenne peut concentrer des valeurs élevées sur un petit
        nombre de tronçons — information que la moyenne efface complètement,
        et qui est précisément celle qui intéresse un gestionnaire.
    """
    enjeux = [e for e in ("MS", "N", "P") if f"score_enjeu_{e}" in table.columns]
    if not enjeux:
        return None, None

    donnees = {e: table[f"score_enjeu_{e}"].dropna() for e in enjeux}
    taux = {e: (100 * donnees[e].mean() / maxima[e]) if maxima.get(e) else 0
            for e in enjeux}

    fig = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.13,
        subplot_titles=("Taux de saturation moyen",
                        "Dispersion des scores sur le réseau"),
    )

    # ── Panneau gauche : barre « fantôme » à 100 % + barre du taux ──
    # La barre de fond matérialise le potentiel maximal et rend la lecture du
    # taux immédiate, sans avoir à remonter à l'axe.
    fig.add_trace(go.Bar(
        x=[LIBELLES_ENJEUX[e] for e in enjeux], y=[100] * len(enjeux),
        marker=dict(color="#F0F1F2"), showlegend=False,
        hoverinfo="skip", width=0.55,
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=[LIBELLES_ENJEUX[e] for e in enjeux],
        y=[taux[e] for e in enjeux],
        marker=dict(color=[COULEURS_ENJEUX[e] for e in enjeux]),
        text=[f"<b>{_pc(taux[e])}</b>" for e in enjeux],
        textposition="outside",
        customdata=[[_dec(donnees[e].mean()), maxima[e]] for e in enjeux],
        hovertemplate="%{x}<br>score moyen : %{customdata[0]} sur "
                      "%{customdata[1]}<extra></extra>",
        showlegend=False, width=0.55,
    ), row=1, col=1)

    # ── Panneau droit : boîtes à moustaches ──
    for e in enjeux:
        fig.add_trace(go.Box(
            y=donnees[e].values, name=LIBELLES_ENJEUX[e],
            marker=dict(color=COULEURS_ENJEUX[e], size=4),
            fillcolor=COULEURS_ENJEUX[e], line=dict(color="#44494D", width=1.2),
            # `boxpoints="outliers"` : seuls les points hors moustaches sont
            # dessinés. Ce sont les tronçons atypiques, l'information la plus
            # utile de ce panneau ; les autres points feraient du bruit.
            boxpoints="outliers",
            showlegend=False,
            hovertemplate="%{y} points<extra></extra>",
        ), row=1, col=2)

        # Repère du maximum théorique : un tiret court à la verticale de la
        # boîte concernée. `add_shape` avec des coordonnées de données permet
        # de le caler exactement sur la bonne catégorie.
        fig.add_shape(
            type="line", row=1, col=2,
            x0=enjeux.index(e) - 0.35, x1=enjeux.index(e) + 0.35,
            y0=maxima[e], y1=maxima[e],
            line=dict(color=COULEUR_ACCENT, width=1.5, dash="dash"),
        )
        fig.add_annotation(
            row=1, col=2, x=enjeux.index(e), y=maxima[e],
            text=f"max {maxima[e]:g}", showarrow=False,
            yanchor="bottom", font=dict(size=10, color=COULEUR_ACCENT),
        )

    fig.update_yaxes(title="% du maximum théorique", range=[0, 118],
                     row=1, col=1)
    fig.update_yaxes(title="Score de l'enjeu par tronçon (points)", row=1, col=2)
    fig.update_layout(barmode="overlay")
    _style_axes(fig)

    enjeu_max = max(taux, key=taux.get)

    _habiller_figure(
        fig,
        titre="Quel enjeu pèse le plus sur le réseau ?",
        sous_titre=(f"Enjeu le plus saturé : {LIBELLES_ENJEUX[enjeu_max]} "
                    f"({_pc(taux[enjeu_max])} de son maximum théorique) — "
                    f"{_nb(len(table))} tronçons"),
        note_lecture=(
            "Les trois enjeux n'ont ni le même nombre d'indicateurs ni le même score maximal : "
            "leurs scores bruts ne sont pas comparables directement. Le panneau de gauche "
            "rapporte chaque score moyen à son maximum théorique pour les rendre comparables ; "
            "celui de droite conserve les scores bruts et montre leur étalement.<br>"
            "Un enjeu peu saturé en moyenne mais très dispersé désigne un petit nombre de "
            "tronçons fortement concernés, que la moyenne seule ne laisse pas voir."
        ),
        pied=pied,
        hauteur=600, marge_basse=165,
    )
    return fig, taux


def _tableau_statistiques(table, maxima):
    """
    Construit le tableau HTML des statistiques descriptives des scores.

    Un tableau plutôt qu'une figure : quatre lignes et six colonnes se lisent
    plus vite sous forme tabulaire, se copient directement dans un rapport, et
    n'ajoutent pas une figure de plus à la page.

    Choix des indicateurs : min, Q1, médiane, moyenne, Q3, max. L'étendue
    brute (min-max) est pilotée par une seule valeur extrême, donc peu
    robuste ; l'écart interquartile (Q1-Q3) dit où se situe le gros du réseau.
    Ce sont aussi exactement les valeurs que dessinent les boîtes à moustaches
    de la figure précédente : le lecteur retrouve les mêmes nombres sous deux
    formes.
    """
    lignes = []
    definitions = [("Score total", "score_troncon_final", sum(maxima.values()))]
    for e in ("MS", "N", "P"):
        if f"score_enjeu_{e}" in table.columns:
            definitions.append((LIBELLES_ENJEUX[e], f"score_enjeu_{e}", maxima.get(e)))

    for libelle, colonne, maximum in definitions:
        if colonne not in table.columns:
            continue
        serie = table[colonne].dropna()
        if len(serie) == 0:
            continue
        lignes.append(f"""
            <tr>
                <th scope="row">{_echapper(libelle)}</th>
                <td>{_dec(serie.min(), 1)}</td>
                <td>{_dec(serie.quantile(0.25), 1)}</td>
                <td>{_dec(serie.median(), 1)}</td>
                <td>{_dec(serie.mean(), 2)}</td>
                <td>{_dec(serie.quantile(0.75), 1)}</td>
                <td>{_dec(serie.max(), 1)}</td>
                <td class="col-max">{maximum:g}</td>
            </tr>""")

    if not lignes:
        return ""

    return f"""
    <table class="tableau-stats">
        <caption>
            Statistiques descriptives des scores, en points.
            Q1 et Q3 délimitent la moitié centrale des tronçons.
        </caption>
        <thead>
            <tr>
                <th scope="col">Score</th>
                <th scope="col">Minimum</th>
                <th scope="col">Q1</th>
                <th scope="col">Médiane</th>
                <th scope="col">Moyenne</th>
                <th scope="col">Q3</th>
                <th scope="col">Maximum</th>
                <th scope="col" class="col-max">Maximum théorique</th>
            </tr>
        </thead>
        <tbody>{"".join(lignes)}</tbody>
    </table>"""


# ═══════════════════════════════════════════════════════════════════════════
# 6. SECTION 3 — RECOUVREMENT DES TÊTES DE CLASSEMENT
# ═══════════════════════════════════════════════════════════════════════════

def _figure_3_recouvrement(table, colonne_id, pied,
                           part=PART_TETE_DE_CLASSEMENT):
    """
    FIGURE 3 — Les tronçons aux scores les plus élevés sont-ils les mêmes
    selon l'enjeu considéré ?

    PRINCIPE : pour chaque enjeu, on isole les X % de tronçons dont le score
    est le plus élevé sur CET enjeu. On obtient trois sous-ensembles, et la
    question est de savoir dans quelle mesure ils se recouvrent.

    POURQUOI CETTE FIGURE : c'est la seule qui répond à « est-ce que mon
    arbitrage entre enjeux change quelque chose ? ». Si les trois listes se
    recouvrent largement, le débat sur la pondération est théorique et on peut
    avancer. Si elles sont disjointes, la question devient un choix de
    politique de gestion, qui doit être posé explicitement. Et un tronçon qui
    figure dans les trois listes est un cas que personne ne discutera.

    FORME RETENUE : un histogramme des 7 combinaisons possibles, et non un
    diagramme de Venn. Trois cercles proportionnels sont mal lus (l'œil
    sous-estime les aires), Plotly ne les produit pas nativement, et la
    lecture demanderait un apprentissage. Ici chaque tronçon apparaît dans une
    seule barre, celle qui correspond exactement à sa combinaison d'enjeux :
    les barres s'additionnent, sans recouvrement à interpréter.
    """
    enjeux = [e for e in ("MS", "N", "P") if f"score_enjeu_{e}" in table.columns]
    if len(enjeux) < 2:
        return None, None

    nb_total = len(table)
    # Au moins un tronçon, sinon la figure n'a pas d'objet sur un réseau
    # de moins de dix tronçons.
    taille_tete = max(1, int(round(nb_total * part)))

    # ── Constitution des trois sous-ensembles ──
    # `nlargest` gère seul les ex æquo au seuil : il en retient exactement
    # `taille_tete`, en s'arrêtant au premier rencontré. C'est une convention,
    # signalée dans la note de lecture.
    tetes = {}
    for e in enjeux:
        tete = table.nlargest(taille_tete, f"score_enjeu_{e}")
        tetes[e] = set(tete[colonne_id].astype(str))

    # ── Affectation de chaque tronçon à UNE combinaison ──
    # Pour chaque tronçon, on liste les enjeux pour lesquels il est en tête.
    # La combinaison est le tuple ordonné de ces enjeux ; les tronçons
    # présents dans aucune tête sont ignorés (ils ne sont pas le sujet).
    combinaisons = {}
    membres = {}
    for identifiant in table[colonne_id].astype(str):
        appartenances = tuple(e for e in enjeux if identifiant in tetes[e])
        if not appartenances:
            continue
        combinaisons[appartenances] = combinaisons.get(appartenances, 0) + 1
        membres.setdefault(appartenances, []).append(identifiant)

    if not combinaisons:
        return None, None

    # ── Ordre d'affichage : d'abord les enjeux seuls, puis les paires, puis
    # le triplet. L'œil suit alors une progression du plus dispersé au plus
    # convergent, et la barre la plus à droite est celle qui fait consensus.
    def cle_de_tri(combinaison):
        return (len(combinaison), [enjeux.index(e) for e in combinaison])

    ordre = sorted(combinaisons.keys(), key=cle_de_tri)

    libelles, valeurs, couleurs, survols = [], [], [], []
    for combinaison in ordre:
        if len(combinaison) == 1:
            libelle = f"{combinaison[0]} seul"
            couleur = COULEURS_ENJEUX[combinaison[0]]
        elif len(combinaison) == len(enjeux):
            libelle = "Les " + str(len(enjeux)) + " enjeux"
            couleur = "#3D4A52"
        else:
            libelle = " + ".join(combinaison)
            couleur = "#8A949B"

        libelles.append(libelle)
        valeurs.append(combinaisons[combinaison])
        couleurs.append(couleur)

        detail = ", ".join(LIBELLES_ENJEUX[e] for e in combinaison)
        # Aperçu de quelques identifiants dans l'infobulle : le gestionnaire
        # peut ainsi partir directement d'un tronçon nommé pour aller le
        # regarder dans QGIS.
        apercu = ", ".join(membres[combinaison][:6])
        if len(membres[combinaison]) > 6:
            apercu += f", … (+{len(membres[combinaison]) - 6})"
        survols.append(f"En tête pour : {detail}<br>"
                       f"{combinaisons[combinaison]} tronçons<br>"
                       f"<i>{apercu}</i>")

    fig = go.Figure(go.Bar(
        x=libelles, y=valeurs,
        marker=dict(color=couleurs),
        text=[_nb(v) for v in valeurs], textposition="outside",
        customdata=survols,
        hovertemplate="%{customdata}<extra></extra>",
    ))
    fig.update_xaxes(title="Enjeux pour lesquels le tronçon figure "
                           "dans les scores les plus élevés")
    fig.update_yaxes(title="Nombre de tronçons",
                     range=[0, max(valeurs) * 1.20])
    fig.update_layout(showlegend=False)
    _style_axes(fig)

    nb_consensus = combinaisons.get(tuple(enjeux), 0)

    _habiller_figure(
        fig,
        titre=f"Les {int(part * 100)} % de tronçons aux scores les plus élevés "
              f"sont-ils les mêmes selon l'enjeu ?",
        sous_titre=(f"{taille_tete} tronçons retenus par enjeu, sur {_nb(nb_total)} — "
                    f"{nb_consensus} tronçon(s) en tête pour les trois enjeux"),
        note_lecture=(
            "COMMENT LIRE : pour chaque enjeu pris séparément, on retient les tronçons dont le "
            f"score est le plus élevé sur cet enjeu ({int(part * 100)} % du réseau). Chaque "
            "tronçon apparaît ensuite dans UNE SEULE barre : celle des enjeux pour lesquels il "
            "figure dans cette tête de classement. Les barres ne se recouvrent donc pas et "
            "peuvent s'additionner.<br>"
            "Des barres « enjeu seul » élevées signifient que le choix de l'enjeu de référence "
            "change fortement la liste des tronçons concernés. Une barre de droite élevée "
            "signifie au contraire que les enjeux convergent. Le seuil est une convention de "
            "lecture, sans signification écologique."
        ),
        pied=pied,
        hauteur=580, marge_basse=185,
    )
    return fig, None


# ═══════════════════════════════════════════════════════════════════════════
# 7. SECTION 4 — SCORE ET AMPLEUR, TRONÇON PAR TRONÇON
# ═══════════════════════════════════════════════════════════════════════════

def _figure_4_nuage(table, colonne_id, pied, maxima):
    """
    FIGURE 4 — Nuage croisant le score final et l'ampleur de la colonisation.

    Un point par tronçon :
      - en ORDONNÉE, le score final SPRINGE (l'enjeu) ;
      - en ABSCISSE, le linéaire colonisé minimum, ou à défaut le nombre de
        populations (l'ampleur) ;
      - en COULEUR, la classe de compacité dominante (la forme du foyer).

    POURQUOI : le score seul ne suffit pas à décider. Deux tronçons à 30
    points, l'un portant 15 m de foyers isolés, l'autre 600 m de linéaire
    continu, n'appellent ni le même budget ni la même stratégie. Ce nuage met
    l'enjeu et l'ampleur sur le même plan, et laisse le gestionnaire tracer
    lui-même ses propres limites.

    CE QUE LA FIGURE NE FAIT PAS : aucun quadrant n'est étiqueté, aucune zone
    n'est désignée comme « à traiter ». Les bandes horizontales affichées sont
    des seuils de CUMUL D'ENJEUX, c'est-à-dire des faits arithmétiques sur le
    barème (voir _seuils_cumul), et non des recommandations d'intervention.
    """
    if "score_troncon_final" not in table.columns:
        return None, None

    # ── Choix de l'axe des abscisses ──
    # Le linéaire est préféré quand il existe : c'est la mesure la plus proche
    # d'un volume de travail. À défaut, le nombre de populations.
    if "lineaire_colonise_total_m" in table.columns and \
            table["lineaire_colonise_total_m"].fillna(0).sum() > 0:
        colonne_x = "lineaire_colonise_total_m"
        titre_x = "Linéaire colonisé minimum sur le tronçon (m)"
        unite_x = " m"
    elif "nb_populations_total" in table.columns and \
            table["nb_populations_total"].fillna(0).sum() > 0:
        colonne_x = "nb_populations_total"
        titre_x = "Nombre de populations recensées sur le tronçon"
        unite_x = " population(s)"
    else:
        return None, None

    donnees = table.dropna(subset=["score_troncon_final"]).copy()
    donnees[colonne_x] = donnees[colonne_x].fillna(0)
    if len(donnees) == 0:
        return None, None

    max_theorique = sum(maxima.values())
    x_max = max(donnees[colonne_x].max(), 1)

    fig = go.Figure()

    # ── Bandes horizontales des seuils de cumul ──
    # Tracées en `layer="below"` pour rester derrière les points. Des bandes
    # colorées plutôt que des lignes : une ligne horizontale se confondrait
    # visuellement avec un alignement de points.
    # Bandes déduites du barème (voir _seuils_cumul) : elles suivent
    # automatiquement toute évolution des maxima.
    seuils = _seuils_cumul(maxima)
    for seuil in seuils:
        borne_haute = min(seuil["max"], max_theorique)
        fig.add_shape(
            type="rect", layer="below",
            xref="paper", x0=0, x1=1,
            yref="y", y0=seuil["min"] - 0.5, y1=borne_haute + 0.5,
            fillcolor=seuil["couleur"], line=dict(width=0),
        )
        # Libellé de la bande, calé à droite, en coordonnées « papier » pour
        # rester visible même lorsque l'utilisateur zoome horizontalement.
        fig.add_annotation(
            xref="paper", x=0.995, yref="y",
            y=(seuil["min"] + borne_haute) / 2,
            text=f"<b>{seuil['libelle']}</b><br>"
                 f"<span style='font-size:10px'>{seuil['min']}–{borne_haute} pts — "
                 f"{seuil['fait']}</span>",
            showarrow=False, xanchor="right", align="right",
            font=dict(size=11, color="#5A6167"),
        )

    # ── Points, groupés par compacité dominante ──
    # Un `Scatter` par classe permet d'obtenir une légende cliquable : le
    # gestionnaire peut masquer une classe d'un clic pour isoler les autres.
    if "compacite_dominante" in donnees.columns:
        classes = [c for c in ORDRE_COMPACITE
                   if c in set(donnees["compacite_dominante"].dropna())]
        groupes = [(c, donnees[donnees["compacite_dominante"] == c]) for c in classes]
        # Les tronçons sans compacité connue forment un groupe à part, jamais
        # rattaché arbitrairement à une classe existante.
        sans_classe = donnees[donnees["compacite_dominante"].isna()]
        if len(sans_classe) > 0:
            groupes.append((None, sans_classe))
    else:
        groupes = [(None, donnees)]

    for classe, groupe in groupes:
        if len(groupe) == 0:
            continue
        libelle = (LIBELLES_COMPACITE.get(classe, str(classe)) if classe
                   else "Compacité inconnue")
        couleur = (COULEURS_COMPACITE.get(classe, COULEUR_NEUTRE) if classe
                   else COULEUR_NEUTRE_CLAIR)

        # ── Contenu de l'infobulle ──
        # C'est le principal apport de la version HTML : sans elle, un point
        # du nuage est anonyme et le graphique ne sert qu'à décrire une forme.
        # Avec elle, le gestionnaire identifie le tronçon et peut aller le
        # regarder dans QGIS.
        colonnes_survol = [colonne_id, "score_troncon_final"]
        for c in ("score_enjeu_MS", "score_enjeu_N", "score_enjeu_P",
                  "nb_populations_total", "synthese_EEE"):
            colonnes_survol.append(c if c in groupe.columns else None)

        donnees_survol = []
        for _, ligne in groupe.iterrows():
            donnees_survol.append([
                str(ligne[colonne_id]),
                _dec(ligne.get("score_enjeu_MS"), 1),
                _dec(ligne.get("score_enjeu_N"), 1),
                _dec(ligne.get("score_enjeu_P"), 1),
                _nb(ligne["nb_populations_total"])
                if "nb_populations_total" in groupe.columns else "—",
                # La synthèse textuelle peut être longue : on la tronque pour
                # que l'infobulle reste lisible à l'écran.
                (str(ligne["synthese_EEE"])[:110] + "…"
                 if "synthese_EEE" in groupe.columns
                 and isinstance(ligne.get("synthese_EEE"), str)
                 and len(str(ligne["synthese_EEE"])) > 110
                 else str(ligne.get("synthese_EEE", "—"))),
                libelle,
            ])

        fig.add_trace(go.Scatter(
            x=groupe[colonne_x], y=groupe["score_troncon_final"],
            mode="markers", name=libelle,
            marker=dict(size=9, color=couleur,
                        line=dict(width=0.8, color="white"), opacity=0.85),
            customdata=donnees_survol,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Score total : %{y} points"
                "<br>&nbsp;&nbsp;MS %{customdata[1]} · N %{customdata[2]} · "
                "P %{customdata[3]}<br>"
                f"Ampleur : %{{x}}{unite_x}<br>"
                "Populations : %{customdata[4]}<br>"
                "Compacité dominante : %{customdata[6]}<br>"
                # customdata[5] = synthèse textuelle des EEE du tronçon,
                # produite par caracteriser_populations_EEE. Affichée en
                # italique en dernière ligne de l'infobulle.
                "<i>%{customdata[5]}</i>"
                "<extra></extra>"
            ),
        ))

    fig.update_xaxes(title=titre_x, range=[-x_max * 0.03, x_max * 1.30])
    fig.update_yaxes(title="Score final du tronçon (points)",
                     range=[-1, max_theorique + 1])
    fig.update_layout(
        legend=dict(orientation="h", y=1.02, x=0, yanchor="bottom",
                    title=dict(text="Compacité dominante : ")),
    )
    _style_axes(fig, grille_x=True, grille_y=True)

    _habiller_figure(
        fig,
        titre="Score et ampleur de la colonisation, tronçon par tronçon",
        sous_titre=f"{_nb(len(donnees))} tronçons — survolez un point pour "
                   f"identifier le tronçon et le détail de son score",
        note_lecture=(
            "Chaque point est un tronçon. La hauteur donne le niveau d'enjeu mesuré par "
            "SPRINGE, la position horizontale l'ampleur de la colonisation. Deux tronçons de "
            "même score peuvent se situer très loin l'un de l'autre sur l'axe horizontal, et "
            "n'appeler ni le même budget ni la même stratégie.<br>"
            "Les bandes horizontales sont des seuils de CUMUL D'ENJEUX, démontrés par le "
            f"barème : au-delà de {seuils[0]['max']} points, aucun enjeu seul ne peut porter "
            f"le score, donc au moins deux enjeux sont engagés ; au-delà de "
            f"{seuils[1]['max'] if len(seuils) > 1 else seuils[0]['max']}, les trois le sont "
            "nécessairement. "
            "Ce sont des constats arithmétiques, pas des consignes d'intervention.<br>"
            "Le linéaire est un minorant. La zone d'intérêt reste à définir par le gestionnaire."
        ),
        pied=pied,
        hauteur=700, marge_basse=190,
    )
    return fig, None


# ═══════════════════════════════════════════════════════════════════════════
# 8. SECTION 5 — FORME DES POPULATIONS SUR LE TERRAIN
# ═══════════════════════════════════════════════════════════════════════════

def _figure_5_compacite(df_caracterisation, pied):
    """
    FIGURE 5 — Compacité des populations, par espèce.

    POURQUOI : c'est l'axe qui change la NATURE de l'intervention, pas son
    rang. Des foyers isolés en front de colonisation laissent envisager une
    éradication ; un linéaire continu installé relève du confinement et de la
    gestion des propagules. Un gestionnaire qui prépare un marché a besoin de
    cette information avant même de savoir quel tronçon vient en premier.

    Cohérent avec le choix structurant du module de caractérisation : aucun
    score, aucun rang, aucun adjectif de valeur — uniquement des comptages.

    La modalité « non renseignée » est AFFICHÉE et non masquée : c'est une
    information sur la qualité de la donnée, et la masquer laisserait croire
    à une couverture complète du protocole.
    """
    if df_caracterisation is None or len(df_caracterisation) == 0:
        return None, None
    if "categorie_EEE" not in df_caracterisation.columns:
        return None, None

    colonnes = {classe: col for classe, col in COLONNES_COMPACITE.items()
                if col in df_caracterisation.columns}
    if not colonnes:
        return None, None

    par_categorie = (df_caracterisation.groupby("categorie_EEE")[list(colonnes.values())]
                     .sum(min_count=0).fillna(0))
    par_categorie = par_categorie[par_categorie.sum(axis=1) > 0]
    if len(par_categorie) == 0:
        return None, None

    # Tri par effectif total croissant : en barres horizontales, l'axe part du
    # bas, donc l'espèce la plus représentée se retrouve en haut du graphique.
    par_categorie = par_categorie.loc[par_categorie.sum(axis=1).sort_values().index]
    libelles = [_libelle_categorie(nom) for nom in par_categorie.index]
    totaux = par_categorie.sum(axis=1).values

    fig = go.Figure()
    for classe in ORDRE_COMPACITE:
        if classe not in colonnes:
            continue
        valeurs = par_categorie[colonnes[classe]].values
        # Part relative, calculée ici plutôt que dans le survol pour éviter
        # une division par zéro sur une espèce sans population.
        parts = [100 * v / t if t else 0 for v, t in zip(valeurs, totaux)]
        fig.add_trace(go.Bar(
            y=libelles, x=valeurs, orientation="h",
            name=LIBELLES_COMPACITE[classe],
            marker=dict(color=COULEURS_COMPACITE[classe]),
            customdata=[[_pc(p)] for p in parts],
            hovertemplate="%{y} — " + LIBELLES_COMPACITE[classe] +
                          "<br>%{x} populations (%{customdata[0]} de l'espèce)"
                          "<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        legend=dict(orientation="h", y=1.02, x=0, yanchor="bottom",
                    title=dict(text="Compacité : ")),
    )
    fig.update_xaxes(title="Nombre de populations recensées")
    _style_axes(fig, grille_x=True, grille_y=False)

    _habiller_figure(
        fig,
        titre="Forme des populations sur le terrain, par espèce",
        sous_titre="Compacité au sens du protocole national de recensement "
                   "(Albert coord., 2017)",
        note_lecture=(
            "Une population est un regroupement d'individus au sens du protocole (règle des "
            "50 m), et non une plante isolée. La compacité décrit la structure spatiale du "
            "foyer : ce n'est ni un score, ni un rang, ni un niveau de gravité.<br>"
            "Elle conditionne la NATURE de l'intervention envisageable plus que son ordre : "
            "individus isolés et linéaire continu ne relèvent pas des mêmes techniques. "
            "La part non renseignée est affichée telle quelle — voir la notice de lecture "
            "pour les taux de renseignement détaillés de la zone."
        ),
        pied=pied,
        hauteur=max(430, 210 + 55 * len(par_categorie)),
        marge_basse=160, marge_gauche=170,
    )
    return fig, None


# ═══════════════════════════════════════════════════════════════════════════
# 9. ASSEMBLAGE DE LA PAGE HTML
# ═══════════════════════════════════════════════════════════════════════════

# Feuille de style de la page. Volontairement sobre et sans dépendance
# externe : la page doit s'afficher correctement sans accès internet.
FEUILLE_DE_STYLE = """
    * { box-sizing: border-box; }

    body {
        margin: 0;
        padding: 32px 16px 64px;
        font-family: Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif;
        font-size: 15px;
        line-height: 1.6;
        color: #2B3238;
        background: #F4F6F7;
    }

    .conteneur { max-width: 1180px; margin: 0 auto; }

    /* ── En-tête ────────────────────────────────────────────────── */
    header {
        background: white;
        border-radius: 10px;
        padding: 28px 32px;
        margin-bottom: 24px;
        border-top: 4px solid #1F4E79;
        box-shadow: 0 1px 3px rgba(0,0,0,.07);
    }
    header h1 { margin: 0 0 6px; font-size: 25px; letter-spacing: -.2px; }
    header .sous-titre { color: #6B747C; margin: 0 0 20px; }

    nav { display: flex; flex-wrap: wrap; gap: 8px; }
    nav a {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 999px;
        background: #EDF1F4;
        color: #1F4E79;
        text-decoration: none;
        font-size: 13.5px;
        font-weight: 600;
    }
    nav a:hover { background: #1F4E79; color: white; }

    /* ── Cartes de cadrage ──────────────────────────────────────── */
    .grille-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }
    .carte-stat {
        background: white;
        border-radius: 10px;
        padding: 20px 22px;
        box-shadow: 0 1px 3px rgba(0,0,0,.07);
        border-left: 4px solid #5B6770;
    }
    .carte-stat .libelle {
        font-size: 12.5px; text-transform: uppercase;
        letter-spacing: .5px; color: #6B747C; font-weight: 600;
    }
    .carte-stat .valeur {
        font-size: 30px; font-weight: 700; line-height: 1.2; margin: 4px 0;
    }
    .carte-stat .detail { font-size: 12.5px; color: #6B747C; line-height: 1.45; }

    /* ── Sections de graphique ──────────────────────────────────── */
    section.bloc {
        background: white;
        border-radius: 10px;
        padding: 28px 32px 22px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,.07);
        scroll-margin-top: 16px;
    }
    section.bloc > h2 {
        margin: 0 0 4px;
        font-size: 20px;
        border-bottom: 2px solid #EDF1F4;
        padding-bottom: 10px;
    }
    section.bloc .question {
        color: #1F4E79; font-weight: 600; font-size: 14.5px; margin: 12px 0 4px;
    }
    section.bloc .explication { color: #444C53; margin: 0 0 18px; }
    section.bloc .explication + .explication { margin-top: -8px; }

    .avertissement {
        background: #FDF6E7;
        border-left: 4px solid #C89A28;
        padding: 12px 16px;
        border-radius: 4px;
        font-size: 14px;
        margin: 16px 0;
    }

    /* ── Bouton de téléchargement ───────────────────────────────── */
    .barre-outils {
        display: flex; justify-content: flex-end;
        margin-top: 4px; padding-top: 10px;
        border-top: 1px solid #EDF1F4;
    }
    .bouton-svg {
        background: #1F4E79; color: white; border: none;
        padding: 8px 16px; border-radius: 6px;
        font-size: 13.5px; font-weight: 600; cursor: pointer;
        font-family: inherit;
    }
    .bouton-svg:hover { background: #163A5A; }
    .bouton-svg:active { transform: translateY(1px); }

    /* ── Tableau de statistiques ────────────────────────────────── */
    .tableau-stats {
        width: 100%; border-collapse: collapse; margin: 18px 0 6px;
        font-size: 14px;
    }
    .tableau-stats caption {
        caption-side: bottom; text-align: left;
        color: #6B747C; font-size: 12.5px; padding-top: 8px;
    }
    .tableau-stats th, .tableau-stats td {
        padding: 9px 12px; text-align: right;
        border-bottom: 1px solid #EDF1F4;
    }
    .tableau-stats thead th {
        background: #F4F6F7; font-size: 12.5px;
        text-transform: uppercase; letter-spacing: .4px; color: #4A5259;
    }
    .tableau-stats tbody th[scope="row"] {
        text-align: left; font-weight: 600;
    }
    .tableau-stats .col-max { color: #6B747C; border-left: 1px solid #EDF1F4; }

    /* ── Pied de page ───────────────────────────────────────────── */
    footer {
        text-align: center; color: #7E868D; font-size: 13px;
        padding: 24px 12px; line-height: 1.7;
    }

    /* ── Impression ─────────────────────────────────────────────── */
    /* La page n'est pas conçue pour être imprimée telle quelle — on retire
       simplement les éléments interactifs, sans effet à l'impression. */
    @media print {
        body { background: white; }
        nav, .barre-outils { display: none; }
        section.bloc { box-shadow: none; page-break-inside: avoid; }
    }
"""

# Fonction JavaScript déclenchant l'export. `Plotly.downloadImage` est fournie
# par la bibliothèque déjà embarquée dans la page : aucun appel réseau,
# aucune dépendance Python supplémentaire (pas de kaleido à installer).
SCRIPT_TELECHARGEMENT = f"""
    function telechargerFigureSVG(idDiv, nomFichier) {{
        var element = document.getElementById(idDiv);
        if (!element) {{ return; }}
        Plotly.downloadImage(element, {{
            format: 'svg',
            filename: nomFichier,
            width: {EXPORT_LARGEUR},
            height: {EXPORT_HAUTEUR}
        }});
    }}
"""


def _bloc_section(identifiant, titre, paragraphes, fig, nom_export,
                  premiere_figure, contenu_supplementaire=""):
    """
    Assemble une section de la page : titre, texte d'accompagnement, figure
    interactive, bouton de téléchargement.

    Paramètres
    ----------
    paragraphes : list[str]
        Texte pédagogique affiché AVANT la figure. Le premier élément est mis
        en évidence comme la question à laquelle la section répond.
    premiere_figure : bool
        Si True, la bibliothèque JavaScript de Plotly (environ 3,5 Mo) est
        incluse avec cette figure. Elle ne doit l'être qu'UNE SEULE FOIS dans
        toute la page, sans quoi le fichier devient inutilement énorme.
    """
    div_id = f"fig-{identifiant}"

    corps_texte = ""
    for i, paragraphe in enumerate(paragraphes):
        classe = "question" if i == 0 else "explication"
        corps_texte += f'<p class="{classe}">{paragraphe}</p>'

    if fig is not None:
        graphique_html = fig.to_html(
            full_html=False,
            include_plotlyjs=bool(premiere_figure),
            div_id=div_id,
            config={
                "responsive": True,
                "displaylogo": False,
                "locale": "fr",
                # L'icône appareil photo de la barre d'outils exporte elle
                # aussi en SVG, avec le même nom de fichier que le bouton.
                "toImageButtonOptions": {
                    "format": "svg",
                    "filename": nom_export,
                    "width": EXPORT_LARGEUR,
                    "height": EXPORT_HAUTEUR,
                },
                # On retire les outils de sélection, peu utiles ici, mais on
                # CONSERVE le zoom : c'est ce qui permet d'explorer un nuage
                # dense sans dégrader l'affichage.
                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
            },
        )
        barre = (f'<div class="barre-outils">'
                 f'<button class="bouton-svg" '
                 f'onclick="telechargerFigureSVG(\'{div_id}\', \'{nom_export}\')">'
                 f'⭳ Télécharger cette figure (SVG)</button></div>')
    else:
        graphique_html = ('<p class="avertissement">Figure non produite : '
                          'les données nécessaires ne sont pas disponibles '
                          'pour ce traitement.</p>')
        barre = ""

    return f"""
    <section class="bloc" id="{identifiant}">
        <h2>{titre}</h2>
        {corps_texte}
        {graphique_html}
        {barre}
        {contenu_supplementaire}
    </section>"""


def _carte_stat(libelle, valeur, detail, couleur=COULEUR_NEUTRE):
    """Produit une carte de cadrage du bandeau supérieur."""
    return f"""
        <div class="carte-stat" style="border-left-color:{couleur}">
            <div class="libelle">{_echapper(libelle)}</div>
            <div class="valeur">{valeur}</div>
            <div class="detail">{detail}</div>
        </div>"""


# ═══════════════════════════════════════════════════════════════════════════
# 10. FONCTION PUBLIQUE
# ═══════════════════════════════════════════════════════════════════════════

def generer_graphiques_plotly(df_scoring,
                              gdf_EEE,
                              colonne_id,
                              output_dir,
                              name=None,
                              DIR=None,
                              NOM=None,
                              date_reference=None,
                              df_caracterisation=None,
                              maxima_theoriques=None,
                              version_springe=None,
                              liste_avertissements=None):
    """
    Produit la page HTML interactive des résultats de SPRINGE.

    Sortie : <output_dir>/graphiques/graphiques_SPRINGE.html

    Paramètres
    ----------
    df_scoring : pandas.DataFrame
        Une ligne par tronçon, avec les colonnes `score_enjeu_MS/N/P`,
        `score_troncon_final`, et — si la caractérisation a été activée — les
        champs de synthèse (`nb_populations_total`, `synthese_EEE`...).
    gdf_EEE : geopandas.GeoDataFrame
        Points d'occurrence, après mapping des espèces (`species_name_sci`) et
        jointure aux tronçons (`colonne_id`, valant 'NA' si non rattaché).
    colonne_id : str
        Colonne d'identifiant de tronçon (typiquement 'nom_plo_fi').
    output_dir : str ou Path
        Dossier de sortie du run ; un sous-dossier `graphiques` y est créé.
    name, DIR, NOM, date_reference, version_springe
        Métadonnées de traçabilité, reprises en pied de chaque figure.
    df_caracterisation : pandas.DataFrame, optionnel
        Table longue produite par `caracteriser_populations_EEE`. Si None, les
        sections 1c et 5 sont remplacées par un message, et le nuage se rabat
        sur le nombre de populations.
    maxima_theoriques : dict, optionnel
        Force les maxima par enjeu, par exemple {"MS": 16, "N": 10, "P": 12}.
    liste_avertissements : list, optionnel
        Liste `_WARNINGS_SPRINGE` du lanceur, enrichie des figures non
        produites pour remonter dans le rapport d'exécution.

    Retour
    ------
    str : chemin du fichier HTML écrit, ou None en cas d'échec.
    """
    print(f"\n{'=' * 70}")
    print("GÉNÉRATION DE LA PAGE DE GRAPHIQUES INTERACTIFS")
    print(f"{'=' * 70}\n")

    dossier = Path(output_dir) / "graphiques"
    dossier.mkdir(parents=True, exist_ok=True)

    pied = _construire_pied(name, DIR, NOM, date_reference, version_springe)
    maxima = _calculer_maxima(df_scoring, maxima_theoriques)
    table = _preparer_table_troncons(df_scoring, colonne_id, df_caracterisation)

    print(f"Maxima théoriques : MS={maxima.get('MS')}  N={maxima.get('N')}  "
          f"P={maxima.get('P')}  total={sum(maxima.values()):g}")

    def _signaler(message):
        """Trace une figure non produite, en console et dans le rapport."""
        print(f"  ⚠️  {message}")
        if liste_avertissements is not None:
            liste_avertissements.append(message)

    def _produire(libelle, fonction):
        """
        Exécute une fonction de figure en isolant ses erreurs.

        Isolation volontaire : l'échec d'une figure (colonne absente, données
        vides) ne doit pas empêcher les autres d'être produites. Les
        graphiques sont un livrable secondaire — le GeoPackage, lui, est déjà
        écrit à ce stade du traitement.
        """
        try:
            fig, extra = fonction()
            if fig is None:
                _signaler(f"Figure « {libelle} » non produite : "
                          f"données insuffisantes.")
            else:
                print(f"  ✔️  {libelle}")
            return fig, extra
        except Exception as e:
            _signaler(f"Figure « {libelle} » en erreur — {str(e)[:130]}")
            return None, None

    # ── Production des figures ──
    fig_1a, infos = _produire("Présence des EEE",
                              lambda: _figure_1a_presence(table, gdf_EEE,
                                                          colonne_id, pied))
    fig_1b, _ = _produire("Espèces par nombre de tronçons",
                          lambda: _figure_1b_par_espece(table, gdf_EEE,
                                                        colonne_id, pied))
    fig_1c, _ = _produire("Ampleur par espèce",
                          lambda: _figure_1c_ampleur(table, colonne_id,
                                                     df_caracterisation, pied))
    fig_2, taux = _produire("Poids des enjeux",
                            lambda: _figure_2_enjeux(table, pied, maxima))
    fig_3, _ = _produire("Recouvrement des têtes de classement",
                         lambda: _figure_3_recouvrement(table, colonne_id, pied))
    fig_4, _ = _produire("Score et ampleur par tronçon",
                         lambda: _figure_4_nuage(table, colonne_id, pied, maxima))
    fig_5, _ = _produire("Forme des populations",
                         lambda: _figure_5_compacite(df_caracterisation, pied))

    # ── Cartes de cadrage ──
    infos = infos or {}
    cartes = [_carte_stat(
        "Tronçons analysés", _nb(infos.get("total", len(table))),
        "Périmètre du traitement, après déduplication", "#1F4E79")]

    if infos.get("total"):
        cartes.append(_carte_stat(
            "Tronçons avec EEE enregistrée",
            _pc(infos.get("part", 0)),
            f"{_nb(infos.get('colonises', 0))} tronçons portent au moins "
            f"un point d'occurrence", COULEUR_NEUTRE))

    if "score_troncon_final" in table.columns:
        scores = table["score_troncon_final"].dropna()
        if len(scores) > 0:
            cartes.append(_carte_stat(
                "Score final médian", _dec(scores.median(), 1),
                f"sur un maximum théorique de {sum(maxima.values()):g} points",
                "#C1440E"))
    if taux:
        enjeu_max = max(taux, key=taux.get)
        cartes.append(_carte_stat(
            "Enjeu le plus saturé", LIBELLES_ENJEUX[enjeu_max],
            f"{_pc(taux[enjeu_max])} de son maximum théorique",
            COULEURS_ENJEUX[enjeu_max]))

    # ── Assemblage des sections ──
    # `compteur_figures` sert à n'embarquer la bibliothèque Plotly qu'une fois,
    # avec la première figure réellement produite (et non systématiquement
    # avec la première de la liste, qui pourrait avoir échoué).
    sections, navigation = [], []
    compteur_figures = 0

    def _ajouter(identifiant, titre_nav, titre, paragraphes, fig, nom_export,
                 supplement=""):
        nonlocal compteur_figures
        premiere = (fig is not None and compteur_figures == 0)
        if fig is not None:
            compteur_figures += 1
        sections.append(_bloc_section(identifiant, titre, paragraphes, fig,
                                      nom_export, premiere, supplement))
        navigation.append(f'<a href="#{identifiant}">{titre_nav}</a>')

    _ajouter(
        "presence", "1 · Présence",
        "1 · Une partie de mon réseau est-elle concernée ?",
        ["Premier temps : établir l'ampleur du problème à l'échelle du réseau.",
         "Ce graphique ne dit rien de la gravité, seulement de l'étendue. Un "
         "réseau colonisé à 90 % par des foyers ponctuels et un réseau colonisé "
         "à 30 % par des linéaires continus posent des problèmes très "
         "différents — les graphiques suivants apportent cette nuance."],
        fig_1a, "springe_1_presence_EEE")

    _ajouter(
        "especes", "2 · Espèces",
        "2 · Quelles espèces sont enregistrées, et sur combien de tronçons ?",
        ["Deuxième temps : savoir par quoi le réseau est concerné.",
         "L'information est directement opérationnelle. Les protocoles "
         "d'intervention, les périodes favorables, les filières d'élimination "
         "des déchets verts et les coûts diffèrent nettement selon l'espèce. "
         "Une espèce présente sur peu de tronçons peut justifier une action "
         "rapide si elle est en début de colonisation."],
        fig_1b, "springe_2_especes_par_troncon")

    _ajouter(
        "ampleur", "3 · Ampleur",
        "3 · À quel volume, et sous quelle forme de dispersion ?",
        ["Troisième temps : passer du nombre de tronçons au volume réel.",
         "Deux mesures différentes sont affichées côte à côte parce qu'elles "
         "ne se recouvrent pas. Le nombre de populations décrit la "
         "fragmentation, donc le nombre de foyers distincts à atteindre et le "
         "temps de déplacement entre eux. Le linéaire décrit le volume de "
         "matière à gérer. Un même linéaire peut correspondre à un chantier "
         "unique ou à une dizaine d'interventions dispersées."],
        fig_1c, "springe_3_ampleur_par_espece")

    _ajouter(
        "enjeux", "4 · Enjeux",
        "4 · Quel enjeu pèse le plus sur mon réseau ?",
        ["SPRINGE ne décide pas de l'enjeu de référence : c'est un choix de "
         "politique de gestion. Cette section informe ce choix.",
         "Les trois enjeux n'ayant ni le même nombre d'indicateurs ni le même "
         "score maximal, leurs scores bruts ne peuvent pas être comparés "
         "directement. La comparaison est donc faite en pourcentage du maximum "
         "atteignable, et complétée par la dispersion, qui révèle les enjeux "
         "concentrés sur un petit nombre de tronçons."],
        fig_2, "springe_4_poids_des_enjeux",
        supplement=_tableau_statistiques(table, maxima))

    _ajouter(
        "recouvrement", "5 · Recouvrement",
        "5 · Le choix de l'enjeu change-t-il la liste des tronçons ?",
        ["C'est la question qui détermine si l'arbitrage entre enjeux mérite "
         "d'être tranché avant d'aller plus loin.",
         "Si les tronçons aux scores les plus élevés sont largement les mêmes "
         "quel que soit l'enjeu retenu, le débat sur la pondération reste "
         "théorique. Si les listes sont disjointes, le choix de l'enjeu de "
         "référence détermine réellement où l'on intervient, et mérite d'être "
         "posé explicitement plutôt que subi.",
         "Ce graphique demande une lecture attentive : la note sous la figure "
         "en détaille le principe."],
        fig_3, "springe_5_recouvrement_enjeux")

    _ajouter(
        "nuage", "6 · Score et ampleur",
        "6 · Où se situe chaque tronçon, entre niveau d'enjeu et ampleur ?",
        ["La vue la plus détaillée : un point par tronçon, identifiable au "
         "survol de la souris.",
         "Le score seul ne suffit pas à décider. Deux tronçons au même score "
         "peuvent porter l'un quelques mètres de foyers isolés, l'autre "
         "plusieurs centaines de mètres de linéaire continu — ni le même "
         "budget, ni la même technique, ni la même urgence de terrain.",
         "Utilisez le zoom pour explorer une zone du nuage, et la légende pour "
         "masquer une classe de compacité. Le survol d'un point affiche "
         "l'identifiant du tronçon, le détail de son score par enjeu et la "
         "synthèse de ses populations : de quoi retrouver directement le "
         "tronçon dans le GeoPackage ou dans QGIS."],
        fig_4, "springe_6_score_et_ampleur")

    _ajouter(
        "populations", "7 · Populations",
        "7 · Quelle forme prennent les populations sur le terrain ?",
        ["Cette section ne hiérarchise rien : elle décrit la structure "
         "spatiale des foyers.",
         "C'est l'information qui conditionne la NATURE de l'intervention "
         "plutôt que son ordre. Des individus isolés en front de colonisation "
         "laissent envisager une éradication ; un linéaire continu installé "
         "relève du confinement et de la gestion des propagules. Un "
         "gestionnaire qui prépare un marché a besoin de cette lecture avant "
         "même de savoir quel tronçon vient en premier."],
        fig_5, "springe_7_forme_des_populations")

    if compteur_figures == 0:
        _signaler("Aucune figure n'a pu être produite : page HTML non écrite.")
        return None

    # ── Page complète ──
    # Les accolades de la feuille de style seraient interprétées par une
    # f-string : on assemble donc par concaténation et `.format` ciblé, en
    # insérant le CSS et le JS comme des blocs déjà constitués.
    page = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SPRINGE — Résultats</title>
<style>""" + FEUILLE_DE_STYLE + """</style>
</head>
<body>
<div class="conteneur">

    <header>
        <h1>SPRINGE — lecture des résultats</h1>
        <p class="sous-titre">""" + _echapper(pied) + """</p>
        <nav>""" + "".join(navigation) + """</nav>
    </header>

    <div class="grille-stats">""" + "".join(cartes) + """</div>

    """ + "".join(sections) + """

    <footer>
        """ + _echapper(pied) + """<br>
        Les graphiques décrivent l'état du réseau tel que les données le
        documentent. Ils ne constituent ni un ordre d'intervention, ni une
        prescription de gestion : l'arbitrage relève du gestionnaire.<br>
        Se reporter à la notice de lecture pour les taux de renseignement
        et les limites des données mobilisées.
    </footer>

</div>
<script>""" + SCRIPT_TELECHARGEMENT + """</script>
</body>
</html>"""

    chemin = dossier / "graphiques_SPRINGE.html"
    # `encoding="utf-8"` explicite : sans lui, Windows écrit en cp1252 et les
    # accents des titres et notes de lecture ressortent en caractères parasites.
    chemin.write_text(page, encoding="utf-8")

    taille_mo = chemin.stat().st_size / (1024 * 1024)
    print(f"\n📊 {compteur_figures} figure(s) — page écrite : {chemin}")
    print(f"   Taille : {taille_mo:.1f} Mo (bibliothèque Plotly embarquée, "
          f"la page s'ouvre sans accès internet)\n")
    return str(chemin)
