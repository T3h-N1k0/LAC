### TODO
- Doit remplir toute les fonctions actuelles de lac
- Etre plus ergonomique
- Toolbox niveau prod
- Création d'utilisateur/groupe.
  Lorsqu'on crée un groupe pouvoir customiser la liste de système de fichier + vérifier l'unicité de son cn
- Une toolbox permettant d'integrer les outils courant (warning password expire / expiration des comptes / utilisateurs fantomes / Scrupté les tentative de brutforce)
- regrouper les attributs par classe
- Profile soumission
- Incorporer la gestion des listes du C4
- History des modifications du compte
- Différencier groupe secondaire/projet (ou=grProjet,ou=groupePosix,dc=cines,dc=fr) compte CINES uniquement
- History lastbind script local récupérant l'historique de tous les bind utilisateurs -−> mis dans une databases locale
- PPolicy mettre en place le maxage :
- Vérifier la moulinette de warning pour les comptes cines + comptes service pwdmaxage (ppolicies) et pwdChangedTime (usr)) : PPolicy par default si pas de ppolicy  pwdPolicySubentry : que les comptes cines / soft / service
  Remettre a zero tous les attributs
- OTRS :
  requete dans : lib/compte.inc.php
  Insert : pour la cration d'un compte cines / sam / ccc /
  Update : pour la modification d'un compte cines / sam / ccc /
  Delete : pour la suppression login au format ZDEL+date+login date= Ymdhm
  Param de connexion a mettre dans la conf de lac.
  ip du serveur otrstest.cines.fr


### DONE
- Heritage à tous les enfants d'un objet pére (ex: desactiver la soumission a tout un groupe) DONE
- Possibilité de multivaluer les attributs sur une ficher (ex: rajout de champs téléphone, mail,... par l'opérateur) DONE
- Moteur de recherche evolué (clicouille sur les champs a afficher + valeur filtre)  tri par et export csv des champs DONE
- Définir la facon dont s'affiche chaque type d'attributs DONE
- Modifier les admins de lac DONE
- Modifier les admins LDAP  DONE
- Définir des templates d'objet LDAP ainsi que les attributs qui les composent (compte ccc/groupe cines /....)  DONE
- Définir les objets enfant d'un objet LDAP (ex: quotaStore qui représente les quotas utilisateurs sur l'espace store)  DONE
- Permettre des traitements par lots (fichiers CSV), l'application doit fournir un CSV backup des donnée avant modif.
- Unicité des UID géré via un objet ldap donnant le prochain uid dispo pour l'objet en cour (voir: lionel).
- Unicité et historique uid/gid (gérer une liste d'exception uid/gid locaux) --> Fournir tranche uid reserver pour usage machine 50000 / 59999 + 25501-25601
- Suppression d'un utilisateur. Prendre en compte les groupes le contenant
- PPolicy par default si pas de ppolicy  pwdPolicySubentry
  Lorsqu'on crée un compte autre et soft il faut par defaut la ppolicy de service.


### Remarques transverses :
- faire attention aux entrées utilisateurs pour eviter les XSS
- faire gaffe a la gestion des session
- Toute la conf de l'application doit être stocké au maximum dans LDAP et une base local (type sqlite)



### Environnements :
LAC actuel (pointe sur ta base ldap) : https://lac-preprod.cines.fr
Serveur ldap (ou tu pourras installer le serveur web + poser le nouveau lac) : ldapone.cines.fr

### Questions:
- Permettre des traitements par lots (fichiers CSV), l'application doit fournir un CSV backup des donnée avant modif => que doit contenir ce fichier de backup ?
- Template d'objet LDAP : edit_page ?
- Objets enfants ?
- sous quelle forme faire les modifications par groupe/héritage ?
- Où sont les admins LDAP ?
- Unicité : stockage de tous les uids dans la base locale LAC ?


- ppolicies par défaut pour branches stockées où ?



### Sécurité :
- ldapsearch SSL
