# 📋 INVENTAIRE — Fonctions Python utilisées par Lancer_SPRINGE

**SPRINGE v26.9.0 — 28 modules Python**

---

## 🔧 **SECTION 1 — PRÉPARATION & IMPORT DONNÉES**

### 1. `check_path.py`
Vérifie que les chemins d'accès aux fichiers/dossiers de données existent et sont correctement accessibles. Centralise les messages d'erreur et la gestion multi-plateforme (Windows/Linux).

### 2. `import_sig.py`
Importe les couches SIG (GeoDataFrame) stockées en local (shapefiles, GeoPackage, etc.). Wrapper simple autour de `gpd.read_file()` avec gestion d'erreurs.

### 3. `import_sig_interne.py`
Importe les données de référence internes à SPRINGE (tables Excel de caractéristiques EEE, tables de mapping espèces, etc.).

### 4. `get_emprise_zone.py`
Extrait l'emprise géographique (bounding box) de la zone d'étude à partir des tronçons pour vérifier que toutes les couches SIG importées sont bien dans le périmètre d'intérêt.

### 5. `reprojeter_en_lambert.py`
Reprojette toutes les GeoDataFrames en Lambert 93 (EPSG:2154) si nécessaire. Homogénéise le système de référence avant les calculs spatiaux.

---

## 🗂️ **SECTION 2 — STRUCTURE & JOINTURES**

### 6. `creer_objet_scoring.py`
Crée le DataFrame principal `df_scoring` qui sera enrichi itérativement avec les colonnes de scoring (MS1_impact, P2_impact, etc.). C'est le conteneur central des résultats.

### 7. `deduplication_troncons.py`
Déduplique les polygones partageant le même identifiant (`nom_plo_fi`). Mode fusion : réconcilie les multipolygones disjoints (cas des échangeurs); mode suffixe : attribue des identifiants uniques (a, b, c...).

### 8. `join_num_troncon_a_gdf_EEE.py`
Effectue la jointure spatiale entre les points de présence EEE et les tronçons. Gère les points situés à cheval sur deux tronçons (bordures) et crée la colonne `nom_plo_fi` sur `gdf_EEE`.

### 9. `detecter_elements_sur_troncon.py`
Détecte la présence d'éléments (cours d'eau, zones naturelles protégées, voies ferrées, etc.) à proximité des tronçons via jointure spatiale + tampon. Crée les colonnes Niv1-Niv4 pour chaque catégorie d'éléments.

---

## 🧮 **SECTION 3 — CALCUL DES INDICATEURS (SCORING)**

### 10. `calculer_vulnerabilite_facon1.py`
Détermine la vulnérabilité de chaque tronçon (oui/non) selon ses caractéristiques (largeur, trafic, proximité EEE) pour initialiser les colonnes `MS1_vulnerabilite`, `N1_vulnerabilite`, etc.

### 11. `calculer_MS1_impact.py` ⚠️ **CORRIGÉ (v21-09-2026)**
Calcule l'impact des EEE sur la **visibilité critique** (MS1 : 0-5 points). Croise la hauteur maximale des EEE avec la vulnérabilité du tronçon. **BUG CORRIGÉ** : case "vulnerable + aucune EEE" retournait 3 au lieu de 0.

### 12. `calculer_MS1b_impact.py`
Bonus MS1b : attribue +1 point si le tronçon a fort trafic (>1000 véh/j) ET est colonisé par EEE. Amplifie le risque sur axes très chargés.

### 13. `calculer_MS2_impact.py`
Calcule l'impact des EEE sur les **populations naturelles** adjacentes (MS2 : 0-5 points). Détecte la colonisation d'habitats naturels protégés à proximité des tronçons.

### 14. `calculer_MS3_impact.py`
Calcule l'impact des EEE sur les **écosystèmes aquatiques** (MS3 : 0-5 points). Croise présence EEE + proximité cours d'eau + type de cours d'eau (rivière, lac, etc.).

### 15. `calculer_N1_impact.py`
Calcule le risque pour les **zones naturelles adjacentes** (N1 : 0-2 points). Détecte les zones protégées Niv1-Niv4 dans un tampon 50m autour des tronçons.

### 16. `calculer_N2_impact.py`
Calcule le risque de **dispersion vectorielle** via les éléments anthropiques (N2 : 0-4 points). Croise présence EEE + carrefours/échangeurs/voies ferrées.

### 17. `calculer_P1_impact.py`
Calcule la **pression d'inoculum** : niveau de colonisation des EEE sur le tronçon (P1 : 0-3 points). Augmente avec la densité de points EEE détectés.

### 18. `calculer_P2_impact.py` ⚠️ **AMÉLIORÉ (v21-09-2026)**
Calcule la **proximité des vecteurs de dispersion** (P2 : 0-5 points). Détecte cours d'eau, carrefours, voies ferrées, fort trafic TMJA. **AMÉLIORÉ** : seuil TMJA adaptatif (Q3) au lieu de fixe 10K.

### 19. `calculer_P3_impact.py` ⚠️ **CORRIGÉ (v21-09-2026)**
Calcule la **menace sur zones naturelles sensibles** (P3 : 0-2 points). Croise EEE + P2≥2 + zones naturelles Niv1-4 dans tampon 200m. **BUG CORRIGÉ** : utilisait colonnes 50m au lieu de 200m.

### 20. `calculer_P4_impact.py`
Calcule la **pression de propagation** : évalue le potentiel de spread de l'EEE via routes/corridors (P4 : 0-3 points). Dépend du trafic routier et des connexions entre tronçons.

---

## 📊 **SECTION 4 — AGRÉGATION & SCORING FINAL**

### 21. `calculer_priorisation.py`
Agrège les 8 indicateurs M (menace) et P (pression) en deux scores synthétiques : **Menace_score** et **Pression_score** (0-5 chacun). Normalise et pondère les impacts.

### 22. `calculer_score_final.py`
Croise Menace_score × Pression_score pour produire le **score final SPRINGE** (0-25 points). Détermine le **niveau de priorité** (URGENT, HAUTE, MOYEN, FAIBLE) pour chaque tronçon.

---

## 📈 **SECTION 5 — MAPPING & ANALYSES AVANCÉES**

### 23. `fenetre_mapping_colonnes_EEE.py` (depuis lanceur)
Fenêtre interactive : permet au gestionnaire de mapper les colonnes de sa base de données vers les colonnes attendues par SPRINGE (espèce, hauteur, diamètre, etc.). Crée la colonne standardisée `species_name_sci`.

### 24. `fenetre_mapping_especes.py` (depuis lanceur)
Fenêtre interactive : permet au gestionnaire d'associer les noms d'espèces locaux aux espèces de référence SPRINGE (grâce au thésaurus OFB). Valide et enriche `gdf_EEE` avant les calculs.

### 25. `mapping.py`
Utilitaires pour les mappages (conversion de dictionnaires, lookup tables). Support pour les transformations espèces et colonnes de manière générique.

### 26. `analyser_attribution_elements_sur_troncon.py`
Analyse post-calcul : vérifie que la détection d'éléments (cours d'eau, zones, etc.) s'est bien déroulée et suggère des corrections si un élément attendu n'a pas été détecté (optionnel).

---

## 📝 **SECTION 6 — RAPPORTS & VISUALISATIONS**

### 27. `generer_rapport.py`
Génère le rapport final SPRINGE (.txt) résumant les résultats, les statistiques par indicateur, et les recommandations d'actions de gestion par tronçon prioritaire.

### 28. `generer_graphiques.py`
Génère des graphiques interactifs (Plotly) : distributions des scores, cartes choroplèthes des priorités, histogrammes des indicateurs. Exporte en HTML pour consultation rapide.

---

## 🔌 **SECTION 7 — UTILITAIRES**

### A. `traitement_en_cours.py`
Affiche une barre de progression ou des messages "en cours de traitement" pour informer l'utilisateur de l'avancement du calcul (optionnel, cosmétique).

### B. `com.py`
Utilitaire léger : emballe les fonctions pour marquer des commentaires/annotations de type "à corriger" dans le code source.

### C. `travaux.py`
Utilitaire léger : marque les sections en cours de développement ou les éléments futurs du code ("work in progress").

---

## 🔀 **FLUX D'EXÉCUTION (ordre d'appel dans Lancer_SPRINGE)**

```
ÉTAPE 1 — PRÉPARATION
    ├─ check_path()               [valide chemins]
    ├─ import_sig()               [charge GeoDataFrames]
    ├─ import_sig_interne()       [charge tables EEE]
    ├─ get_emprise_zone()         [extrait emprise]
    └─ reprojeter_en_lambert()    [harmonise SRS]

ÉTAPE 2 — STRUCTURE
    ├─ creer_objet_scoring()      [crée df_scoring]
    ├─ deduplication_troncons()   [fusionne doublons]
    ├─ join_num_troncon_a_gdf_EEE()  [jointure spatiale EEE↔tronçons]
    ├─ fenetre_mapping_especes()  [map espèces]
    ├─ fenetre_mapping_colonnes_EEE() [map colonnes]
    └─ detecter_elements_sur_troncon() [détecte éléments près tronçons]

ÉTAPE 3 — SCORING (calcul des 8 indicateurs)
    ├─ calculer_vulnerabilite_facon1() [détermine vulnerabilite]
    ├─ calculer_MS1_impact()      [visibilité critique]
    ├─ calculer_MS1b_impact()     [bonus fort trafic]
    ├─ calculer_MS2_impact()      [impact pop naturelles]
    ├─ calculer_MS3_impact()      [impact aquatique]
    ├─ calculer_N1_impact()       [risque zones naturelles]
    ├─ calculer_N2_impact()       [dispersion anthropique]
    ├─ calculer_P1_impact()       [pression inoculum]
    ├─ calculer_P2_impact()       [proximité vecteurs]
    ├─ calculer_P3_impact()       [menace zones sensibles]
    └─ calculer_P4_impact()       [pression propagation]

ÉTAPE 4 — AGRÉGATION
    ├─ calculer_priorisation()    [agrège M et P]
    └─ calculer_score_final()     [score 0-25 + niveau]

ÉTAPE 5 — RAPPORT & VISUA
    ├─ generer_rapport.py         [génère .txt final]
    └─ generer_graphiques.py      [génère HTML interactifs]
---

**Dernière mise à jour** : 21 septembre 2026  

