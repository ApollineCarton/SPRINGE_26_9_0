<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<!--
  ════════════════════════════════════════════════════════════════════════
  SPRINGE — Style 00 : étiquettes d'identifiant des tronçons
  ════════════════════════════════════════════════════════════════════════
  Couche cible : couche cartographique des tronçons du GeoPackage SPRINGE.
  Testé sur    : QGIS 3.34.4. À valider sur 3.44.11.

  À quoi sert ce style :
      Afficher le numéro de chaque tronçon ("nom_plo_fi", ex. 35PR100D)
      pour pouvoir le citer, le retrouver dans la table attributaire ou
      le reporter dans un compte rendu.

  PARTICULARITÉ : ce style ne contient QUE des étiquettes
  (styleCategories="Labeling"). Il se charge PAR-DESSUS n'importe quel
  autre style SPRINGE sans remplacer sa symbologie :
      1. charger d'abord un style de symbologie (01, 05, ...) ;
      2. puis charger celui-ci de la même façon :
         Propriétés > Symbologie > Style > Charger le style...
  Pour retirer les étiquettes : Propriétés > Étiquettes > « Pas d'étiquettes ».

  Choix graphiques :
      - Texte noir de 8 pt entouré d'un TAMPON blanc de 1 mm : le numéro
        reste lisible quelle que soit la couleur du tronçon dessous.
      - Visibles seulement à partir du 1:50 000 (en zoomant). À l'échelle
        d'une DIR entière, plusieurs centaines de numéros se chevauchent
        et deviennent illisibles.
      - Les polygones D et G d'un même PR se recouvrent presque
        entièrement : leurs étiquettes se disputent la même place. QGIS
        cherche alors un autre emplacement à l'intérieur du polygone ; s'il
        n'en trouve pas, il en masque une plutôt que de les superposer.
        En zoomant davantage, les deux finissent par s'afficher.

  Les commentaires disparaissent si le style est ré-enregistré depuis QGIS.
  ════════════════════════════════════════════════════════════════════════
-->
<!-- labelsEnabled="1" : active l'étiquetage de la couche au chargement. -->
<qgis version="3.34.4-Prizren" styleCategories="Labeling" labelsEnabled="1">

  <!-- type="simple" : une seule règle d'étiquetage pour tous les tronçons. -->
  <labeling type="simple">
    <settings calloutType="simple">

      <!--
        ──────────────────────────────────────────────────────────────────
        TEXTE
        ──────────────────────────────────────────────────────────────────
        fieldName="nom_plo_fi" + isExpression="0" : on affiche directement
          la valeur du champ (pas une expression calculée).
        fontFamily / fontSize / fontSizeUnit="Point" : police de 8 points.
          Si Arial manque sur le poste, QGIS prend la police par défaut.
        textColor : noir légèrement adouci #1A1A1A = 26,26,26.
        Les attributs non précisés prennent la valeur par défaut de QGIS.
      -->
      <text-style fieldName="nom_plo_fi" isExpression="0"
                  fontFamily="Arial" fontSize="8" fontSizeUnit="Point" fontWeight="50"
                  textColor="26,26,26,255" textOpacity="1"
                  multilineHeight="1" multilineHeightUnit="Percentage" allowHtml="0">
        <families/>

        <!--
          TAMPON (halo) autour des lettres
          bufferDraw="1"          tampon activé
          bufferSize="1" + MM     largeur de 1 mm autour de chaque caractère
          bufferColor             blanc 255,255,255 ...
          bufferOpacity="0.85"    ... à 85 % d'opacité : le tronçon reste
                                  deviné sous le numéro
          bufferNoFill="1"        seul le contour des lettres est tamponné
                                  (pas de pavé blanc à l'intérieur des lettres)
          bufferJoinStyle="128"   coins arrondis (128 = RoundJoin)
        -->
        <text-buffer bufferDraw="1" bufferSize="1" bufferSizeUnits="MM"
                     bufferColor="255,255,255,255" bufferOpacity="0.85"
                     bufferNoFill="1" bufferJoinStyle="128" bufferBlendMode="0"/>
      </text-style>

      <!--
        ──────────────────────────────────────────────────────────────────
        PLACEMENT
        ──────────────────────────────────────────────────────────────────
        placement="4"               « Horizontal » : texte horizontal, placé
                                    à l'intérieur du polygone (plus lisible
                                    qu'un texte qui suit la courbe du ruban).
        polygonPlacementFlags="2"   autorise le placement à l'intérieur du
                                    polygone.
        fitInPolygonOnly="0"        le texte peut déborder du ruban s'il est
                                    plus long que le ruban n'est large.
        overlapHandling             PreventOverlap : jamais deux étiquettes
                                    l'une sur l'autre (une est masquée).
        priority="5"                priorité moyenne face aux étiquettes
                                    d'autres couches du projet (0 à 10).
      -->
      <placement placement="4" polygonPlacementFlags="2" fitInPolygonOnly="0"
                 overlapHandling="PreventOverlap" priority="5"
                 dist="0" distUnits="MM" offsetType="0" quadOffset="4"
                 xOffset="0" yOffset="0" offsetUnits="MM" rotationAngle="0"
                 centroidWhole="0" centroidInside="0"/>

      <!--
        ──────────────────────────────────────────────────────────────────
        RENDU
        ──────────────────────────────────────────────────────────────────
        scaleVisibility="1"  visibilité conditionnée à l'échelle.
        scaleMax="50000"     échelle la plus « dézoomée » où les étiquettes
                             apparaissent : 1:50 000. (Nommage QGIS
                             contre-intuitif : scaleMax = plus grand
                             dénominateur d'échelle.)
        scaleMin="0"         aucune limite en zoom avant.
        obstacle="0"         les polygones de la couche ne repoussent PAS les
                             étiquettes : sinon, le numéro serait chassé
                             hors du ruban qu'il désigne.
        labelPerPart="0"     un seul numéro par tronçon, même si le polygone
                             est en plusieurs morceaux.
        upsidedownLabels="0" pas de texte à l'envers.
        drawLabels="1"       étiquettes dessinées.
      -->
      <rendering drawLabels="1" scaleVisibility="1" scaleMin="0" scaleMax="50000"
                 obstacle="0" labelPerPart="0" upsidedownLabels="0"
                 limitNumLabels="0" maxNumLabels="2000" minFeatureSize="0"
                 fontLimitPixelSize="0" zIndex="0" unplacedVisibility="0"/>
    </settings>
  </labeling>

  <!-- 2 = polygones. -->
  <layerGeometryType>2</layerGeometryType>
</qgis>
