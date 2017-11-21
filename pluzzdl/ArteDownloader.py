#!/usr/bin/env python
# -*- coding:Utf-8 -*-

# Notes :
#	 -> Filtre Wireshark :
#		   http.host contains "ftvodhdsecz" or http.host contains "francetv" or http.host contains "pluzz"
#	 ->

#
# Modules
#

import BeautifulSoup
import datetime
import os
import threading
import time
import xml.etree.ElementTree
import xml.sax
import json

from Navigateur import Navigateur, FakeAgent
from PluzzDLException import PluzzDLException
# from Downloader import PluzzDLM3U8, PluzzDLF4M, PluzzDLMMS, PluzzDLRTMP
from Downloader import DownloadM3U8

import logging

logger = logging.getLogger("pluzzdl")


#
# Classes
#

class ArteDownloader(object):
    """
    Classe principale pour lancer un telechargement
    """

    #  http://webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/?idDiffusion=166810096&catalogue=Pluzz
    # http://www.pluzz.fr/appftv/webservices/video/getInfosOeuvre.php?mode=zeri&id-diffusion=166810096
    def __init__(self,
                 url,  # URL de la video
                 proxy=None,  # Proxy a utiliser
                 proxySock=False,  # Indique si le proxy est de type SOCK
                 sousTitres=False,  # Telechargement des sous-titres ?
                 progressFnct=lambda x: None,  # Callback pour la progression du telechargement
                 stopDownloadEvent=threading.Event(),  # Event pour arreter un telechargement
                 outDir="."  # Repertoire de sortie de la video telechargee
                 ):
        # Classe pour telecharger des fichiers
        self.fakeAgent = FakeAgent()

        # Infos video recuperees dans le XML
        self.id = None
        self.lienMMS = None
        self.lienRTMP = None
        self.manifestURL = None
        self.m3u8URL = None
        self.drm = None
        self.chaine = None
        self.timeStamp = None
        self.codeProgramme = None

        # Recupere l'id de l'emission
        self.m3u8URL = self.getVideoUrl(url)

        # Petit message en cas de DRM
        if (self.drm):
            logger.warning("La vidéo posséde un DRM ; elle sera sans doute illisible")

        # get filename
        # nomFichier = self.getOutputFilename(outDir, self.codeProgramme, self.timeStamp, "ts")

        # Downloader
        downloader = DownloadM3U8(self.m3u8URL, os.path.join(".","arte.ts"), self.fakeAgent, stopDownloadEvent, progressFnct)

        # Lance le téléchargement
        downloader.download()


    def getVideoUrl(self, url):
        """
        Recupere l'ID de la video a partir de son URL
        """
        # \todo LBR: process error exceptions in case page can't be loaded or videoId can't be found
        # \todo LBR: check how to use regex
        try:
            page = self.fakeAgent.readPage(url)
            # idEmission = re.findall(self.REGEX_ID, page)[0]
            # LBR 10/05/2017
            data_main_video_tag = page[page.find("iframe="):]
            data_id = data_main_video_tag[data_main_video_tag.find('"') + 1:]
            id_emission = data_id[:data_id.find('"')]
            # data_main_video_tag = re.findall(self.DATA_MAIN_VIDEO, page)[0]
            print "Found data-main-video tag:", id_emission
            # idEmission = re.findall('"[0-9]*"', data_main_video_tag)[0]
            # idEmission = idEmission.strip('"')
            # idEmission = "157542198"
            logger.debug("ID de l'émission : %s" % (id_emission))
            return id_emission

        except :
            raise PluzzDLException("Can't get video ID" )

    def parseInfosJSON(self, pageInfos):
        """
        Parse le fichier de description JSON d'une emission
        """
        try:
            data = json.loads(pageInfos)
            self.lienRTMP = None
            self.lienMMS = None
            self.timeStamp = data['diffusion']['timestamp']
            self.codeProgramme = data['code_programme']
            for v in data['videos']:
                if v['format'] == 'm3u8-download':
                    self.m3u8URL = v['url']
                    self.drm = v['drm']
                elif v['format'] == 'smil-mp4':
                    self.manifestURL = v['url']
            logger.debug("URL m3u8 : %s" % (self.m3u8URL))
            logger.debug("URL manifest : %s" % (self.manifestURL))
            logger.debug("Lien RTMP : %s" % (self.lienRTMP))
            logger.debug("Lien MMS : %s" % (self.lienMMS))
            logger.debug("Utilisation de DRM : %s" % (self.drm))
        except:
            raise PluzzDLException("Impossible de parser le fichier JSON de l'émission")

    def getOutputFilename(self, repertoire, codeProgramme, timeStamp, extension):
        """
        Construit le nom du fichier de sortie
        """
        return os.path.join(repertoire, "%s-%s.%s" % (
            datetime.datetime.fromtimestamp(timeStamp).strftime("%Y%m%d"), codeProgramme, extension))

    def telechargerSousTitres(self, idEmission, nomChaine, nomVideo):
        """
        Recupere le fichier de sous titre de la video
        """
        urlSousTitres = self.URL_SMI.replace("_CHAINE_", nomChaine.lower().replace(" ", "")).replace("_ID_EMISSION_",
                                                                                                     idEmission)
        # Essaye de recuperer le sous titre
        try:
            sousTitresSmi = self.navigateur.getFichier(urlSousTitres)
        except:
            logger.debug("Sous titres indisponibles")
            return
        logger.debug("Sous titres disponibles")
        # Enregistre le fichier de sous titres en smi
        try:
            (nomFichierSansExtension, _) = os.path.splitext(nomVideo)
            # Ecrit le fichier
            with open("%s.smi" % (nomFichierSansExtension), "w") as f:
                f.write(sousTitresSmi)
        except:
            raise PluzzDLException("Impossible d'écrire dans le répertoire %s" % (os.getcwd()))
        logger.debug("Fichier de sous titre smi enregistré")
        # Convertit le fichier de sous titres en srt
        try:
            with open("%s.srt" % (nomFichierSansExtension), "w") as f:
                pageSoup = BeautifulSoup.BeautifulSoup(sousTitresSmi)
                elmts = pageSoup.findAll("sync")
                indice = 1
                for (elmtDebut, elmtFin) in (elmts[i: i + 2] for i in range(0, len(elmts), 2)):
                    # Extrait le temps de debut et le texte
                    tempsEnMs = int(elmtDebut["start"])
                    tempsDebutSrt = time.strftime("%H:%M:%S,XXX", time.gmtime(int(tempsEnMs / 1000)))
                    tempsDebutSrt = tempsDebutSrt.replace("XXX", str(tempsEnMs)[-3:])
                    lignes = elmtDebut.p.findAll("span")
                    texte = "\n".join(map(lambda x: x.contents[0].strip(), lignes))
                    # Extrait le temps de fin
                    tempsEnMs = int(elmtFin["start"])
                    tempsFinSrt = time.strftime("%H:%M:%S,XXX", time.gmtime(int(tempsEnMs / 1000)))
                    tempsFinSrt = tempsFinSrt.replace("XXX", str(tempsEnMs)[-3:])
                    # Ecrit dans le fichier
                    f.write("%d\n" % (indice))
                    f.write("%s --> %s\n" % (tempsDebutSrt, tempsFinSrt))
                    f.write("%s\n\n" % (texte.encode("iso-8859-1")))
                    # Element suivant
                    indice += 1
        except:
            logger.error("Impossible de convertir les sous titres en str")
            return
        logger.debug("Fichier de sous titre srt enregistré")
