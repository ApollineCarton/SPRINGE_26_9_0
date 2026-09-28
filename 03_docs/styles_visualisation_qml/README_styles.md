# Styles QGIS pour les sorties de SPRINGE

Ce dossier contient douze styles `.qml` à appliquer aux couches du GeoPackage
produit par SPRINGE. Chacun répond à **une** question : plutôt que de tout
faire tenir dans une symbologie unique, on charge le style qui correspond à ce
qu'on cherche à voir, et on en change en deux clics.

Testés sur **QGIS 3.44.11** (chargement) et **QGIS 3.34.4** (chargement,
classement et rendu). Les versions antérieures à la 3.34 n'ont pas été
vérifiées.

---

## 1. Charger un style

1. Ajouter la couche du GeoPackage au projet.
2. Clic droit sur la couche → **Propriétés** → **Symbologie**.
3. En bas de la fenêtre : **Style** → **Charger le style…**
4. Choisir le fichier `.qml`, puis **OK**.

Chaque style charge trois choses : la symbologie, les étiquettes de numéro de
tronçon et l'info-bulle. Il ne touche pas aux formulaires, aux jointures ni aux
champs déjà configurés. En revanche, il **remplace** les étiquettes existantes
de la couche.

Pour voir les info-bulles : menu **Vue** → **Afficher les info-bulles**, puis
survoler un tronçon. Elles ne s'affichent que pour la couche sélectionnée dans
le panneau Couches.

---

## 2. Quel style pour quelle question

### Couche cartographique des tronçons

| Fichier | Question | Classes |
|---|---|---|
| `01_score_total_seuils.qml` | Quels tronçons présentent une problématique, et combien d'enjeux le score implique-t-il ? | 0–16 / 17–28 / 29–38 |
| `02_score_enjeu_MS.qml` | Maintenance et Sécurité : combien d'indicateurs sont impactés ? | 0–10 / 11–12 / 13–16 |
| `03_score_enjeu_N.qml` | Protection des milieux naturels : idem | 0–6 / 7–8 / 9–10 |
| `04_score_enjeu_P.qml` | Propagation : idem | 0–7 / 8–9 / 10–12 |
| `05_statut_donnee.qml` | Sur quels tronçons dispose-t-on d'observations ? | observé / aucune observation |
| `06_nb_populations.qml` | Combien de foyers distincts, toutes espèces confondues ? | 1 / 2–3 / 4–5 / 6 et plus |
| `07_nb_especes.qml` | Combien d'espèces différentes ? | 1 / 2 / 3 / 4–5 |
| `08_anciennete_releve.qml` | De quand date le relevé le plus récent ? | ≤ 4 ans / 5–8 / 9–12 / > 12 ans / année non renseignée |
| `09_compacite_maximale.qml` | Le tronçon porte-t-il des populations continues, en taches, ou seulement isolées ? | continue / taches / isolés / non renseignée |
| `10_nb_populations_plus_20m.qml` | Combien de populations de plus de 20 m ? | 0 / 1 / 2–3 / 4 et plus |
| `00_etiquettes_identifiant.qml` | (numéros de tronçon seuls, voir § 5) | — |

### Couche de points `caracterisation_population`

| Fichier | Question |
|---|---|
| `11_populations_EEE.qml` | Où sont les populations, de quelle espèce, de quelle taille, de quelle structure ? |

Ce style se superpose à n'importe quel style de tronçons. Il porte trois
variables à la fois : la **couleur** donne l'espèce, la **taille** la classe de
longueur (losange si elle n'est pas renseignée), le **remplissage** la
compacité (plein pour une population continue, à demi teinté pour des taches
discontinues, contour seul pour des individus isolés, contour pointillé si la
compacité n'est pas renseignée). La légende porte les trois : les entrées
grises de taille et de remplissage servent uniquement d'explication et ne
dessinent aucun point.

---

## 3. Prérequis

**Styles 09 et 10.** Ils lisent la table `caracterisation_EEE_par_troncon_espece`
du GeoPackage, qui doit être chargée dans le projet **sous ce nom exact**
(Couche → Ajouter une couche → Couche vecteur, puis choisir la table). Si elle
manque ou porte un autre nom, tous les tronçons observés basculent dans la
classe « Non calculable — table absente du projet ? ».

**Style 11.** Il attend la couche `caracterisation_population`, écrite par le
lanceur uniquement quand la caractérisation des populations est active (données
déclarées conformes au protocole Albert 2017). Il lit des noms de champs et des
modalités fixes, identiques d'une DIR à l'autre : **il ne fonctionne pas sur une
couche de points brute**.

**Styles 01 à 04.** Les bornes des classes découlent des maxima théoriques
(MS 16, N 10, P 12, total 38) et ne valent **que si tous les coefficients du
lanceur restent à 1**. Si `coef_indicateurs` ou `coef_enjeux` sont modifiés, les
maxima changent et les bornes doivent être recalculées.

---

## 4. Conventions communes

**Ce que dit un trait en tirets.** Un tronçon sans observation enregistrée est
toujours dessiné en tirets, sans remplissage. Un tronçon sans observation n'est
**pas** un tronçon sans EEE : SPRINGE ne dispose d'aucune information sur la
couverture de prospection et ne peut pas distinguer « prospecté sans résultat »
de « non prospecté ».

- Dans les styles de **score** (01 à 04), ces tronçons prennent la couleur de la
  première classe. Sans EEE connue, tous les indicateurs valent 0, donc la
  classe est juste : « pas de problématique **apparente** », au vu des données
  disponibles.
- Dans les styles **descriptifs** (05 à 10), ils restent en gris. Un nombre de
  populations, une compacité ou une année n'ont aucune valeur mesurée pour eux.

À l'échelle d'une DIR entière, les deux bords du ruban se rejoignent et les
tirets se fondent en trait continu : la distinction n'apparaît qu'en zoomant.

**Triangle jaune.** Il signale un tronçon composé de plusieurs portions
dispersées, parfois éloignées de plusieurs dizaines de kilomètres (des polygones
portant le même identifiant, réunis par le lanceur). Ses valeurs sont calculées
sur **toutes** ses portions réunies. Un triangle est posé sur chaque portion, à
partir du 1:100 000 : plus dézoomé, les triangles recouvraient les rubans.

**Entrées « à vérifier ».** Dessinées en noir pointillé, elles signalent une
valeur hors des classes prévues : score vide ou supérieur au maximum, statut de
la donnée non reconnu, espèce hors des cinq catégories. Elles existent pour
qu'aucun tronçon ne disparaisse de la carte sans prévenir. Si l'une d'elles
apparaît, c'est la donnée qu'il faut regarder, pas le style.

**Couleurs.** Aucun style n'utilise le vert-orange-rouge : SPRINGE décrit, il ne
hiérarchise pas. Les classes ordonnées sont rendues par un dégradé d'une seule
teinte, du clair au foncé. Le jaune, le vert et le bleu sont réservés aux trois
enjeux (MS, N, P), conformément aux documents de présentation.

**Ordre de dessin.** Les polygones D et G d'un même PR se recouvrent presque
entièrement, et le dernier dessiné masque l'autre. Chaque style trie donc le
dessin pour que la valeur la plus forte reste visible. L'info-bulle affiche les
valeurs du tronçon dessiné au-dessus.

---

## 5. Les étiquettes

Les numéros de tronçon sont **déjà intégrés** dans les styles 01 à 10 : noir
8 pt, tampon blanc, visibles à partir du 1:50 000, un numéro par portion pour un
tronçon fragmenté. Le style 11 étiquette les populations par `id_population`, à
partir du 1:25 000.

> ⚠ `id_population` est réattribué à chaque exécution de SPRINGE. Il désigne un
> point dans **ce** fichier ; ce n'est pas un identifiant pérenne.

`00_etiquettes_identifiant.qml` ne contient **que** les étiquettes. Il sert à
ajouter les numéros par-dessus une symbologie personnelle, sans la remplacer :
charger d'abord sa propre symbologie, puis ce fichier.

Pour retirer les étiquettes : **Propriétés** → **Étiquettes** → « Pas
d'étiquettes ».

---

## 6. Modifier un style

Les fichiers `.qml` sont abondamment commentés : chaque règle, chaque couleur et
chaque expression est expliquée dans le fichier lui-même. Pour un ajustement
ponctuel (une couleur, une borne), il est plus simple de modifier le XML
directement.

> ⚠ Ré-enregistrer un style depuis QGIS (**Style** → **Enregistrer le style…**)
> écrase le fichier et **supprime tous les commentaires**. Pour conserver la
> version documentée, enregistrer sous un autre nom.

---

## 7. Ce que ces styles ne disent pas

- **Aucun n'est une priorisation.** Ils décrivent un état à partir des données
  disponibles. Une forte colonisation n'appelle pas mécaniquement une
  intervention : selon sa stratégie, un gestionnaire peut cibler les foyers les
  plus étendus ou au contraire les petits foyers isolés en front de
  colonisation.
- **Un point est une population, pas une plante.** Deux taches d'une même espèce
  distantes de moins de 50 m forment une seule population. Un tronçon portant
  plus de points porte plus de foyers distincts, pas nécessairement plus de
  végétation.
- **Aucune surface, aucune densité.** Les classes du protocole sont ouvertes
  (« plus de 3 m », « plus de 20 m ») : aucune conversion en m² n'est possible
  sans inventer des bornes.

Pour le détail de chaque champ et la justification des choix de calcul, voir la
notice de lecture générée avec les résultats et le document de présentation de
l'algorithme SPRINGE.
