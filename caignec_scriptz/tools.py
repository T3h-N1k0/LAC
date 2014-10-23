import csv
import os.path


def saveDict(fn, dict_rap):
    """Sauvegarde un dictionnaire dans un fichier csv"""
    f = open(fn, "wb")
    ligne = csv.writer(f)
    for key, val in dict_rap.items():
        ligne.writerow([key, val])
    f.close()


def readDict(fn):
    """Lit un fichier et stocke le contenu dans un dictionnaire"""
    dict_rap = {}
    if os.path.exists(fn):
        f = open(fn, 'rb')

        for key, val in csv.reader(f):
            dict_rap[key] = eval(val)
        f.close()
    return(dict_rap)