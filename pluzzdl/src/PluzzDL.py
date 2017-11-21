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
#from Downloader import PluzzDLM3U8, PluzzDLF4M, PluzzDLMMS, PluzzDLRTMP
from Downloader import PluzzDLM3U8


import logging

logger = logging.getLogger("pluzzdl")


#
# Classes
#

class PluzzDL(object):
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
                 proxy=None,  # Proxy a utiliser
                 proxySock=False,  # Indique si le proxy est de type SOCK
                 sousTitres=False,  # Telechargement des sous-titres ?
                 progressFnct=lambda x: None,  # Callback pour la progression du telechargement
                 stopDownloadEvent=threading.Event(),  # Event pour arreter un telechargement
                 outDir="."  # Repertoire de sortie de la video telechargee
                 ):
        # Classe pour telecharger des fichiers
        self.navigateur = Navigateur(proxy, proxySock)
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
        idEmission = self.getId(url)
        # Recupere la page d'infos de l'emission
        # try:
        #     # pageInfos = self.navigateur.getFichier(self.XML_DESCRIPTION.replace("_ID_EMISSION_", idEmission))
        #     pageInfos = self.fakeAgent.readPage(self.XML_DESCRIPTION.replace("_ID_EMISSION_", idEmission))
        #     # Parse la page d'infos
        #     self.parseInfos(pageInfos)
        # except:
        #     logger.debug("Problème avec le fichier XML, récupération du JSON")
        #     # pageInfos = self.navigateur.getFichier(self.JSON_DESCRIPTION.replace("_ID_EMISSION_", idEmission))
        #     pageInfos = self.fakeAgent.readPage(self.JSON_DESCRIPTION.replace("_ID_EMISSION_", idEmission))
        #     self.parseInfosJSON(pageInfos)

        # go for JSON straight, don't eventry XML
        pageInfos = self.fakeAgent.readPage(self.JSON_DESCRIPTION.replace("_ID_EMISSION_", idEmission))
        self.parseInfosJSON(pageInfos)
        
        # Petit message en cas de DRM
        if (self.drm):
            logger.warning("La vidéo posséde un DRM ; elle sera sans doute illisible")
        # Verification qu'un lien existe
        if (self.m3u8URL is None and
                    self.manifestURL is None and
                    self.lienRTMP is None and
                    self.lienMMS is None):
            raise PluzzDLException("Aucun lien vers la vidéo")
        # Le telechargement se fait de differente facon selon le type du lien disponible
        # Pour l'instant, seule la methode via les liens m3u8 fonctionne
        # Le code pour les autres liens reste quand meme en place pour etre utilise si les elements manquants sont trouves (clef HMAC par exemple)
        if (self.m3u8URL is not None):
            # Nom du fichier
            nomFichier = self.getNomFichier(outDir, self.codeProgramme, self.timeStamp, "ts")
            # Downloader
            downloader = PluzzDLM3U8(self.m3u8URL, nomFichier, self.navigateur, stopDownloadEvent, progressFnct)
        elif (self.manifestURL is not None):
            # Nom du fichier
            nomFichier = self.getNomFichier(outDir, self.codeProgramme, self.timeStamp, "flv")
            # Downloader
            downloader = PluzzDLF4M(self.manifestURL, nomFichier, self.navigateur, stopDownloadEvent, progressFnct)
        elif (self.lienRTMP is not None):
            # Downloader
            downloader = PluzzDLRTMP(self.lienRTMP)
        elif (self.lienMMS is not None):
            # Downloader
            downloader = PluzzDLMMS(self.lienMMS)
        # Recupere les sous titres si necessaire
        if (sousTitres):
            self.telechargerSousTitres(idEmission, self.chaine, nomFichier)
        # Lance le téléchargement
        downloader.telecharger()

    def getId(self, url):
        """
        Recupere l'ID de la video a partir de son URL
        """
        # try :
        # page = self.navigateur.getFichier(url)
        page = self.fakeAgent.readPage(url)
        # idEmission = re.findall(self.REGEX_ID, page)[0]
        # LBR 10/05/2017
        data_main_video_tag = page[page.find("data-main-video="):]
        data_id = data_main_video_tag[data_main_video_tag.find('"') + 1:]
        id_emission = data_id[:data_id.find('"')]
        # data_main_video_tag = re.findall(self.DATA_MAIN_VIDEO, page)[0]
        print "Found data-main-video tag:", id_emission
        # idEmission = re.findall('"[0-9]*"', data_main_video_tag)[0]
        # idEmission = idEmission.strip('"')
        # idEmission = "157542198"
        logger.debug("ID de l'émission : %s" % (id_emission))
        return id_emission

    # except :
    # raise PluzzDLException( "Impossible de récupérer l'ID de l'émission" )

    def parseInfos(self, pageInfos):
        """
        Parse le fichier de description XML d'une emission
        """
        try:
            xml.sax.parseString(pageInfos, PluzzDLInfosHandler(self))
            # Si le lien m3u8 n'existe pas, il faut essayer de creer celui de la plateforme mobile
            if (self.m3u8URL is None):
                logger.debug("m3u8URL file missing, we will try to guess it")
                if (self.manifestURL is not None):
                    self.m3u8URL = self.manifestURL.replace("manifest.f4m", "index_2_av.m3u8")
                    self.m3u8URL = self.m3u8URL.replace("/z/", "/i/")
                    # self.m3u8URL = self.M3U8_LINK.replace( "_FILE_NAME_", re.findall( self.REGEX_M3U8, pageInfos )[ 0 ] )
            logger.debug("URL m3u8 : %s" % (self.m3u8URL))
            logger.debug("URL manifest : %s" % (self.manifestURL))
            logger.debug("Lien RTMP : %s" % (self.lienRTMP))
            logger.debug("Lien MMS : %s" % (self.lienMMS))
            logger.debug("Utilisation de DRM : %s" % (self.drm))
        except:
            raise PluzzDLException("Impossible de parser le fichier XML de l'émission")

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

    def getNomFichier(self, repertoire, codeProgramme, timeStamp, extension):
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




class PluzzDLInfosHandler(xml.sax.handler.ContentHandler):
    """
	Handler pour parser le XML de description d'une emission
	"""

    def __init__(self, pluzzdl):
        self.pluzzdl = pluzzdl

        self.isUrl = False
        self.isDRM = False
        self.isChaine = False
        self.isCodeProgramme = False

    def startElement(self, name, attrs):
        if (name == "url"):
            self.isUrl = True
        elif (name == "drm"):
            self.isDRM = True
        elif (name == "chaine"):
            self.isChaine = True
        elif (name == "diffusion"):
            self.pluzzdl.timeStamp = float(attrs.getValue("timestamp"))
        elif (name == "code_programme"):
            self.isCodeProgramme = True

    def characters(self, data):
        if (self.isUrl):
            if (data[: 3] == "mms"):
                self.pluzzdl.lienMMS = data
            elif (data[: 4] == "rtmp"):
                self.pluzzdl.lienRTMP = data
            elif (data[-3:] == "f4m"):
                self.pluzzdl.manifestURL = data
            elif (data[-4:] == "m3u8"):
                self.pluzzdl.m3u8URL = data
        elif (self.isDRM):
            self.pluzzdl.drm = data
        elif (self.isChaine):
            self.pluzzdl.chaine = data
        elif (self.isCodeProgramme):
            self.pluzzdl.codeProgramme = data

    def endElement(self, name):
        if (name == "url"):
            self.isUrl = False
        elif (name == "drm"):
            self.isDRM = False
        elif (name == "chaine"):
            self.isChaine = False
        elif (name == "code_programme"):
            self.isCodeProgramme = False
