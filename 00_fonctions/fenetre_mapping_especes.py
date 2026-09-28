# -*- coding: utf-8 -*-
"""
Created on 2026-09-07
@author: Antoine

═══════════════════════════════════════════════════════════════════
Fonction "fenetre_mapping_especes"
Date : 2026-09-07
Objectif : demander interactivement à l'utilisateur (1) quelle colonne de
           gdf_EEE contient le nom d'espèce, puis (2) à quelle espèce cible
           du référentiel SPRINGE correspond chaque valeur trouvée dans
           cette colonne.
═══════════════════════════════════════════════════════════════════

CONTEXTE / POURQUOI CETTE FENÊTRE EXISTE :
La couche de points EEE (gdf_EEE) est fournie par chaque DIR gestionnaire,
depuis son propre système (export CamAlien, base interne...). Le nom de la
colonne "espèce" et les valeurs qu'elle contient (ex: 'Renouees', 'renouée',
'RJ', un code numérique...) varient donc d'un DIR à l'autre. Un mapping figé
en dur dans le code (colonne 'plante' + 5 valeurs fixes, comme c'était fait
avant) ne fonctionne que pour le jeu de données de test actuel : il casse
silencieusement -- ou plante -- dès qu'un autre DIR fournit une couche
structurée différemment.

Cette fenêtre ne fait AUCUNE déduction automatique : c'est l'utilisateur qui
valide explicitement, pour chaque valeur brute rencontrée, à quelle espèce
cible elle correspond. Rien n'est présélectionné par défaut.

Sortie de mapping_interactif_especes() :
    - gdf_EEE_mapping : copie de gdf_EEE + colonne 'species_name_sci' ajoutée
      (nom scientifique, celui utilisé pour la jointure avec EEE_SHEET dans
      tout le reste du pipeline de scoring)
    - colonne_espece  : str, nom de la colonne source choisie par l'utilisateur
      (à conserver pour le rapport d'exécution -- traçabilité du choix)
    - mapping_valeurs : dict {valeur_brute_str : species_name_sci} appliqué
      (idem, traçabilité -- utile si un manager doit justifier/revoir son choix)

            ===========
            ! IMPORTANT !
            ===========
    Cette fenêtre ne fait QUE le mapping. Au 2026-09-07, les fichiers
    calculer_MS1_impact.py, calculer_MS2_impact.py, calculer_MS3_impact.py,
    calculer_N2_impact.py et calculer_P1_impact.py contiennent CHACUN leur
    propre dict de mapping figé en dur sur la colonne 'plante' (copié-collé
    identique dans les 5 fichiers). Tant que ces 5 fichiers n'ont pas été
    harmonisés pour utiliser directement la colonne 'species_name_sci' déjà
    présente dans gdf_EEE (au lieu de re-mapper eux-mêmes depuis 'plante'),
    le résultat de cette fenêtre n'est PAS répercuté sur le calcul des
    indicateurs. Harmonisation prévue dans un second temps (décision du
    2026-09-07) -- ne pas oublier.
"""

import tkinter as tk
from tkinter import ttk         # ttk = version "moderne" des widgets tkinter ;
                                 # contient Combobox (liste déroulante), absente de tkinter de base
from tkinter import messagebox  # importé explicitement (plutôt que de compter sur un import
                                 # transitif via filedialog/simpledialog ailleurs dans le script)


# ----------------------------------------------------------------------------
# Référentiel des 5 espèces cibles SPRINGE (codé en dur -- décision du 2026-09-07 :
# on préfère la simplicité à une dérivation dynamique depuis EEE_SHEET, qui
# aurait nécessité de charger EEE_SHEET avant gdf_EEE dans le script principal)
#
# clé   = libellé "parlant" affiché à l'utilisateur dans la fenêtre
# valeur = species_name_sci correspondant, tel qu'utilisé dans EEE_SHEET et
#          dans toutes les jointures du pipeline de scoring (MS1, MS2, MS3,
#          N1, N2, P1, P2, P3, P4)
# ----------------------------------------------------------------------------
CATEGORIES_CIBLES = {
    "Ailante glanduleux": "Ailanthus altissima",
    "Ambroisie à feuilles d'armoise": "Ambrosia artemisiifolia",
    "Berce du Caucase": "Heracleum mantegazzianum",
    "groupe des Renouées asiatiques": "Reynoutria sp",
    "Autres": "EEE autre",
}

# ----------------------------------------------------------------------------
# Traduction des codes FIXES renvoyés par fenetre_selection_especes.py
# ('Renouees', 'Ailante', 'Ambroisie', 'BerceCaucase', 'Autre') vers
# species_name_sci.
#
# Ces codes ne sont PAS des valeurs brutes issues d'une couche EEE : ce sont
# les options d'une fenêtre de sélection à choix fixes (Partie 1, avant tout
# chargement de données), qui désignent toujours les 5 mêmes espèces cibles
# quelle que soit la couche fournie par le DIR. On peut donc les traduire
# avec un dict figé, sans repasser par une fenêtre interactive -- contrairement
# au mapping de la colonne brute de gdf_EEE (CATEGORIES_CIBLES ci-dessus), qui
# lui dépend entièrement de la structure de la couche fournie.
# ----------------------------------------------------------------------------
CODES_SELECTION_VERS_SCI = {
    "Renouees": "Reynoutria sp",
    "Ailante": "Ailanthus altissima",
    "Ambroisie": "Ambrosia artemisiifolia",
    "BerceCaucase": "Heracleum mantegazzianum",
    "Autre": "EEE autre",
}

# Libellé utilisé pour représenter les valeurs manquantes (NaN / vide) de la
# colonne espèce choisie, afin de les traiter comme une valeur "normale" à
# mapper explicitement -- et non les ignorer silencieusement.
# (on évite volontairement d'utiliser NaN comme clé de dictionnaire : en
# Python, nan != nan, donc un dict {nan: ...} est piégeux et peu fiable)
VALEUR_MANQUANTE = "(valeur manquante / vide)"


def demander_colonne_espece(gdf_EEE):
    """
    Étape 1 : demande à l'utilisateur quelle colonne de gdf_EEE contient le
    nom d'espèce EEE.

    Paramètres
    ----------
    gdf_EEE : GeoDataFrame des points de présence EEE (structure arbitraire)

    Retour
    ------
    str : nom de la colonne choisie, ou None si l'utilisateur a fermé la
          fenêtre sans valider (cas à gérer par l'appelant)
    """

    # On exclut la colonne de géométrie de la liste proposée : elle ne peut de
    # toute façon pas contenir un nom d'espèce, autant ne pas polluer le choix
    colonnes_candidates = [c for c in gdf_EEE.columns if c != gdf_EEE.geometry.name]

    # Dictionnaire "boîte aux lettres" pour récupérer le résultat depuis la
    # fonction imbriquée "valider" ci-dessous. On ne peut pas juste faire
    # "colonne_choisie = ..." dans valider() et la lire après : une fonction
    # imbriquée ne peut pas réassigner une variable de la fonction englobante
    # avec un simple "=" (il faudrait "nonlocal", plus verbeux qu'un dict ici)
    resultat = {"colonne": None}

    # ------------------------------------------------------------------------
    # Construction de la fenêtre
    # tk.Tk() = fenêtre racine (obligatoire pour tkinter, mais on la cache avec
    # withdraw() car seule la fenêtre Toplevel doit être visible)
    # ------------------------------------------------------------------------
    root = tk.Tk()
    root.withdraw()

    fenetre = tk.Toplevel(root)
    # Barre de titre : numéro d'étape ajouté en 26.9.0 (parcours en 4 étapes).
    fenetre.title("SPRINGE — Étape 4/4 · Colonne du nom d'espèce EEE")
    fenetre.resizable(False, False)

    # -- Titre de l'étape (ajout 26.9.0) --
    # Même format « Étape N / 4 — … » que toutes les fenêtres du parcours.
    tk.Label(
        fenetre,
        text="Étape 4 / 4 — Compréhension des données d'entrée (suite)",
        font=("Arial", 12, "bold")
    ).grid(row=0, column=0, padx=20, pady=(12, 8))

    # -- Consigne principale --
    # Version 26.9.0 : plus de "\n" manuel au milieu de la phrase ;
    # wraplength (en pixels) laisse Tkinter couper la ligne lui-même, à la
    # largeur de la liste, ce qui donne un paragraphe régulier.
    tk.Label(
        fenetre,
        text="Sélectionnez la colonne de votre couche de points EEE "
             "qui contient le nom de l'espèce :",
        justify="left", wraplength=420
    ).grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")

    # -- Note d'aide : suggérer de vérifier via la table attributaire --
    # Version 26.9.0 : texte reformulé et retours à la ligne manuels
    # supprimés (ils produisaient des lignes de longueurs très inégales,
    # parce qu'ils se cumulaient avec le retour automatique de wraplength).
    tk.Label(
        fenetre,
        text="💡 En cas de doute, ouvrez la table attributaire de la couche "
             "renseignée pour vérifier le contenu des colonnes (ou variables) "
             "avant de répondre.",
        fg="gray30", justify="left", wraplength=420
    ).grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")

    # -- Listbox des colonnes disponibles (sélection simple) --
    # exportselection=False : évite un bug classique de Listbox où la
    # sélection se désélectionne dès qu'on clique ailleurs dans la fenêtre
    # (par exemple sur le bouton Valider)
    # max(1, ...) : garde-fou si gdf_EEE n'avait (cas très improbable) aucune
    # colonne hors géométrie -- une Listbox de hauteur 0 est invalide
    liste_colonnes = tk.Listbox(
        fenetre,
        height=max(1, min(10, len(colonnes_candidates))),
        exportselection=False,
        width=50
    )
    # Couleurs alternées blanc / gris (ajout 26.9.0) pour aider la lecture :
    # l'œil suit plus facilement une ligne quand ses voisines sont d'une
    # autre teinte, surtout avec des noms de colonnes courts et semblables
    # (absplo, abspr, abscml…).
    # enumerate() fournit le numéro de ligne i en plus du nom de colonne ;
    # i % 2 == 1 est vrai une ligne sur deux (lignes 1, 3, 5…).
    # itemconfig(i, background=…) colore le fond de la seule ligne i.
    # La ligne sélectionnée garde la couleur de sélection habituelle (bleu) :
    # Tkinter la superpose au fond, le choix reste donc bien visible.
    COULEUR_LIGNE_GRISE = "#e8e8e8"
    for i, colonne in enumerate(colonnes_candidates):
        liste_colonnes.insert(tk.END, colonne)
        if i % 2 == 1:
            liste_colonnes.itemconfig(i, background=COULEUR_LIGNE_GRISE)
    liste_colonnes.grid(row=3, column=0, padx=20, pady=5)   # row décalé (+1) en 26.9.0

    # -- Callback du bouton Valider --
    def valider():
        selection = liste_colonnes.curselection()  # tuple des index sélectionnés (vide si rien choisi)
        if not selection:
            # on bloque la fermeture tant que rien n'est sélectionné : mieux
            # vaut forcer un choix explicite que de laisser passer un None
            messagebox.showwarning(
                "Sélection requise",
                "Veuillez sélectionner une colonne avant de valider."
            )
            return
        resultat["colonne"] = colonnes_candidates[selection[0]]
        fenetre.destroy()

    tk.Button(fenetre, text="✔️ Valider", command=valider).grid(
        row=4, column=0, pady=15   # row décalé (+1) en 26.9.0
    )

    # -- Forcer la fenêtre au premier plan --
    # Sur certains environnements (notamment Windows + IDE), une Toplevel peut
    # s'ouvrir SANS voler le focus et rester cachée derrière une autre fenêtre
    # -- donnant l'impression qu'"elle ne s'affiche pas" alors qu'elle existe.
    # lift() : place la fenêtre au-dessus des autres dans l'empilement de fenêtres
    # attributes("-topmost", True) : la force temporairement au tout premier plan
    # after(200, ...) : au bout de 200 ms, on redonne un comportement normal
    # (sinon la fenêtre resterait "toujours au-dessus" en permanence, ce qui
    # gênerait l'utilisateur pour consulter sa table attributaire QGIS à côté)
    fenetre.lift()
    fenetre.attributes("-topmost", True)
    fenetre.after(200, lambda: fenetre.attributes("-topmost", False))
    fenetre.focus_force()

    # -- Blocage de l'exécution tant que la fenêtre n'est pas fermée --
    # grab_set() : rend la fenêtre modale (empêche d'interagir avec le reste
    # tant qu'elle est ouverte) ; wait_window() : met le script en pause
    # jusqu'à la destruction de "fenetre" (bouton Valider OU croix de fermeture)
    fenetre.grab_set()
    root.wait_window(fenetre)
    root.destroy()

    return resultat["colonne"]


def demander_mapping_valeurs(gdf_EEE, colonne_espece):
    """
    Étape 2 : pour chaque valeur unique trouvée dans gdf_EEE[colonne_espece],
    demande à l'utilisateur à quelle espèce cible SPRINGE elle correspond.

    Paramètres
    ----------
    gdf_EEE : GeoDataFrame des points de présence EEE
    colonne_espece : str, nom de la colonne contenant le nom d'espèce brut
                     (déterminé par demander_colonne_espece)

    Retour
    ------
    dict {valeur_brute_str : species_name_sci}, ou None si fermeture sans
    validation complète
    """

    # ------------------------------------------------------------------------
    # Préparation des valeurs à mapper
    # ------------------------------------------------------------------------
    # .fillna(VALEUR_MANQUANTE) AVANT .astype(str) : les valeurs manquantes
    # deviennent une catégorie explicite "(valeur manquante / vide)" plutôt
    # que d'être ignorées silencieusement.
    # .astype(str) : uniformise le type (évite qu'une colonne mixte int/str
    # ne crée des doublons visuellement identiques mais de types différents,
    # et rend les valeurs utilisables telles quelles comme clés de dict et
    # comme "values" de Combobox)
    valeurs_brutes_str = gdf_EEE[colonne_espece].fillna(VALEUR_MANQUANTE).astype(str)

    # Nombre de points concernés par chaque valeur -- affiché à l'utilisateur
    # pour l'aider à juger l'importance de chaque catégorie : une valeur
    # bizarre avec 1 seul point est probablement une faute de frappe, avec
    # 500 points c'est probablement une vraie catégorie qu'il faut bien classer
    effectifs = valeurs_brutes_str.value_counts()

    # Ordre alphabétique : plus facile à parcourir visuellement qu'un ordre
    # arbitraire (celui d'apparition dans les données)
    valeurs_uniques = sorted(valeurs_brutes_str.unique().tolist())

    resultat = {"mapping": None}

    # ------------------------------------------------------------------------
    # Construction de la fenêtre
    # ------------------------------------------------------------------------
    root = tk.Tk()
    root.withdraw()

    fenetre = tk.Toplevel(root)
    # Barre de titre : numéro d'étape ajouté en 26.9.0.
    fenetre.title("SPRINGE — Étape 4/4 · Correspondance des espèces EEE")
    fenetre.resizable(False, False)

    # -- Titre de l'étape (ajout 26.9.0) --
    tk.Label(
        fenetre,
        text="Étape 4 / 4 — Compréhension des données d'entrée (suite)",
        font=("Arial", 12, "bold")
    ).grid(row=0, column=0, columnspan=2, padx=20, pady=(12, 8))

    tk.Label(
        fenetre,
        text=f"Colonne analysée : '{colonne_espece}'  —  "
             f"{len(valeurs_uniques)} valeur(s) distincte(s) trouvée(s)\n"
             "Pour chaque valeur, choisissez l'espèce cible SPRINGE correspondante :",
        justify="left"
    ).grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 5), sticky="w")   # row +1 (26.9.0)

    tk.Label(
        fenetre,
        text="ℹ️ Le détail des espèces (noms latins, description biologique)\n"
             "est disponible dans le document d'explication de SPRINGE (§1.2).",
        fg="gray30", justify="left", wraplength=480
    ).grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")   # row +1 (26.9.0)

    # ------------------------------------------------------------------------
    # Zone défilante (scrollable) pour la liste des valeurs à mapper.
    # Nécessaire car le nombre de valeurs distinctes dépend de la couche
    # fournie par chaque DIR -- potentiellement plus que ce qui tient à l'écran.
    #
    # Principe : un Canvas qui affiche une "fenêtre" sur une Frame interne
    # (frame_liste) pouvant être plus haute que la zone visible. Une Scrollbar
    # pilote le défilement vertical du Canvas.
    # ------------------------------------------------------------------------
    conteneur = tk.Frame(fenetre)
    conteneur.grid(row=3, column=0, columnspan=2, padx=20, pady=5)   # row +1 (26.9.0)

    hauteur_visible = min(320, 40 * len(valeurs_uniques))  # plafonne la hauteur affichée
    canvas = tk.Canvas(conteneur, width=520, height=hauteur_visible, highlightthickness=0)
    scrollbar = tk.Scrollbar(conteneur, orient="vertical", command=canvas.yview)
    frame_liste = tk.Frame(canvas)

    # Callback : à chaque fois que frame_liste change de taille (ex: elle vient
    # d'être remplie avec toutes les lignes), on recalcule la scrollregion du
    # canvas pour que la scrollbar corresponde à la vraie hauteur du contenu.
    # bbox("all") renvoie la boîte englobante de tout ce qui est dessiné dans le canvas.
    frame_liste.bind(
        "<Configure>",
        lambda evenement: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    # On insère frame_liste DANS le canvas comme une fenêtre interne
    # (anchor="nw" = ancrée en haut à gauche du canvas)
    canvas.create_window((0, 0), window=frame_liste, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    # -- Une ligne par valeur unique : libellé brut + effectif + menu déroulant --
    # variables_choix : dict {valeur_brute : StringVar} pour retrouver le choix
    # de chaque ligne au moment de la validation
    variables_choix = {}
    noms_categories = list(CATEGORIES_CIBLES.keys())  # les 5 libellés "parlants" du référentiel

    for i, valeur in enumerate(valeurs_uniques):
        n_points = effectifs.get(valeur, 0)

        tk.Label(
            frame_liste,
            text=f"'{valeur}'  ({n_points} entité(s))",
            anchor="w", width=38, justify="left"
        ).grid(row=i, column=0, padx=(0, 10), pady=3, sticky="w")

        # StringVar laissée VIDE (pas de valeur par défaut) : le menu apparaît
        # donc vide tant que l'utilisateur n'a pas cliqué dessus. C'est
        # volontaire -- on ne veut jamais assigner une catégorie par défaut
        # sans action explicite de l'utilisateur (cf. objectif de la demande)
        var = tk.StringVar(value="")
        combo = ttk.Combobox(
            frame_liste,
            textvariable=var,
            values=noms_categories,
            state="readonly",   # empêche de taper du texte libre : uniquement les 5 choix proposés
            width=32
        )
        combo.grid(row=i, column=1, pady=3)

        variables_choix[valeur] = var

    # ------------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------------
    def valider():
        # on vérifie qu'aucune ligne n'a été laissée sans choix avant d'accepter
        manquants = [
            valeur for valeur, var in variables_choix.items()
            if var.get() not in CATEGORIES_CIBLES
        ]
        if manquants:
            messagebox.showwarning(
                "Correspondances incomplètes",
                "Veuillez choisir une espèce cible pour chaque valeur listée.\n\n"
                "Non renseigné(e) : " + ", ".join(f"'{v}'" for v in manquants)
            )
            return

        # Construction du mapping final : valeur_brute -> species_name_sci.
        # On traduit le libellé "parlant" choisi dans la Combobox vers le nom
        # scientifique via CATEGORIES_CIBLES, car c'est species_name_sci qui
        # sert de clé de jointure avec EEE_SHEET dans tout le reste du pipeline.
        resultat["mapping"] = {
            valeur: CATEGORIES_CIBLES[var.get()]
            for valeur, var in variables_choix.items()
        }
        fenetre.destroy()

    tk.Button(fenetre, text="✔️ Valider", command=valider).grid(
        row=4, column=0, columnspan=2, pady=15   # row +1 (26.9.0)
    )

    # -- Forcer la fenêtre au premier plan (cf. commentaire détaillé dans
    # demander_colonne_espece pour le pourquoi) --
    fenetre.lift()
    fenetre.attributes("-topmost", True)
    fenetre.after(200, lambda: fenetre.attributes("-topmost", False))
    fenetre.focus_force()

    fenetre.grab_set()
    root.wait_window(fenetre)
    root.destroy()

    return resultat["mapping"]


def mapping_interactif_especes(gdf_EEE):
    """
    Fonction principale, à appeler depuis le script principal.
    Enchaîne les 2 étapes (choix de la colonne, puis mapping des valeurs) et
    retourne gdf_EEE enrichi d'une colonne 'species_name_sci'.

    Paramètres
    ----------
    gdf_EEE : GeoDataFrame des points de présence EEE, structure arbitraire

    Retour
    ------
    gdf_EEE_mapping : copie de gdf_EEE + colonne 'species_name_sci'
    colonne_espece : str, nom de la colonne source choisie (traçabilité / rapport)
    mapping_valeurs : dict {valeur_brute_str : species_name_sci} appliqué (traçabilité)

    Lève une ValueError si l'utilisateur ferme une des deux fenêtres sans
    valider -- on préfère arrêter le script proprement plutôt que de
    continuer avec un mapping incomplet ou absent (même logique que pour le
    chargement de l'emprise/des tronçons ailleurs dans le script principal).
    """

    print("\n" + "=" * 70)
    print("MAPPING INTERACTIF DES ESPÈCES EEE")
    print("=" * 70)

    # --- Étape 1 : quelle colonne contient le nom d'espèce ? ---
    colonne_espece = demander_colonne_espece(gdf_EEE)
    if colonne_espece is None:
        raise ValueError("❌ Aucune colonne d'espèce sélectionnée. Arrêt du programme.")
    print(f"✔️ Colonne retenue pour le nom d'espèce : '{colonne_espece}'")

    # --- Étape 2 : quelle correspondance pour chaque valeur de cette colonne ? ---
    mapping_valeurs = demander_mapping_valeurs(gdf_EEE, colonne_espece)
    if mapping_valeurs is None:
        raise ValueError("❌ Mapping des espèces non validé. Arrêt du programme.")

    print("✔️ Mapping validé :")
    for valeur, espece in mapping_valeurs.items():
        print(f"   • '{valeur}' → '{espece}'")

    # --- Application du mapping ---
    # Copie de gdf_EEE pour ne pas modifier l'original par effet de bord
    # (même précaution que dans l'ancien mapping.py)
    gdf_EEE_mapping = gdf_EEE.copy()
    valeurs_str = gdf_EEE_mapping[colonne_espece].fillna(VALEUR_MANQUANTE).astype(str)
    gdf_EEE_mapping["species_name_sci"] = valeurs_str.map(mapping_valeurs)

    return gdf_EEE_mapping, colonne_espece, mapping_valeurs
