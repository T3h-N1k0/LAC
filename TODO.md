Un site web en deux parties :

### Partie pour la maintenance des comptes LDAP qui remplacera le lac actuel :
- Doit remplir toute les fonctions actuelles de lac
- Etre plus ergonomique
- Permettre des traitements par lots (fichiers CSV), l'application doit fournir un CSV backup des donnée avant modif.
- Heritage à tous les enfants d'un objet pére (ex: desactiver la soumission a tout un groupe)
- Possibilité de multivaluer les attributs sur une ficher (ex: rajout de champs téléphone, mail,... par l'opérateur)
- Moteur de recherche evolué (clicouille sur les champs a afficher + valeur filtre)  tri par et export csv des champs
- Toolbox niveau prod


### Site d'administration permettant de configurer l'application :
- Définir la facon dont s'affiche chaque type d'attributs
- Modifier les admins de lac
- Modifier les admins LDAP
- Définir des templates d'objet LDAP ainsi que les attributs qui les composent (compte ccc/groupe cines /....)
- Définir les objets enfant d'un objet LDAP (ex: quotaStore qui représente les quotas utilisateurs sur l'espace store)
- Une toolbox permettant d'integrer les outils courant
- Unicité des UID géré via un objet ldap donnant le prochain uid dispo pour l'objet en cour (voir: lionel).
- regrouper les attributs par classe

### Remarques transverses :
- faire attention aux entrées utilisateurs pour eviter les XSS
- faire gaffe a la gestion des session
- Toute la conf de l'application doit être stocké au maximum dans LDAP et une base local (type sqlite)



### Environnements :
LAC actuel (pointe sur ta base ldap) : https://lac-preprod.cines.fr
Serveur ldap (ou tu pourras installer le serveur web + poser le nouveau lac) : ldapone.cines.fr

### Questions:
- Longueur fixe pour uid ?



### Sécurité :
- ldapsearch SSL
