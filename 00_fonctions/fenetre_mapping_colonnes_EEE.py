# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
Fonction "fenetre_mapping_colonnes_EEE"
Date : 2026-09-08
Objectif : (1) vérifier que la couche de points EEE suit bien le protocole
           national de recensement, puis (2) demander à l'utilisateur quelle
           colonne de sa couche porte chacune des informations descriptives
           attendues par ce protocole.
═══════════════════════════════════════════════════════════════════

CONTEXTE / POURQUOI CETTE FENÊTRE EXISTE :

Deux problèmes distincts, traités par les deux écrans de cette fenêtre.

--- Problème 1 : toutes les couches ne suivent pas le protocole -----------
La caractérisation des populations d'EEE repose entièrement sur une
hypothèse : les données ont été collectées selon

    Albert, A. (coord.) 2017. Protocole d'acquisition de données sur les
    plantes exotiques envahissantes le long du réseau routier national.
    Fédération des Conservatoires botaniques nationaux, Montreuil. 24 p.
    https://especes-exotiques-envahissantes.fr/wp-content/uploads/2023/01/
    fcbn-dit_eee_protocolerecensement_25072017.pdf

Ce protocole définit un point comme une POPULATION (règle des 50 m), et non
comme une plante. Si la couche vient d'une autre source (INPN, relevés
locaux, inventaires ponctuels), un point peut être une plante, un foyer, ou
tout autre chose : additionner ces objets produirait un nombre sans référent.

D'où le choix structurant CS-3 : PAS DE CALCUL SI LA SOURCE N'EST PAS
CONFORME. Un résultat non interprétable est plus nuisible qu'une absence de
résultat. Une seconde voie de calcul adaptée aux autres sources est
envisageable, mais elle est hors du périmètre de la version du 30/09/2026.

--- Problème 2 : les noms de colonnes ne sont pas normalisés --------------
Le protocole normalise les VARIABLES et leurs MODALITÉS, pas les noms de
colonnes des couches diffusées. Ceux-ci varient selon la DIR, l'outil
d'export et le millésime. Un nom codé en dur ('largeur', 'longueur',
'densite') ne fonctionnerait que pour le jeu de test actuel : il casse
silencieusement -- ou plante -- dès qu'un autre DIR fournit sa couche.

--- Parti pris repris de fenetre_mapping_especes -------------------------
AUCUNE PRÉ-SÉLECTION AUTOMATIQUE. Même quand une colonne s'appelle
exactement 'largeur', elle n'est pas cochée d'avance : c'est l'utilisateur
qui valide explicitement chaque association. Une pré-sélection ferait
valider par défaut une correspondance que le gestionnaire n'a pas examinée,
ce qui est précisément ce que la fenêtre existe pour éviter.

La détection automatique sert uniquement au CONTRÔLE DE CONFORMITÉ de
l'écran 2 : elle vérifie que les modalités de la colonne déclarée
correspondent au protocole. Elle ne devine jamais la colonne.

Sortie de mapping_interactif_colonnes_EEE() :
    - conforme_protocole : bool. Si False, l'appelant NE DOIT PAS appeler
      caracteriser_populations_EEE (choix structurant CS-3).
    - mapping_colonnes : dict {information_attendue : nom_de_colonne ou None}
      directement consommable par caracteriser_populations_EEE.
    - rapport_conformite : dict de traçabilité (modalités trouvées, taux de
      reconnaissance par colonne) à verser au rapport d'exécution.
"""

import tkinter as tk
from tkinter import ttk          # ttk = widgets "modernes" ; contient Combobox
from tkinter import messagebox   # importé explicitement plutôt que via un
                                 # import transitif depuis un autre module

# On réutilise les constantes du module de calcul plutôt que de les recopier :
# une seule définition des modalités canoniques, dans un seul fichier. Si le
# protocole évolue, on ne modifie qu'un endroit.
import caracteriser_populations_EEE as cpe


# ----------------------------------------------------------------------------
# Description des informations attendues.
#
# Chaque entrée décrit UNE information du protocole :
#   - 'libelle'    : texte affiché à l'utilisateur
#   - 'aide'       : précision affichée en gris sous le libellé
#   - 'requis'     : True  -> son absence bloque tout le calcul
#                    False -> son absence supprime seulement certains champs
#   - 'modalites'  : liste des modalités canoniques attendues, ou None si la
#                    colonne est numérique / à valeurs libres (donc non
#                    contrôlable par comparaison de modalités)
#   - 'perte'      : ce qui est perdu si la colonne est déclarée absente,
#                    affiché pour que le choix soit éclairé
#
# Le niveau requis/facultatif applique le choix structurant CS-5. En
# particulier, 'evaluation' est FACULTATIF : vérification faite, il n'alimente
# aucun comptage, aucune agrégation et aucun calcul géométrique -- il ne sert
# qu'à une information de traçabilité. Le rendre obligatoire bloquerait le
# calcul pour un champ non structurant.
# ----------------------------------------------------------------------------
INFORMATIONS_ATTENDUES = {
    'largeur': {
        'libelle': "Largeur moyenne de la population",
        'aide': "3 classes : moins de 1 m / 1 à 3 m / plus de 3 m",
        'requis': True,
        'modalites': cpe.MODALITES_LARGEUR,
        'perte': None,
    },
    'longueur': {
        'libelle': "Longueur approximative de la population",
        'aide': "3 classes : moins de 5 m / 5 à 20 m / plus de 20 m",
        'requis': True,
        'modalites': cpe.MODALITES_LONGUEUR,
        'perte': None,
    },
    'compacite': {
        'libelle': "Compacité de la population",
        'aide': ("3 modalités : individus isolés / taches discontinues / "
                 "population continue.\n"
                 "Nommée « densité des individus de la population » dans le "
                 "protocole."),
        'requis': True,
        'modalites': cpe.MODALITES_COMPACITE,
        'perte': None,
    },
    'abscisse': {
        'libelle': "Abscisse curviligne le long de la route",
        'aide': "Valeur numérique en mètres (ex. colonne 'abscml' du SI ROUTE)",
        'requis': False,
        'modalites': None,
        'perte': ("les 4 descripteurs de répartition (étendue occupée, part du "
                  "tronçon occupée, écarts entre populations)"),
    },
    'localisation': {
        'libelle': "Localisation sur la dépendance verte",
        'aide': "Terre-plein central / accotement / fossé / talus…",
        'requis': False,
        'modalites': None,
        'perte': "le champ 'localisation_dominante'",
    },
    'evaluation': {
        'libelle': "Évaluation du relevé",
        'aide': "2 modalités : certain / incertain",
        'requis': False,
        'modalites': ['Certain', 'Incertain'],
        'perte': "le comptage des relevés incertains",
    },
    'date': {
        'libelle': "Date du relevé",
        'aide': "Format JJ/MM/AAAA",
        'requis': False,
        'modalites': None,
        'perte': "les années de relevé et l'avertissement sur l'ancienneté",
    },
}

# Libellé de l'option "cette colonne n'existe pas dans ma couche", proposée
# uniquement pour les informations facultatives.
COLONNE_ABSENTE = "— colonne absente de ma couche —"

# Seuil de reconnaissance des modalités, en pourcentage.
# En dessous, on considère que la colonne déclarée ne suit vraisemblablement
# pas le protocole (mauvaise colonne, ou référentiel différent) et on demande
# une confirmation explicite plutôt que de calculer sur du sable.
#
# Pourquoi 50 % et pas plus haut : le jeu national de référence présente des
# taux de non-renseigné réels de 15 à 18 % sur ces colonnes, et une couche
# locale peut faire pire sans cesser d'être conforme. Un seuil trop strict
# bloquerait des données légitimes ; 50 % ne se déclenche que si la MAJORITÉ
# des valeurs est inexploitable, ce qui n'arrive pas sur une bonne colonne.
SEUIL_RECONNAISSANCE_PCT = 50


def demander_conformite_protocole(gdf_EEE):
    """
    ÉCRAN 1 : la couche suit-elle le protocole national de recensement ?

    C'est la première des deux barrières du choix structurant CS-3. La seconde
    est le contrôle automatique des modalités, à l'écran 2.

    Retour
    ------
    bool : True si l'utilisateur déclare la couche conforme,
           False s'il déclare qu'elle ne l'est pas,
           None s'il ferme la fenêtre sans répondre (à traiter comme un arrêt).
    """
    # Dictionnaire "boîte aux lettres" pour récupérer le résultat depuis les
    # fonctions imbriquées : une fonction interne ne peut pas réassigner une
    # variable de la fonction englobante avec un simple "=" (il faudrait
    # "nonlocal", plus verbeux qu'un dict ici).
    resultat = {"reponse": None}

    root = tk.Tk()
    root.withdraw()   # on cache la racine : seule la Toplevel doit être visible

    fenetre = tk.Toplevel(root)
    # Barre de titre : numéro d'étape ajouté en 26.9.0.
    fenetre.title("SPRINGE — Étape 4/4 · Conformité au protocole de recensement")
    fenetre.resizable(False, False)

    # -- Titre de l'étape (ajout 26.9.0) --
    tk.Label(
        fenetre,
        text="Étape 4 / 4 — Compréhension des données d'entrée (suite)",
        font=("Arial", 12, "bold")
    ).grid(row=0, column=0, columnspan=2, padx=20, pady=(12, 8))

    # -- Question posée --
    # Version 26.9.0 : les "\n" manuels sont retirés de tous les paragraphes
    # de cet écran. wraplength coupe les lignes automatiquement ; seuls les
    # "\n\n" qui SÉPARENT deux paragraphes sont conservés.
    tk.Label(
        fenetre,
        text="Vos données de présence EEE suivent-elles le protocole national "
             "de recensement le long du réseau routier national ?",
        justify="left", font=("TkDefaultFont", 10, "bold"), wraplength=540
    ).grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")

    # -- Présentation du protocole (gris, inchangée sur le fond) --
    tk.Label(
        fenetre,
        text="Référence : Albert, A. (coord.) 2017. Protocole d'acquisition de données "
             "sur les plantes exotiques envahissantes le long du réseau routier national. "
             "Fédération des Conservatoires botaniques nationaux, Montreuil, 24 p.\n\n"
             "Ce protocole a servi au recensement des DIR de 2018-2020. Il caractérise "
             "chaque population par une classe de largeur, une classe de longueur et une "
             "modalité de compacité (individus isolés / taches / continue).\n\n"
             "Point déterminant : dans ce protocole, UN POINT = UNE POPULATION, et non "
             "une plante. Deux taches d'une même espèce distantes de moins de 50 m sont "
             "enregistrées comme une seule population.",
        fg="gray30", justify="left", wraplength=540
    ).grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")

    # -- Conséquence d'un « non » : EN ROUGE (26.9.0) --
    # Paragraphe isolé dans son propre Label pour pouvoir le colorer seul : un
    # Label Tkinter n'a qu'une couleur de texte. Texte élargi en 26.9.0 : un
    # protocole de recensement DIFFÉRENT fait aussi perdre la caractérisation,
    # pas seulement une autre source de données.
    tk.Label(
        fenetre,
        text="⚠️  Si vos données suivent un protocole de recensement différent, ou "
             "proviennent d'une autre source (INPN, relevés locaux, inventaires "
             "ponctuels), la caractérisation des populations ne sera pas calculée. "
             "Le reste de SPRINGE (indicateurs MS, N, P) fonctionnera normalement.",
        fg="#c62828", justify="left", wraplength=540
    ).grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")

    # -- Motif du choix structurant CS-3 (reste en gris foncé) --
    tk.Label(
        fenetre,
        text="Motif : sans connaître l'unité d'observation, un comptage de points n'a pas "
             "de signification définie. Un point peut être une plante, un foyer ou une "
             "population selon la source. Mieux vaut ne rien produire qu'un chiffre "
             "ininterprétable.",
        fg="gray20", justify="left", wraplength=540
    ).grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="w")

    def repondre_oui():
        resultat["reponse"] = True
        fenetre.destroy()

    def repondre_non():
        resultat["reponse"] = False
        fenetre.destroy()

    tk.Button(
        fenetre, text="✔️  Oui, mes données suivent ce protocole",
        command=repondre_oui, width=38
    ).grid(row=5, column=0, padx=20, pady=(0, 15))   # row 3 → 5 (26.9.0)

    tk.Button(
        fenetre, text="✖️  Non / je ne sais pas",
        command=repondre_non, width=28
    ).grid(row=5, column=1, padx=20, pady=(0, 15))   # row 3 → 5 (26.9.0)

    # -- Forcer la fenêtre au premier plan --
    # Sans cela, la fenêtre peut s'ouvrir derrière la console ou l'IDE, et
    # l'utilisateur croit que le script est bloqué. attributes("-topmost") est
    # remis à False après 200 ms pour ne pas garder la fenêtre en surimpression
    # de tout le bureau pendant qu'elle est ouverte.
    fenetre.lift()
    fenetre.attributes("-topmost", True)
    fenetre.after(200, lambda: fenetre.attributes("-topmost", False))
    fenetre.focus_force()

    fenetre.grab_set()          # rend la fenêtre modale : rien d'autre ne répond
    root.wait_window(fenetre)   # bloque le script tant qu'elle est ouverte
    root.destroy()

    return resultat["reponse"]


def _analyser_modalites(gdf_EEE, nom_colonne, modalites_attendues):
    """
    Analyse une colonne : quelles valeurs contient-elle, et combien sont
    reconnues comme des modalités du protocole ?

    Sert au contrôle automatique de conformité (seconde barrière de CS-3).

    Retour : dict {taux_reconnaissance, valeurs_trouvees, nb_lignes}
    ou None si la colonne n'a pas de modalités contrôlables (numérique, date,
    ou liste de valeurs ouverte).
    """
    if modalites_attendues is None:
        return None

    serie = gdf_EEE[nom_colonne]
    # On réutilise la normalisation du module de calcul : même traitement des
    # accents et de la casse ici et au moment du calcul, donc pas de surprise
    # entre ce que la fenêtre annonce et ce que le calcul reconnaît.
    formes_attendues = {cpe._normaliser_texte(m) for m in modalites_attendues}
    normalisee = serie.map(cpe._normaliser_texte)

    # Les valeurs vides sont des trous de saisie normaux : on les exclut du
    # calcul du taux, sinon une couche à 18 % de trous (taux national réel)
    # ferait chuter le taux de reconnaissance sans que la colonne soit en cause.
    non_vides = normalisee[normalisee != '']
    if len(non_vides) == 0:
        taux = 0.0
    else:
        taux = 100.0 * non_vides.isin(formes_attendues).mean()

    return {
        'taux_reconnaissance': round(taux, 1),
        'valeurs_trouvees': sorted(set(serie.astype(str).str.strip()) - {''})[:10],
        'nb_lignes': len(serie),
    }


def demander_colonnes(gdf_EEE):
    """
    ÉCRAN 2 : quelle colonne porte chaque information attendue ?

    Une ligne par information, avec un menu déroulant listant les colonnes de
    la couche. Aucune n'est pré-sélectionnée.

    Retour
    ------
    dict {information : nom_de_colonne ou None}, ou None si l'utilisateur a
    fermé la fenêtre sans valider.
    """
    # On exclut la colonne de géométrie : elle ne peut porter aucune de ces
    # informations, autant ne pas polluer les listes déroulantes.
    try:
        nom_geometrie = gdf_EEE.geometry.name
    except AttributeError:
        # gdf_EEE peut être un DataFrame simple lors d'un test hors QGIS.
        nom_geometrie = None
    colonnes_candidates = [c for c in gdf_EEE.columns if c != nom_geometrie]

    resultat = {"mapping": None}

    root = tk.Tk()
    root.withdraw()

    fenetre = tk.Toplevel(root)
    # Barre de titre : numéro d'étape ajouté en 26.9.0.
    fenetre.title("SPRINGE — Étape 4/4 · Colonnes de caractérisation des populations EEE")
    fenetre.resizable(False, False)

    # -- Titre de l'étape (ajout 26.9.0) --
    tk.Label(
        fenetre,
        text="Étape 4 / 4 — Compréhension des données d'entrée (suite)",
        font=("Arial", 12, "bold")
    ).grid(row=0, column=0, columnspan=3, padx=20, pady=(12, 8))

    tk.Label(
        fenetre,
        text="Pour chaque information du protocole, indiquez la colonne "
             "correspondante dans votre couche de points EEE :",
        justify="left", font=("TkDefaultFont", 10, "bold"), wraplength=620
    ).grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 5), sticky="w")   # row +1

    # Phrase d'aide harmonisée en 26.9.0 avec la fenêtre « Colonne du nom
    # d'espèce » (fenetre_mapping_especes) : même consigne, même formulation.
    tk.Label(
        fenetre,
        text="💡 En cas de doute, ouvrez la table attributaire de la couche renseignée "
             "pour vérifier le contenu des colonnes (ou variables) avant de répondre.\n"
             "Aucune colonne n'est présélectionnée : chaque correspondance doit être "
             "choisie explicitement.",
        fg="gray30", justify="left", wraplength=620
    ).grid(row=2, column=0, columnspan=3, padx=20, pady=(0, 10), sticky="w")   # row +1

    # ------------------------------------------------------------------------
    # Zone défilante : le nombre d'informations est fixe (7), mais les libellés
    # d'aide sont longs et la fenêtre doit rester utilisable sur un petit écran.
    # Même principe que dans fenetre_mapping_especes : un Canvas affiche une
    # "fenêtre" sur une Frame interne potentiellement plus haute que la zone
    # visible, une Scrollbar pilote le défilement.
    # ------------------------------------------------------------------------
    conteneur = tk.Frame(fenetre)
    conteneur.grid(row=3, column=0, columnspan=3, padx=20, pady=5)   # row +1 (26.9.0)

    # height 380 → 340 px en 26.9.0 : compense la ligne de titre ajoutée,
    # pour que le bouton Valider reste visible sur un écran d'ordinateur portable.
    canvas = tk.Canvas(conteneur, width=640, height=340, highlightthickness=0)
    scrollbar = tk.Scrollbar(conteneur, orient="vertical", command=canvas.yview)
    frame_liste = tk.Frame(canvas)

    # À chaque changement de taille de frame_liste, on recalcule la zone
    # défilable du canvas pour que la scrollbar corresponde au contenu réel.
    frame_liste.bind(
        "<Configure>",
        lambda evenement: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=frame_liste, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    # -- Une ligne par information attendue --
    variables_choix = {}
    ligne_courante = 0

    for cle, description in INFORMATIONS_ATTENDUES.items():
        # Libellé principal, avec mention explicite du caractère requis
        mention = "  (requis)" if description['requis'] else "  (facultatif)"
        couleur = "black" if description['requis'] else "gray20"
        tk.Label(
            frame_liste,
            text=description['libelle'] + mention,
            anchor="w", justify="left", fg=couleur,
            font=("TkDefaultFont", 9, "bold")
        ).grid(row=ligne_courante, column=0, columnspan=2,
               padx=(0, 10), pady=(8, 0), sticky="w")
        ligne_courante += 1

        # Texte d'aide : rappelle les modalités attendues, ce qui permet à
        # l'utilisateur de reconnaître la bonne colonne sans quitter la fenêtre.
        tk.Label(
            frame_liste, text=description['aide'],
            anchor="w", justify="left", fg="gray40", wraplength=560
        ).grid(row=ligne_courante, column=0, columnspan=2, sticky="w")
        ligne_courante += 1

        # Pour un champ facultatif, on précise ce que coûte son absence : le
        # gestionnaire doit pouvoir arbitrer en connaissance de cause.
        if not description['requis'] and description['perte']:
            tk.Label(
                frame_liste,
                text=f"Si absente : SPRINGE ne produira pas {description['perte']}.",
                anchor="w", justify="left", fg="gray50", wraplength=560
            ).grid(row=ligne_courante, column=0, columnspan=2, sticky="w")
            ligne_courante += 1

        # Menu déroulant. StringVar laissée VIDE : aucune présélection, même
        # si une colonne porte exactement le nom attendu (parti pris repris de
        # fenetre_mapping_especes).
        valeurs_proposees = list(colonnes_candidates)
        if not description['requis']:
            valeurs_proposees = [COLONNE_ABSENTE] + valeurs_proposees

        var = tk.StringVar(value="")
        combo = ttk.Combobox(
            frame_liste, textvariable=var,
            values=valeurs_proposees,
            state="readonly",   # empêche la saisie libre : uniquement la liste
            width=45
        )
        combo.grid(row=ligne_courante, column=0, pady=(2, 6), sticky="w")
        variables_choix[cle] = var
        ligne_courante += 1

    # ------------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------------
    def valider():
        # 1) Aucune ligne ne doit rester sans réponse. Pour les facultatives,
        #    "colonne absente" EST une réponse valide -- mais il faut l'avoir
        #    choisie, pas l'avoir laissée vide par inattention.
        manquants = [
            INFORMATIONS_ATTENDUES[cle]['libelle']
            for cle, var in variables_choix.items()
            if var.get() == ""
        ]
        if manquants:
            messagebox.showwarning(
                "Réponses incomplètes",
                "Veuillez répondre pour chaque information listée.\n"
                "Pour les informations facultatives, choisissez "
                f"« {COLONNE_ABSENTE} » si votre couche ne les contient pas.\n\n"
                "Sans réponse : " + ", ".join(manquants)
            )
            return

        # 2) Une même colonne ne peut pas porter deux informations différentes.
        #    C'est presque toujours une erreur de saisie, et le laisser passer
        #    produirait des comptages incohérents sans message d'erreur.
        choix_reels = [v.get() for v in variables_choix.values()
                       if v.get() != COLONNE_ABSENTE]
        doublons = {c for c in choix_reels if choix_reels.count(c) > 1}
        if doublons:
            messagebox.showwarning(
                "Colonne utilisée plusieurs fois",
                "Une même colonne a été désignée pour plusieurs informations :\n"
                + ", ".join(f"'{c}'" for c in doublons)
                + "\n\nChaque information doit avoir sa propre colonne."
            )
            return

        resultat["mapping"] = {
            cle: (None if var.get() == COLONNE_ABSENTE else var.get())
            for cle, var in variables_choix.items()
        }
        fenetre.destroy()

    tk.Button(fenetre, text="✔️ Valider", command=valider).grid(
        row=4, column=0, columnspan=3, pady=15   # row +1 (26.9.0)
    )

    fenetre.lift()
    fenetre.attributes("-topmost", True)
    fenetre.after(200, lambda: fenetre.attributes("-topmost", False))
    fenetre.focus_force()

    fenetre.grab_set()
    root.wait_window(fenetre)
    root.destroy()

    return resultat["mapping"]


def mapping_interactif_colonnes_EEE(gdf_EEE):
    """
    Fonction principale, à appeler depuis le script principal.

    Enchaîne les deux écrans, puis exécute le contrôle automatique des
    modalités qui constitue la seconde barrière du choix structurant CS-3.

    Paramètres
    ----------
    gdf_EEE : GeoDataFrame des points de présence EEE, structure arbitraire.

    Retour
    ------
    conforme_protocole : bool -- si False, l'appelant NE DOIT PAS appeler
        caracteriser_populations_EEE.
    mapping_colonnes : dict {information : nom_de_colonne ou None}, ou None si
        la couche n'est pas conforme.
    rapport_conformite : dict de traçabilité pour le rapport d'exécution.

    Contrairement à fenetre_mapping_especes, la fermeture d'une fenêtre sans
    valider ne lève PAS d'exception : elle est traitée comme un « non ». Motif :
    la caractérisation est un axe descriptif complémentaire, pas un pré-requis
    du scoring. Arrêter tout SPRINGE parce que le gestionnaire a fermé cette
    fenêtre serait disproportionné -- il perd la caractérisation, pas son run.
    """
    print("\n" + "=" * 70)
    print("CARACTÉRISATION DES POPULATIONS EEE — paramétrage")
    print("=" * 70)

    rapport_conformite = {
        'conforme_declare': None,
        'colonnes_retenues': {},
        'controle_modalites': {},
    }

    # --- Écran 1 : conformité au protocole --------------------------------
    conforme = demander_conformite_protocole(gdf_EEE)
    rapport_conformite['conforme_declare'] = conforme

    if conforme is None:
        print("⚠️  Fenêtre fermée sans réponse : la caractérisation des "
              "populations ne sera pas calculée.")
        return False, None, rapport_conformite

    if conforme is False:
        print("ℹ️  Données déclarées non conformes au protocole Albert 2017.")
        print("    La caractérisation des populations ne sera pas calculée "
              "(choix structurant CS-3).")
        print("    Le reste de SPRINGE (indicateurs MS, N, P) n'est pas affecté.")
        return False, None, rapport_conformite

    # --- Écran 2 : identification des colonnes ----------------------------
    mapping_colonnes = demander_colonnes(gdf_EEE)

    if mapping_colonnes is None:
        print("⚠️  Fenêtre fermée sans validation : la caractérisation des "
              "populations ne sera pas calculée.")
        return False, None, rapport_conformite

    rapport_conformite['colonnes_retenues'] = dict(mapping_colonnes)

    print("✔️ Colonnes retenues :")
    for cle, colonne in mapping_colonnes.items():
        libelle = INFORMATIONS_ATTENDUES[cle]['libelle']
        print(f"   • {libelle:<45} → {colonne or '(absente)'}")

    # --- Contrôle automatique des modalités (seconde barrière de CS-3) ----
    # On vérifie que les colonnes déclarées contiennent bien les modalités du
    # protocole. Un taux de reconnaissance effondré signifie presque toujours
    # que la colonne désignée n'est pas la bonne, ou qu'elle suit un autre
    # référentiel -- deux cas où calculer produirait des comptages faux.
    colonnes_suspectes = []

    for cle, colonne in mapping_colonnes.items():
        if colonne is None:
            continue
        analyse = _analyser_modalites(
            gdf_EEE, colonne, INFORMATIONS_ATTENDUES[cle]['modalites']
        )
        if analyse is None:
            continue   # colonne numérique ou à valeurs libres : non contrôlable

        rapport_conformite['controle_modalites'][cle] = analyse
        print(f"   • Contrôle '{colonne}' : "
              f"{analyse['taux_reconnaissance']} % des valeurs non vides "
              f"correspondent aux modalités du protocole")

        if analyse['taux_reconnaissance'] < SEUIL_RECONNAISSANCE_PCT:
            colonnes_suspectes.append((cle, colonne, analyse))

    if colonnes_suspectes:
        # On ne bloque pas d'autorité : le gestionnaire peut avoir une raison
        # légitime (variante locale de nommage des modalités). Mais il doit
        # confirmer explicitement, en voyant les valeurs réellement trouvées.
        details = []
        for cle, colonne, analyse in colonnes_suspectes:
            valeurs = ", ".join(f"'{v}'" for v in analyse['valeurs_trouvees'][:6])
            details.append(
                f"• {INFORMATIONS_ATTENDUES[cle]['libelle']} → colonne '{colonne}'\n"
                f"  {analyse['taux_reconnaissance']} % de valeurs reconnues\n"
                f"  Valeurs trouvées : {valeurs}\n"
                f"  Attendu : {', '.join(INFORMATIONS_ATTENDUES[cle]['modalites'])}"
            )

        root = tk.Tk()
        root.withdraw()
        poursuivre = messagebox.askyesno(
            "Modalités inattendues",
            "Les colonnes suivantes ne contiennent pas les modalités attendues "
            "par le protocole :\n\n"
            + "\n\n".join(details)
            + "\n\nLes valeurs non reconnues seront comptées en « non renseigné », "
              "ce qui videra une grande partie des résultats.\n\n"
              "Voulez-vous poursuivre malgré tout ?"
        )
        root.destroy()

        if not poursuivre:
            print("ℹ️  Paramétrage abandonné suite au contrôle des modalités.")
            return False, None, rapport_conformite

        rapport_conformite['poursuite_malgre_alerte'] = True
        print("⚠️  Poursuite confirmée malgré des modalités inattendues.")

    return True, mapping_colonnes, rapport_conformite
