#!/usr/bin/python
# -*- coding: utf-8 -*
import ldap
from tools import *

SERVER = 'SERVER.cines.fr'
USER = 'uid=XXXX,ou=cines,ou=people,dc=cines,dc=fr'
PASSWORD = 'XXXXX'
BRANCHUSER = 'dc=cines,dc=fr'
FILE = 'history.csv'


def getAccount():
    """ Renvoi la liste des comptes avec leur dernier bind"""
    try:
        server = ldap.open(SERVER)
        server.protocol_version = ldap.VERSION3
        server.simple_bind_s(USER, PASSWORD)

        retrieveAttributes = ['uidNumber', 'authTimestamp']
        result = server.search_st(
            BRANCHUSER, ldap.SCOPE_SUBTREE, 'uid=*', retrieveAttributes)
        server.unbind()
        return result
    except ldap.LDAPError, e:
        server.unbind()
        print e


if __name__ == '__main__':
    bindHistory = readDict(FILE)
    oldSize = len(bindHistory)
    lResult = getAccount()

    # Construit pour chaque compte l'historique
    for dn in lResult:
        key = str(dn[1]['uidNumber'])[2:-2]
        val = [str(dn[0])]

        #  initialise variable lastBind
        if len(dn[1]) == 2:
            lastBind = str(dn[1]['authTimestamp'])[2:-2]
        else:
            lastBind = '-'

        # Construit l'historique du compte suivant qu'il existe ou non
        hist = []
        if key in bindHistory:
            # récupère l'ancien historique du compte
            hist = list(bindHistory[key][1])
            if not lastBind in hist:
                hist.append(lastBind)
        else:
            hist.append(lastBind)
        bindHistory[key] = [val, hist]

    # Sauvegarde l'histoiruqe dictionnaire
    if len(bindHistory) >= oldSize:
        saveDict(FILE, bindHistory)
        
