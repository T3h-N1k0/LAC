#!/usr/bin/python
# -*- coding: utf-8 -*
import ldap
import time
from random import randint

SERVER = 'SERVER.cines.fr'
USER = 'uid=XXXX,ou=cines,ou=people,dc=cines,dc=fr'
PASSWORD = 'XXXXX'
BRANCH = 'ou=ccc,ou=people,dc=cines,dc=fr'
TODAY = (int(time.time()) / 86400)
SHADOWMAX = 365

def searchAccount(conn):
    """ Renvoi la liste des comptes d'une branche"""
    result = []
    retrieveAttributes = ['uid','shadowMax']
    result = conn.search_st(
        BRANCH, ldap.SCOPE_SUBTREE, 'uid=*', retrieveAttributes)
    return result


def generatePassword(length=12):
    """ Genere un mot de passe aléatoire """
    password = ''
    for i in range(length):
        password += str(randint(0, 9))
    return str(password)


def setExpire(conn, compte, lastchange):
    """ Affecte une date de péremption au compte """
    try:

        attrib = [(ldap.MOD_REPLACE, 'shadowLastChange', str(lastchange))]
        conn.modify_s(compte, attrib)
    except ldap.LDAPError, e:
        print "erreur compte : ", compte
        print e


def setAttr(conn, compte, attr, valeur):
    """ Modify l'attribut passer en parametre """
    try:
        attrib = [(ldap.MOD_REPLACE, attr, str(valeur))]
        conn.modify_s(compte, attrib)
    except ldap.LDAPError, e:
        print "erreur compte : ", compte
        print e


if __name__ == '__main__':
    try:
        server = ldap.open(SERVER)
        server.protocol_version = ldap.VERSION3
        server.simple_bind_s(USER, PASSWORD)

        lResult = searchAccount(server)

        fichierMdP = open("./newPass.txt", "w")
        ligne = 'Compte;"Mot de passe"\n'
        fichierMdP.write(ligne)
        fichierError = open("./newPassError.txt", "w")
        for dn in lResult:
            if len(dn[1]) == 2:
                shadowMax = str(dn[1]['shadowMax'])[2:-2]
                if shadowMax == '90':
                    newPassword = generatePassword()
                    lastChange = TODAY - SHADOWMAX + 10
                    server.passwd_s(dn[0], None, newPassword)
                    setAttr(server, dn[0], 'shadowLastChange', lastChange)
                    setAttr(server, dn[0], 'shadowMax', SHADOWMAX)
                else:                    
                    fichierError.write(str(dn) + "\n")
            else:
                fichierError.write(str(dn) + "\n")
            ligne = str(dn[1]['uid'])[2:-2] + ';"' + newPassword + '"\n'
            fichierMdP.write(ligne)

        fichierMdP.close()
        fichierError.close()
        server.unbind()
    except ldap.LDAPError, e:
        print e
