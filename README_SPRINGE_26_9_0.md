# SPRINGE 26.9.0

> **Soutien à la PRiorisation des INterventions de Gestion des EEE**

---

## 📋 Table des matières

- [À propos](#à-propos)
- [Fonctionnalités](#fonctionnalités)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Structure du projet](#structure-du-projet)
- [Indicateurs](#indicateurs)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [Contact](#contact)

---

## 🎯 À propos

**SPRINGE** est un **outil d'aide à la décision (OAD)** destiné aux **Directions Interdépartementales des Routes (DIR)**.

Il propose d'établir un état des lieux du réseau routier par rapport à des enjeux et des indicateurs, pour aider à la gestion des linéaires routiers colonisés par des **plantes exotiques envahissantes (EEE)**, en croisant :

- **Vulnérabilité des tronçons** selon trois enjeux :
  - **MS** — Maintenance & Sécurité (visibilité, sanitaire, infrastructures)
  - **N** — Environnement (zones naturelles sensibles)
  - **P** — Propagation (risques colonisation adjacente)

- **Présence et impacts** des espèces EEE ciblées

### Espèces traitées

1. **Renouées asiatiques** — *Reynoutria* spp.
   - *R. bohemica*, *R. japonica*, *R. sachalinensis*
2. **Ailante** — *Ailanthus altissima*
3. **Berce du Caucase** — *Heracleum mantegazzianum*
4. **Ambroisie** — *Ambrosia artemisiifolia*
5. **Autres EEE**

### Méthodologie

SPRINGE est **DESCRIPTIF et COMPARATIF**, jamais prescriptif :
- Caractérise et score les tronçons selon les trois enjeux
- Le gestionnaire conserve l'entière maîtrise de ses arbitrages
- Aide au classement des priorités, pas à la décision automatique

---

## ✨ Fonctionnalités

### Saisie guidée (4 étapes)

1. **Identification** — Structure DIR, opérateur, dossier de sortie
2. **Zone d'étude** — Emprise de travail, réseau routier, identifiant des tronçons
3. **Données SIG** — Couches d'entrée obligatoires et optionnelles
4. **Paramétrage** — Sélection espèces, mapping, caractérisation

### Calculs automatisés

- **Déduplication** des tronçons (fusion géométrique)
- **Jointure spatiale** EEE → tronçons
- **10 indicateurs** (MS1, MS1b, MS2, MS3, N1, N2, P1, P2, P3, P4)
- **Score final** avec classement priorisé
- **Caractérisation détaillée** des populations EEE

### Sorties

- **GeoPackage** (QGIS-ready) : couche cartographique + tables attributaires
- **Rapport d'exécution** : contexte, données, avertissements
- **Graphiques interactifs** (HTML/Plotly) : distributions, histogrammes
- **Notice de lecture** : explications, définitions, modalités
- **Log console** : traçabilité complète de l'exécution

### Chargements automatisés

- **APIs nationales** :
  - INPN (aires protégées, Natura 2000, réserves)
  - IGN BD TOPO (cours d'eau, voies ferrées)
  - IGN BD Carto (zones d'habitation, activité)
  - SNCF (ponts)

---

## 📦 Installation

### Prérequis

- **Python** 3.10 ou plus
- **pip** ou **conda** (Anaconda/Miniconda recommandé)
- **Connexion internet** (pour les APIs)
- **~500 MB** d'espace disque

### Étape 1 — Installer les dépendances

#### Option A : pip (recommandé pour tests rapides)

```bash
pip install -r requirements.txt
```

Temps : ~3-5 minutes selon votre connexion.

#### Option B : Anaconda/Miniconda (recommandé pour production)

```bash
# Créer un environnement virtuel
conda create -n springe python=3.10

# Activer l'environnement
conda activate springe

# Installer les dépendances
conda install -c conda-forge geopandas rasterio rtree
pip install -r requirements.txt
```

#### Problème avec geopandas ?

```bash
# Via conda (plus robuste)
conda install -c conda-forge geopandas
```

### Étape 2 — Vérifier l'installation

```bash
python -c "import geopandas; import pandas; print('✅ Installation OK')"
```

Doit afficher : `✅ Installation OK`

### Étape 3 — Préparer les données

Déposer les fichiers SIG dans le dossier `01_data/` (voir structure ci-dessous).

Les formats acceptés : **`.shp`** (shapefile) et **`.gpkg`** (GeoPackage).

---

## 🚀 Utilisation

### Lancement simple

```bash
python Lancer_SPRINGE_26_9_0.py
```

Ou via IDE Python (Spyder, VSCode, PyCharm) :
- Ouvrir `Lancer_SPRINGE_26_9_0.py`
- Touche **F5** ou menu **Run**

### Flux d'exécution

1. **Fenêtre d'accueil** → Click OK
2. **Étape 1** — Renseigner DIR, opérateur, dossier OUTPUT
3. **Étape 2** — Choisir réseau routier, emprise (optionnel), identifiant tronçons
4. **Étape 3** — Sélectionner couches SIG d'entrée (EEE obligatoire)
5. **Étape 4** — Choisir espèces, mapper noms, paramétrages
6. **Récapitulatif** → Vérifier et cliquer "Lancer SPRINGE"
7. **Calculs** → Attendre (3-15 min selon données)
8. **Résultats** → Dans `02_outputs/`

### Résultats

Les fichiers générés dans `02_outputs/` :

```
02_outputs/
├── SPRINGE_[DIR]_[NOM]_[DATE].gpkg          # Couche cartographique
├── RAPPORT_EXECUTION_[DATE].txt             # Résumé exécution
├── NOTICE_LECTURE_[DATE].txt                # Explications résultats
├── GRAPHIQUES_[DATE].html                   # Visualisations interactives
├── CARACTERISATION_[DATE].csv               # Détail populations EEE
└── SPRINGE_console_[DATE].txt               # Log de console (nouveau 26.9.0)
```

**Point d'entrée QGIS** : Ouvrir le fichier `.gpkg` → couche prête à cartographier.

---

## 📁 Structure du projet

```
SPRINGE_26_9_0_utilisateur/
│
├── Lancer_SPRINGE_26_9_0.py                 ← MAIN SCRIPT (à lancer)
├── installer.py                             ← Installation dépendances
├── requirements.txt                         ← Dépendances Python
├── README_SPRINGE_26_9_0.md                 ← Cette documentation
│
├── 00_fonctions/                            ← Modules Python (ne pas toucher)
│   ├── fenetre_accueil.py
│   ├── fenetre_identification.py
│   ├── fenetre_zone_travail.py
│   ├── fenetre_donnees_indicateurs.py
│   ├── fenetre_selection_especes.py
│   ├── fenetre_mapping_especes.py
│   ├── fenetre_mapping_colonnes_EEE.py
│   ├── fenetre_recap.py
│   ├── deduplication_troncons.py
│   ├── join_num_troncon_a_gdf_EEE.py
│   ├── creer_objet_scoring.py
│   ├── calculer_MS1_impact.py
│   ├── calculer_MS1b_impact.py
│   ├── calculer_MS2_impact.py
│   ├── calculer_MS3_impact.py
│   ├── calculer_N1_impact.py
│   ├── calculer_N2_impact.py
│   ├── calculer_P1_impact.py
│   ├── calculer_P2_impact.py
│   ├── calculer_P3_impact.py
│   ├── calculer_P4_impact.py
│   ├── calculer_score_final.py
│   ├── caracteriser_populations_EEE.py
│   ├── ecrire_couche_populations.py
│   ├── ecrire_table_caracterisation.py
│   ├── generer_rapport.py
│   ├── generer_notice_lecture.py
│   ├── generer_graphiques_plotly.py
│   ├── appel_api.py
│   └── [autres modules]
│
├── 01_data/                                 ← DONNÉES D'ENTRÉE (à fournir)
│   ├── CSV_fichier_excel_caracteristiques_eee/
│   │   └── [fichier .csv des caractéristiques EEE]
│   ├── gdf_EEE/                             ← OBLIGATOIRE
│   │   └── points_EEE.[shp|gpkg]
│   ├── gdf_troncons/                        ← OBLIGATOIRE
│   │   └── reseau_routier.[shp|gpkg]
│   ├── gdf_carrefours/                      ← Optionnel (MS1)
│   ├── gdf_echangeurs/                      ← Optionnel (MS1)
│   ├── gdf_pn/                              ← Optionnel (N1)
│   ├── gdf_tmja/                            ← Optionnel (MS1b)
│   └── [autres couches optionnelles]
│
├── 02_outputs/                              ← RÉSULTATS GÉNÉRÉS
│   ├── SPRINGE_*.gpkg                       (créé automatiquement)
│   ├── RAPPORT_*.txt
│   ├── NOTICE_*.txt
│   ├── GRAPHIQUES_*.html
│   ├── CARACTERISATION_*.csv
│   └── SPRINGE_console_*.txt
│
└── 03_docs/                                 ← Documentation du projet
    ├── SPRINGE_presentation_algorithme.docx
    ├── SPRINGE_guide_utilisateur.docx
    └── [autre documentation]
```

---

## 📊 Indicateurs

| Code | Enjeu | Indicateur | Logique |
|------|-------|-----------|---------|
| **MS1** | Maintenance & Sécurité | Impact sur la **visibilité critique** | Gêne la vue (carrefours, échangeurs) |
| **MS1b** | Maintenance & Sécurité | **Exposition au trafic** | Usagers nombreux exposes |
| **MS2** | Maintenance & Sécurité | **Risque sanitaire** | Potentiel urticant/toxique |
| **MS3** | Maintenance & Sécurité | **Menace infrastructures** | Dégrade routes, ponts, murs |
| **N1** | Environnement | **Proximité zones naturelles** | Bordure vs. proximité |
| **N2** | Environnement | **Potentiel transformation** | Colonise milieux ouverts naturels |
| **P1** | Propagation | **Potentiel reproductif** | Graines/rhizomes/boutures |
| **P2** | Propagation | **Proximité vecteurs** | Cours d'eau, transport routier |
| **P3** | Propagation | **Risque zones adjacentes** | À proximité d'aires protégées |
| **P4** | Propagation | **Colonisation tronçons adjacents** | Tronçons voisins non colonisés |

**Sorties** : Vulnérabilité + Impact + Score final → Classement priorisé par tronçon.

---

## 📚 Documentation

### Guides complets

- **`SPRINGE_presentation_algorithme.docx`** — Spécification technique complète
  - Définitions, logiques, seuils, justifications

- **`SPRINGE_guide_utilisateur.docx`** — Manuel utilisateur pas-à-pas
  - Préparation données, lancement, interprétation résultats

### Documentation technique

Pour comprendre les modifications 26.9.0 :

- **`MODIFICATIONS_Lancer_SPRINGE_26_9_0.md`** — Code avant/après
- **`GUIDE_UTILISATION_26_9_0_MOD.md`** — Prérequis, installation, troubleshooting
- **`CHECKLIST_DEPLOIEMENT.txt`** — Pas-à-pas de mise en place

---

## 🔧 Troubleshooting

### Installation échoue

**Symptôme** : Erreur lors de `pip install -r requirements.txt`

**Solutions** :
```bash
# Essayer pip avec upgrade
pip install --upgrade pip
pip install -r requirements.txt

# Ou via Anaconda (plus robuste)
conda install -c conda-forge geopandas rasterio rtree
pip install -r requirements.txt
```

### geopandas n'installe pas

**Symptôme** : `ERROR: Could not build wheels for geopandas`

**Solution** :
```bash
conda install -c conda-forge geopandas
```

### SPRINGE démarre mais crash immédiatement

**Symptôme** : Fenêtre lance puis ferme

**Solutions** :
1. Vérifier Python 3.10+ : `python --version`
2. Vérifier dépendances : `python -c "import geopandas; print('OK')"`
3. Relancer `installer.py` (mise à jour dépendances)
4. Vérifier fichier Excel CSV existe dans `01_data/CSV_fichier_excel_caracteristiques_eee/`

### Fichiers générés au mauvais endroit

**Symptôme** : `02_outputs/` vide, fichiers ailleurs

**Solution** :
Vérifier que vous utilisez `Lancer_SPRINGE_26_9_0.py` (version 26.9.0+).
Les versions antérieures pointaient vers des dossiers d'anciennes versions.

### Pas de log console

**Symptôme** : Exécution finie, pas de fichier `SPRINGE_console_*.txt`

**Solution** :
Vérifier que `02_outputs/` existe et est accessible en écriture.
Si permissions refusées → vérifier antivirus, permissions dossier.

### API échoue, données partielles

**Symptôme** : Message "API INPN : 0 entités chargées"

**Solutions** :
1. Vérifier **connexion internet** active
2. Vérifier pare-feu n'est pas bloquant
3. APIs peuvent être temporairement indisponibles (relancer)
4. Les données chargées antérieurement sont conservées
5. Un avertissement est ajouté au rapport d'exécution

---

## 📝 Changelog

### Version 26.9.0 (Septembre 2026)

**Nouvelles fonctionnalités** :
- ✅ Fenêtres réordonnées en 4 étapes numérotées
- ✅ Identifiant des tronçons en liste déroulante
- ✅ Mapping des espèces avancé AVANT récapitulatif
- ✅ Fenêtre « Comprendre vos données » supprimée (obsolète)
- ✅ Caractérisation EEE conditionnelle (optionnelle)

**Corrections** :
- ✅ Chemins fichier Excel dynamiques (n'importe quel nom .csv)
- ✅ OUTPUT_DIR pointe vers `02_outputs` de cette version (pas anciennes)
- ✅ Log console automatique (`SPRINGE_console_*.txt`)
- ✅ Multi-OS (Windows/macOS/Linux)
- ✅ Indicateurs : mapping espèces unifié (pas dupliqué dans modules)

**Documentation** :
- ✅ README modernisé avec structure standard
- ✅ requirements.txt commenté avec détails
- ✅ Guide complet d'utilisation et troubleshooting
- ✅ Checklist de déploiement pas-à-pas

---

## 📞 Contact

**Auteur** : Apolline CARTON  
**Organisme** : Office Français de la Biodiversité (OFB)  
**Email** : [contact]  
**Site** : [https://www.ofb.gouv.fr](https://www.ofb.gouv.fr)

### Signaler un bug

Créer une issue avec :
- Version SPRINGE utilisée
- Système d'exploitation (Windows/macOS/Linux)
- Fichier `SPRINGE_console_*.txt` (log d'exécution)
- Description du problème

---

**Dernière mise à jour** : 21 septembre 2026  
**Version** : 26.9.0 (Beta)  
**Statut** : Prêt pour déploiement opérationnel
