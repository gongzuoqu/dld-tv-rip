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
import re
import json
from bs4 import BeautifulSoup

from PluzzDLException import PluzzDLException
# from Downloader import PluzzDLM3U8, PluzzDLF4M, PluzzDLMMS, PluzzDLRTMP
from Downloader import DownloadM3U8

import logging

logger = logging.getLogger("frtvdld")


#
# Classes
#

class FranceTvDownloader(object):
    """
    Classe principale pour lancer un telechargement
    """

    DATA_MAIN_VIDEO = 'data-main-video="([0-9][a-z]-)*"'
    REGEX_ID = "http://info.francetelevisions.fr/\?id-video=([^\"]+)"
    XML_DESCRIPTION = "http://www.pluzz.fr/appftv/webservices/video/getInfosOeuvre.php?mode=zeri&id-diffusion=_ID_EMISSION_"
    JSON_DESCRIPTION = "http://webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/?idDiffusion=_ID_EMISSION_&catalogue=Pluzz"
    URL_SMI = "http://www.pluzz.fr/appftv/webservices/video/getFichierSmi.php?smi=_CHAINE_/_ID_EMISSION_.smi&source=azad"
    M3U8_LINK = "http://medias2.francetv.fr/catchup-mobile/france-dom-tom/non-token/non-drm/m3u8/_FILE_NAME_.m3u8"
    REGEX_M3U8 = "/([0-9]{4}/S[0-9]{2}/J[0-9]{1}/[0-9]*-[0-9]{6,8})-"

    #  http://webservices.francetelevisions.fr/tools/getInfosOeuvre/v2/?idDiffusion=166810096&catalogue=Pluzz
    # http://www.pluzz.fr/appftv/webservices/video/getInfosOeuvre.php?mode=zeri&id-diffusion=166810096
    def __init__(self,
                 url,  # URL de la video
                 fakeAgent=None,  # fakeAgent to download page/file
                 sousTitres=False,  # Telechargement des sous-titres ?
                 progressFnct=lambda x: None,  # Callback pour la progression du telechargement
                 stopDownloadEvent=threading.Event(),  # Event pour arreter un telechargement
                 outDir="."  # Repertoire de sortie de la video telechargee

                 ):

        self.fakeAgent = fakeAgent

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

        # check if url point to the video page, if not get list of video URl one by one
        idEmission = None
        videoUrl = url
        i = 0
        while idEmission is None:
            page = self.fakeAgent.readPage(videoUrl)
            idEmission = self.getVideoId(page)

            if idEmission is None:
                videoUrl = self.getListOfAvailableVideo(url, i)
                i+=1

            if videoUrl is None:
                raise(PluzzDLException("Can't find selected Video url"))

        # go for JSON straight, don't even try XML
        pageInfos = self.fakeAgent.readPage(self.JSON_DESCRIPTION.replace("_ID_EMISSION_", idEmission))
        self.parseInfosJSON(pageInfos)

        # Petit message en cas de DRM
        if (self.drm):
            logger.warning("La vidéo posséde un DRM ; elle sera sans doute illisible")

        # Verification qu'un lien existe
        if (self.m3u8URL is None):
            raise PluzzDLException("Aucun lien vers la vidéo")

        # get filename
        nomFichier = self.getOutputFilename(outDir, self.codeProgramme, self.timeStamp, "ts")

        # Downloader
        downloader = DownloadM3U8(self.m3u8URL, nomFichier, self.fakeAgent, stopDownloadEvent, progressFnct)

        # Recupere les sous titres si necessaire
        if (sousTitres):
            self.telechargerSousTitres(idEmission, self.chaine, nomFichier)

        # start downloading the video
        downloader.download()

    def getVideoId(self, page):
        """
        get Video ID from the video page
        """
        # \todo LBR: process error exceptions in case page can't be loaded or videoId can't be found
        try:
            parsed = BeautifulSoup(page, "html.parser")
            videoId = parsed.find_all("div", attrs={"class": "PlayerContainer", "data-main-video": re.compile("[0-9]+")})
            if len(videoId) == 0 :
                return None

            # logger.debug("ID de l'émission : %s" % (videoId[0]["data-main-video"]))
            return videoId[0]["data-main-video"]

        except :
            raise PluzzDLException("Can't get or parse video ID page" )

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

    def getListOfAvailableVideo(self, url, index):
        page = self.fakeAgent.readPage(url)
        parsed = BeautifulSoup(page, "html.parser")
        videoUrlList = parsed.find_all("a", attrs={"class": "card-link", "data-link": "player", "data-video": re.compile("[0-9]+")})
        if index > len(videoUrlList):
            return None

        return "https:"+videoUrlList[index]["href"]




