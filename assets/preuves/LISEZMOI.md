# Où déposer les preuves

Placer ici les documents consultables publiquement : captures d'écran,
cahiers des charges, attestations de certification, procédures, supports
de formation.

Puis, dans `donnees/parcelles.json`, pour la preuve concernée :

    "etat": "en-ligne",
    "href": "../assets/preuves/mon-fichier.pdf"

et relancer `python outils/arpenteur.py`.

## Ce qui ne va PAS ici

Le tableur d'analyse des coûts et le rapport de synthèse de l'audit de la
Mairie de Douvres relèvent du secret professionnel. Ils restent déclarés
"confidentiel" dans les données, s'affichent comme tels sur le site, et ne
doivent jamais être déposés dans ce dossier.
