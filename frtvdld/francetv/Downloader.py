#!/usr/bin/env python
# -*- coding:Utf-8 -*-


#
# Modules
#
import os
import re
import logging

# from Historique import Historique, Video
from PluzzDLException import PluzzDLException

logger = logging.getLogger("pluzzdl")


class DownloadM3U8(object):
    """
    Telechargement des liens m3u8
    """

    def __init__(self, m3u8URL, outputFilename, fakeAgent, stopDownloadEvent, progressFnct):
        self.m3u8URL = m3u8URL
        self.videoFileName = outputFilename
        self.fakeAgent = fakeAgent
        self.stopDownloadEvent = stopDownloadEvent
        self.progressFnct = progressFnct

    # def creerMKV(self):
    #     """
    #     Creer un mkv a partir de la video existante (cree l'en-tete de la video)
    #     """
    #     logger.info("Création du fichier MKV (vidéo finale); veuillez attendre quelques instants")
    #     logger.info("Convert: %s -> %s" % (self.nomFichier, self.nomFichierFinal))
    #     commande = "ffmpeg -i %s -c:a aac -strict -2 -vcodec copy %s" % (self.nomFichier, self.nomFichierFinal)
    #
    #     try:
    #         if (os.system(commande) == 0):
    #             os.remove(self.nomFichier)
    #             logger.info("Fin !")
    #         else:
    #             logger.warning(
    #                 "Problème lors de la création du MKV avec FFmpeg ; le fichier %s est néanmoins disponible" % (
    #                     self.nomFichier))
    #     except:
    #         raise PluzzDLException("Impossible de créer la vidéo finale")

    def download(self):

        # Get fragments index: master.m3u8
        logger.info("Get index master.m3u8")
        self.m3u8 = self.fakeAgent.readPage(self.m3u8URL)

        # get URL of all fragments
        self.listFragments = re.findall(".+?\.ts", self.m3u8)
        if not self.listFragments:
            self.listFragments = []
            listeM3U8 = re.findall(".+?index_2_av\.m3u8", self.m3u8)
            for m3u8 in listeM3U8:
                m3u8data = self.fakeAgent.readPage(m3u8)
                self.listFragments.extend(re.findall(".+?\.ts", m3u8data))

        self.maxNbrFrag = long(len(self.listFragments))
        logger.info("Nbr of fragments : %d" % (self.maxNbrFrag))

        #
        # Create video file
        #
        try:
            self.videoFile = open(self.videoFileName, "wb")
        except:
            raise PluzzDLException("Can't create video file")


        # Download fragments and create the ts file
        logger.info("Start downloading fragments")
        try:
            i = 0
            while i <= self.maxNbrFrag and not self.stopDownloadEvent.isSet():
                frag = self.fakeAgent.readPage("%s" % (self.listFragments[i]))
                self.videoFile.write(frag)

                # display progress
                self.progressFnct(min(int((i*100) / self.maxNbrFrag), 100))
                i += 1

            if i == self.maxNbrFrag:
                self.progressFnct(100)
                logger.info("Download completed")
                self.videoFile.close()

        except KeyboardInterrupt:
            logger.info("Interruption clavier")
            return None

        except Exception as inst:
            logger.critical("Erreur inconnue %s" % inst)
            return None

        finally:
            if i != self.maxNbrFrag:
                logger.critical("Couldn't complete video download.  Stop at fragment %d/%d" % (i, self.maxNbrFrag))

            return self.videoFileName


#
# class PluzzDLM3U8(object):
#     """
#     Telechargement des liens m3u8
#     """
#
#     def __init__(self, m3u8URL, nomFichier, navigateur, stopDownloadEvent, progressFnct):
#         self.m3u8URL = m3u8URL
#         self.nomFichier = nomFichier
#         self.navigateur = navigateur
#         self.stopDownloadEvent = stopDownloadEvent
#         self.progressFnct = progressFnct
#
#         self.historique = Historique()
#
#         self.nomFichierFinal = "%s.mp4" % (self.nomFichier[:-3])
#
#     def ouvrirNouvelleVideo(self):
#         """
#         Creer une nouvelle video
#         """
#         try:
#             # Ouverture du fichier
#             print "Nom Fichier:", self.nomFichier
#             #			fullPathFile = os.path.join(os.getcwd(), self.nomFichier)
#             #			print "fullPathFile:", fullPathFile
#             self.fichierVideo = open(self.nomFichier, "wb")
#         # self.fichierVideo = open( fullPathFile, "wb" )
#         except:
#             raise PluzzDLException("Impossible d'ecrire dans le repertoire %s" % (os.getcwd()))
#             # Ajout de l'en-tête Fait dans creerMKV
#
#     def ouvrirVideoExistante(self):
#         """
#         Ouvre une video existante
#         """
#         try:
#             # Ouverture du fichier
#             self.fichierVideo = open(self.nomFichier, "a+b")
#         except:
#             raise PluzzDLException("Impossible d'écrire dans le répertoire %s" % (os.getcwd()))
#
#     def creerMKV(self):
#         """
#         Creer un mkv a partir de la video existante (cree l'en-tete de la video)
#         """
#         logger.info("Création du fichier MKV (vidéo finale); veuillez attendre quelques instants")
#         logger.info("Convert: %s -> %s" % (self.nomFichier, self.nomFichierFinal))
#         commande = "ffmpeg -i %s -c:a aac -strict -2 -vcodec copy %s" % (self.nomFichier, self.nomFichierFinal)
#
#         try:
#             if (os.system(commande) == 0):
#                 os.remove(self.nomFichier)
#                 logger.info("Fin !")
#             else:
#                 logger.warning(
#                     "Problème lors de la création du MKV avec FFmpeg ; le fichier %s est néanmoins disponible" % (
#                         self.nomFichier))
#         except:
#             raise PluzzDLException("Impossible de créer la vidéo finale")
#
#     def telecharger(self):
#         # Recupere le fichier master.m3u8
#         self.m3u8 = self.navigateur.getFichier(self.m3u8URL)
#         # Extrait l'URL de tous les fragments
#         self.listeFragments = re.findall(".+?\.ts", self.m3u8)
#         if not self.listeFragments:
#             self.listeFragments = []
#             self.listeM3U8 = re.findall(".+?index_2_av\.m3u8", self.m3u8)
#             for m3u8 in self.listeM3U8:
#                 m3u8data = self.navigateur.getFichier(m3u8)
#                 self.listeFragments.extend(re.findall(".+?\.ts", m3u8data))
#         #
#         # Creation de la video
#         #
#         self.premierFragment = 1
#         self.telechargementFini = False
#         video = self.historique.getVideo(self.m3u8URL)
#         # Si la video est dans l'historique
#         if (video is not None):
#             # Si la video existe sur le disque
#             if (os.path.exists(self.nomFichier) or os.path.exists(self.nomFichierFinal)):
#                 if (video.finie):
#                     logger.info("La vidéo a déjà été entièrement téléchargée")
#                     if (not os.path.exists(self.nomFichierFinal)):
#                         self.creerMKV()
#                     return
#                 else:
#                     self.ouvrirVideoExistante()
#                     self.premierFragment = video.fragments
#                     logger.info("Reprise du téléchargement de la vidéo au fragment %d" % (video.fragments))
#             else:
#                 self.ouvrirNouvelleVideo()
#                 logger.info(u"Impossible de reprendre le téléchargement de la vidéo, le fichier %s n'existe pas" % (
#                     self.nomFichier))
#         else:  # Si la video n'est pas dans l'historique
#             self.ouvrirNouvelleVideo()
#         # Nombre de fragments
#         self.nbFragMax = float(len(self.listeFragments))
#         logger.debug("Nombre de fragments : %d" % (self.nbFragMax))
#         # Ajout des fragments
#         logger.info("Début du téléchargement des fragments")
#         try:
#             i = self.premierFragment
#             while (i <= self.nbFragMax and not self.stopDownloadEvent.isSet()):
#                 frag = self.navigateur.getFichier("%s" % (self.listeFragments[i - 1]))
#                 self.fichierVideo.write(frag)
#                 # Affichage de la progression
#                 self.progressFnct(min(int((i / self.nbFragMax) * 100), 100))
#                 i += 1
#             if (i == self.nbFragMax + 1):
#                 self.progressFnct(100)
#                 self.telechargementFini = True
#                 logger.info("Fin du téléchargement")
#                 self.creerMKV()
#         except KeyboardInterrupt:
#             logger.info("Interruption clavier")
#         except Exception as inst:
#             logger.critical("Erreur inconnue %s" % inst)
#         finally:
#             # Ajout dans l'historique
#             self.historique.ajouter(Video(lien=self.m3u8URL, fragments=i, finie=self.telechargementFini))
#             # Fermeture du fichier
#             self.fichierVideo.close()
#
#
# class PluzzDLF4M(object):
#     """
# 	Telechargement des liens f4m
# 	"""
#
#     adobePlayer = "http://fpdownload.adobe.com/strobe/FlashMediaPlayback_101.swf"
#
#     def __init__(self, manifestURL, nomFichier, navigateur, stopDownloadEvent, progressFnct):
#         self.manifestURL = manifestURL
#         self.nomFichier = nomFichier
#         self.navigateur = navigateur
#         self.stopDownloadEvent = stopDownloadEvent
#         self.progressFnct = progressFnct
#
#         self.historique = Historique()
#         self.configuration = Configuration()
#         self.hmacKey = self.configuration["hmac_key"].decode("hex")
#         self.playerHash = self.configuration["player_hash"]
#
#     def parseManifest(self):
#         """
# 		Parse le manifest
# 		"""
#         try:
#             arbre = xml.etree.ElementTree.fromstring(self.manifest)
#             # Duree
#             self.duree = float(arbre.find("{http://ns.adobe.com/f4m/1.0}duration").text)
#             self.pv2 = arbre.find("{http://ns.adobe.com/f4m/1.0}pv-2.0").text
#             media = arbre.findall("{http://ns.adobe.com/f4m/1.0}media")[-1]
#             # Bitrate
#             self.bitrate = int(media.attrib["bitrate"])
#             # URL des fragments
#             urlbootstrap = media.attrib["url"]
#             self.urlFrag = "%s%sSeg1-Frag" % (
#                 self.manifestURLToken[: self.manifestURLToken.find("manifest.f4m")], urlbootstrap)
#             # Header du fichier final
#             self.flvHeader = base64.b64decode(media.find("{http://ns.adobe.com/f4m/1.0}metadata").text)
#         except:
#             raise PluzzDLException("Impossible de parser le manifest")
#
#     def ouvrirNouvelleVideo(self):
#         """
# 		Creer une nouvelle video
# 		"""
#         try:
#             # Ouverture du fichier
#             self.fichierVideo = open(self.nomFichier, "wb")
#         except:
#             raise PluzzDLException("Impossible d'écrire dans le répertoire %s" % (os.getcwd()))
#         # Ajout de l'en-tête FLV
#         self.fichierVideo.write(binascii.a2b_hex("464c56010500000009000000001200010c00000000000000"))
#         # Ajout de l'header du fichier
#         self.fichierVideo.write(self.flvHeader)
#         self.fichierVideo.write(binascii.a2b_hex("00000000"))  # Padding pour avoir des blocs de 8
#
#     def ouvrirVideoExistante(self):
#         """
# 		Ouvre une video existante
# 		"""
#         try:
#             # Ouverture du fichier
#             self.fichierVideo = open(self.nomFichier, "a+b")
#         except:
#             raise PluzzDLException("Impossible d'écrire dans le répertoire %s" % (os.getcwd()))
#
#     def decompressSWF(self, swfData):
#         """
# 		Decompresse un fichier swf
# 		"""
#         # Adapted from :
#         #	 Prozacgod
#         #	 http://www.python-forum.org/pythonforum/viewtopic.php?f=2&t=14693
#         if (type(swfData) is str):
#             swfData = StringIO.StringIO(swfData)
#
#         swfData.seek(0, 0)
#         magic = swfData.read(3)
#
#         if (magic == "CWS"):
#             return "FWS" + swfData.read(5) + zlib.decompress(swfData.read())
#         else:
#             return None
#
#     def getPlayerHash(self):
#         """
# 		Recupere le sha256 du player flash
# 		"""
#         # Get SWF player
#         playerData = self.navigateur.getFichier("http://static.francetv.fr/players/Flash.H264/player.swf")
#         # Uncompress SWF player
#         playerDataUncompress = self.decompressSWF(playerData)
#         # Perform sha256 of uncompressed SWF player
#         hashPlayer = hashlib.sha256(playerDataUncompress).hexdigest()
#         # Perform base64
#         return base64.encodestring(hashPlayer.decode('hex'))
#
#     def debutVideo(self, fragID, fragData):
#         """
# 		Trouve le debut de la video dans un fragment
# 		"""
#         # Skip fragment header
#         start = fragData.find("mdat") + 4
#         # For all fragment (except frag1)
#         if (fragID > 1):
#             # Skip 2 FLV tags
#             for dummy in range(2):
#                 tagLen, = struct.unpack_from(">L", fragData, start)  # Read 32 bits (big endian)
#                 tagLen &= 0x00ffffff  # Take the last 24 bits
#                 start += tagLen + 11 + 4  # 11 = tag header len ; 4 = tag footer len
#         return start
#
#     def telecharger(self):
#         # Verifie si le lien du manifest contient la chaine "media-secure"
#         if (self.manifestURL.find("media-secure") != -1):
#             raise PluzzDLException("pluzzdl ne sait pas gérer ce type de vidéo (utilisation de DRMs)...")
#         # Lien du manifest (apres le token)
#         self.manifestURLToken = self.navigateur.getFichier("http://hdfauth.francetv.fr/esi/urltokengen2.html?url=%s" % (
#             self.manifestURL[self.manifestURL.find("/z/"):]))
#         # Recupere le manifest
#         self.manifest = self.navigateur.getFichier(self.manifestURLToken)
#         # Parse le manifest
#         self.parseManifest()
#         # Calcul les elements
#         self.hdnea = self.manifestURLToken[self.manifestURLToken.find("hdnea"):]
#         self.pv20, self.hdntl = self.pv2.split(";")
#         self.pvtokenData = r"st=0000000000~exp=9999999999~acl=%2f%2a~data=" + self.pv20 + "!" + self.playerHash
#         self.pvtoken = "pvtoken=%s~hmac=%s" % (
#             urllib.quote(self.pvtokenData), hmac.new(self.hmacKey, self.pvtokenData, hashlib.sha256).hexdigest())
#
#         #
#         # Creation de la video
#         #
#         self.premierFragment = 1
#         self.telechargementFini = False
#
#         video = self.historique.getVideo(self.urlFrag)
#         # Si la video est dans l'historique
#         if (video is not None):
#             # Si la video existe sur le disque
#             if (os.path.exists(self.nomFichier)):
#                 if (video.finie):
#                     logger.info("La vidéo a déjà été entièrement téléchargée")
#                     return
#                 else:
#                     self.ouvrirVideoExistante()
#                     self.premierFragment = video.fragments
#                     logger.info("Reprise du téléchargement de la vidéo au fragment %d" % (video.fragments))
#             else:
#                 self.ouvrirNouvelleVideo()
#                 logger.info("Impossible de reprendre le téléchargement de la vidéo, le fichier %s n'existe pas" % (
#                     self.nomFichier))
#         else:  # Si la video n'est pas dans l'historique
#             self.ouvrirNouvelleVideo()
#
#         # Calcul l'estimation du nombre de fragments
#         self.nbFragMax = round(self.duree / 6)
#         logger.debug("Estimation du nombre de fragments : %d" % (self.nbFragMax))
#
#         # Ajout des fragments
#         logger.info("Début du téléchargement des fragments")
#         try:
#             i = self.premierFragment
#             self.navigateur.appendCookie("hdntl", self.hdntl)
#             while (not self.stopDownloadEvent.isSet()):
#                 # frag	= self.navigateur.getFichier( "%s%d?%s&%s&%s" %( self.urlFrag, i, self.pvtoken, self.hdntl, self.hdnea ) )
#                 frag = self.navigateur.getFichier("%s%d" % (self.urlFrag, i), referer=self.adobePlayer)
#                 debut = self.debutVideo(i, frag)
#                 self.fichierVideo.write(frag[debut:])
#                 # Affichage de la progression
#                 self.progressFnct(min(int((i / self.nbFragMax) * 100), 100))
#                 i += 1
#         except urllib2.URLError, e:
#             if (hasattr(e, 'code')):
#                 if (e.code == 403):
#                     if (e.reason == "Forbidden"):
#                         logger.info("Le hash du player semble invalide ; calcul du nouveau hash")
#                         newPlayerHash = self.getPlayerHash()
#                         if (newPlayerHash != self.playerHash):
#                             self.configuration["player_hash"] = newPlayerHash
#                             self.configuration.writeConfig()
#                             logger.info("Un nouveau hash a été trouvé ; essayez de relancer l'application")
#                         else:
#                             logger.critical("Pas de nouveau hash disponible...")
#                     else:
#                         logger.critical("Impossible de charger la vidéo")
#                 elif (e.code == 404):
#                     self.progressFnct(100)
#                     self.telechargementFini = True
#                     logger.info("Fin du téléchargement")
#         except KeyboardInterrupt:
#             logger.info("Interruption clavier")
#         except:
#             logger.critical("Erreur inconnue")
#         finally:
#             # Ajout dans l'historique
#             self.historique.ajouter(Video(lien=self.urlFrag, fragments=i, finie=self.telechargementFini))
#             # Fermeture du fichier
#             self.fichierVideo.close()
#
#
# class PluzzDLRTMP(object):
#     """
# 	Telechargement des liens rtmp
# 	"""
#
#     def __init__(self, lienRTMP):
#         self.lien = lienRTMP
#
#     def telecharger(self):
#         logger.info("Lien RTMP : %s\nUtiliser par exemple rtmpdump pour la recuperer directement" % (self.lien))
#
#
# class PluzzDLMMS(object):
#     """
# 	Telechargement des liens mms
# 	"""
#
#     def __init__(self, lienMMS):
#         self.lien = lienMMS
#
#     def telecharger(self):
#         logger.info("Lien MMS : %s\nUtiliser par exemple mimms ou msdl pour la recuperer directement" % (self.lien))
