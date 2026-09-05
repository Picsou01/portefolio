# Le Cadastre - portfolio E5

Portfolio de **Maël Davidenko**, BTS SIO option SLAM, session 2027.
Épreuve **E5 : Support et mise à disposition de services informatiques**.

**En ligne : <https://picsou01.github.io/portefolio/>**

Le site présente les neuf réalisations professionnelles du tableau de synthèse
officiel et les six compétences du bloc 1, sous la forme d'un **plan cadastral
arpentable** : chaque croix du tableau est une borne cliquable qui mène à la
fiche détaillée de la réalisation et à ses preuves.

---

## Démarrer

Le site est du HTML/CSS/JavaScript statique. Il n'a besoin de rien pour
fonctionner : ouvrir `index.html` dans un navigateur suffit.

Pour le servir localement, comme en ligne :

```bash
python -m http.server 8765
```

Puis ouvrir <http://localhost:8765>.

---

## Modifier le contenu

**Aucune page HTML ne se modifie à la main.** Elles sont toutes produites à
partir de trois fichiers de données, puis régénérées d'une commande :

```bash
python outils/arpenteur.py
```

| Fichier | Ce qu'il contient |
|---|---|
| `donnees/cadastre.json` | Identité, chiffres clés, portes d'entrée, les six compétences, les zones du tableau |
| `donnees/parcelles.json` | Les neuf réalisations : contexte, démarche, preuves, enseignement |
| `donnees/pages.json` | Les pages rédigées : veille, parcours, mentions légales |

Le générateur écrit `index.html`, `tableau-de-synthese.html`, les neuf fiches de
`parcelles/`, les six fiches de `competences/`, les trois pages rédigées, le
relief topographique, la rose des vents, l'index des parcelles pour le carnet de
relevé, et `A-FAIRE.md`.

Avant d'écrire quoi que ce soit, il **contrôle la cohérence des données** :
compétence inconnue, zone inconnue, état de preuve invalide, compétence non
couverte. Après avoir écrit, il **vérifie tous les liens internes**. En cas de
problème il s'arrête avec un code d'erreur, plutôt que de produire un site
silencieusement cassé.

### Cas courants

**Ajouter une réalisation** : ajouter un objet dans `donnees/parcelles.json` en
recopiant la structure d'un existant, puis régénérer. La ligne apparaît dans le
plan, la croix se place dans la bonne colonne, la fiche est créée, un
quadrilatère de plus est découpé dans le plan de bornage, le compteur de
couverture est recalculé, le carnet de relevé passe de /9 à /10, et les liens
« parcelle précédente / suivante » se réenchaînent.

**Déposer une preuve** : placer le fichier dans `assets/preuves/`, puis dans
`donnees/parcelles.json` passer `"etat": "a-deposer"` à `"en-ligne"` et ajouter
`"href": "../assets/preuves/mon-fichier.pdf"`.

**Renseigner le dépôt public** : champs `github` et `githubLabel` de
`donnees/cadastre.json`. Le lien se met à jour sur les vingt pages d'un coup.

### États de preuve

| État | Affichage | Sens |
|---|---|---|
| `en-ligne` | Consultable | Le document est accessible depuis le site |
| `confidentiel` | Sur demande | Ne sera jamais publié, consultable auprès de la mairie |
| `a-deposer` | Non publié | Reste à fournir. Listé dans `A-FAIRE.md` |
| `livre` | Livré | Remis au commanditaire |

---

## Structure

```
index.html                  la planche 00 : couverture, portes d'entrée, plan
tableau-de-synthese.html    le tableau officiel E5, imprimable
veille.html                 veille technologique (compétence 1.6)
parcours.html               parcours, certifications, identité professionnelle
mentions-legales.html       éditeur, données, accessibilité
parcelles/                  une fiche par réalisation (9)
competences/                une fiche par compétence du bloc 1 (6)
donnees/                    LA SOURCE DE VÉRITÉ : les trois fichiers JSON
outils/arpenteur.py         le générateur
css/style.css               jetons, typographie, primitives (plaque, chanfrein)
css/cadastre.css            les composants : couverture, plan, parcellaire, fiches
css/impression.css          feuille d'impression A4
js/relief.js                le relief animé sur canvas
js/script.js                thème, en-tête, révélation, sommaire vivant
js/cadastre.js              la visée, les deux vues, le filtre, l'altimètre
js/carnet.js                le carnet de relevé
js/parcelles.js             généré : index des parcelles
assets/                     relief (SVG et JSON), rose des vents, marque, preuves
bac-a-sable/                anciens fichiers d'apprentissage SVG, hors site
A-FAIRE.md                  généré : ce qu'il reste à déposer et à rédiger
```

---

## Décisions techniques

**Aucune dépendance, aucune étape de compilation.** Le site livré est du HTML
statique. Le générateur Python est un outil de maintenance : le site fonctionne
sans lui, sans réseau, et sans Python installé. C'est la même philosophie que
celle appliquée au site de la Mairie de Douvres : aucune dépendance tierce non
maîtrisée.

**Le tableau existe en HTML statique ; le JavaScript ne fait que l'enrichir.**
Si le JavaScript est bloqué, le tableau de synthèse reste un `<table>` sémantique
complet, lisible, navigable au clavier et imprimable, et aucune section n'est
masquée (c'est le rôle de la classe `js` posée en tête de page). La grille de
notation E5 prévoit dix points de pénalité pour un portfolio inaccessible et deux
pour l'absence de tableau de synthèse : il n'était pas question de faire dépendre
l'un ou l'autre d'un script.

**Deux vues d'une même section.** Le tableau officiel et le plan de bornage
montrent les mêmes données. Les deux sont écrits dans la page ; le script n'en
fait qu'un basculement. Le filtre par compétence est posé sur le conteneur de la
section, ce qui le fait agir sur les deux vues à la fois.

**Le relief est calculé, pas dessiné.** `outils/arpenteur.py` définit un relief
comme une somme de bosses gaussiennes, en extrait les courbes de niveau par
*marching squares*, puis les allège par l'algorithme de Ramer-Douglas-Peucker.
Le résultat sort en deux formats : un SVG statique, qui sert de fond de plaque,
et un JSON que `js/relief.js` anime sur canvas (tracé progressif, trois plans de
profondeur, balayage lumineux, réaction au pointeur).

**Le plan de bornage est découpé en guillotine.** Chaque coupe va d'un bord à
l'autre du quadrilatère, et les deux parcelles nées d'une coupe partagent leurs
points. C'est ce partage qui garantit qu'aucun interstice ne s'ouvre entre
voisines : mesuré à 100 % de couverture, sans recouvrement.

**Contrastes vérifiés dans les deux thèmes.** Le plus faible rapport mesuré est
de 4,95:1 en mode nuit et 4,53:1 en mode papier, sur trente-neuf paires
texte/fond. La palette papier bascule vers le bronze : les ors pensés pour un
fond noir ne tiennent pas le seuil sur du papier.

---

## Conventions de rédaction

Deux règles s'appliquent à tout le texte visible, et au rapport de stage qui
accompagne ce portfolio :

- **Aucun tiret long.** Ni em dash (U+2014), ni en dash (U+2013). Seuls le
  trait d'union `-` et le tiret bas `_` sont admis. Une incise
  se compose entre parenthèses, une explication après un deux-points, une
  apposition après une virgule.
- **Espaces insécables** avant `: ; ! ?` et autour des guillemets, pour qu'aucun
  signe ne se retrouve orphelin en début de ligne.

---

## Mise en ligne

Le site est publié par GitHub Pages depuis la branche `main`, à la racine du
dépôt. Un fichier `.nojekyll` demande à Pages de servir les fichiers tels
quels, sans les passer par Jekyll.

Tous les chemins du site sont relatifs, jamais absolus : le site fonctionne
donc aussi bien à la racine d'un domaine que dans un sous-dossier comme
`/portefolio/`, et en ouvrant `index.html` en local.

Publier une mise à jour :

```bash
python outils/arpenteur.py
git add -A && git commit -m "..." && git push
```

---

## Ce qui reste à faire

Les preuves qui manquent portent l'étiquette « Non publié », sans commentaire
ni encadré : le site public ne montre pas ses coutures. Les notes de travail
vivent uniquement dans `A-FAIRE.md`, régénéré à chaque build, qui liste les
preuves à déposer, les passages à rédiger et les documents confidentiels à ne
jamais publier.
