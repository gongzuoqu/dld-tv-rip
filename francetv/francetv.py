#!/usr/bin/env python2
# -*- coding:Utf-8 -*-

import requests
import BeautifulSoup
import argparse
import re

__version__ = "0.0.1"

# red_exp = 'href="//www.france.tv/[a-z]*france-2/infrarouge/605-la-traque-des-nazis.html"'
# REG_EXP = 'href="//www.france.tv/()"'
# REG_EXP = 'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
# REG_EXP = 'href="//www.france.tv/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
REG_EXP = 'www.france.tv/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

def Parse(url):
    page = requests.get(url)

    # print "page.content", page.content
    index = page.content.find("la sélection")
    print "page.content:\n", page.content[index:]

    urls = re.findall(REG_EXP, page.content[index:])
    # urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', page.content[:index])
    print urls

    soup = BeautifulSoup.BeautifulSoup(page.content, 'html.parser')
    print(soup.prettify())



if (__name__ == "__main__"):

    # Arguments de la ligne de commande
    usage = "francetv [options] urlEmission"
    parser = argparse.ArgumentParser(usage=usage, description="Télécharge les émissions de Pluzz")
    parser.add_argument("-b", "--progressbar", action="store_true", default=False,
                    help='affiche la progression du téléchargement')
    parser.add_argument("-p", "--proxy", dest="proxy", metavar="PROXY",
                    help='utilise un proxy HTTP au format suivant http://URL:PORT')
    parser.add_argument("-s", "--sock", action="store_true", default=False,
                    help='si un proxy est fourni avec l\'option -p, un proxy SOCKS5 est utilisé au format suivant ADRESSE:PORT')
    parser.add_argument("-v", "--verbose", action="store_true", default=False,
                    help='affiche les informations de debugage')
    parser.add_argument("-t", "--soustitres", action="store_true", default=False,
                    help='récupère le fichier de sous-titres de la vidéo (si disponible)')

    parser.add_argument("-o", "--outDir", action="store", default=None, help='output folder (default .)')

    parser.add_argument("--nocolor", action='store_true', default=False, help='désactive la couleur dans le terminal')
    parser.add_argument("--version", action='version', version="francetv %s" % (__version__))
    parser.add_argument("urlEmission", action="store", help="URL de l'émission Pluzz a charger")
    args = parser.parse_args()

    Parse(args.urlEmission)