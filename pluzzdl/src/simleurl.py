from BeautifulSoup import BeautifulSoup
import requests

#url = "https://www.france.tv/france-2/on-n-est-pas-couche/"
url = "https://www.france.tv/france-2/journal-20h00/"

page = requests.get(url)

parsed = BeautifulSoup(page.content)

allAtag = parsed.findAll("a")

for atag in allAtag:
    for attr in atag.attrs:
        if "data-video" in attr:
            print "->", atag["href"], "-> V-id:", atag["data-video"]



