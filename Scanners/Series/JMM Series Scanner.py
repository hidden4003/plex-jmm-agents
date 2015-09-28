# -*- coding: utf-8 -*-
### Log variables, regex, skipped folders, words to remove, character maps ###
import sys, os, time, re, fnmatch, unicodedata, urllib2, Utils, VideoFiles, Media #import Stack ### Plex Media Server\Plug-ins\Scanners.bundle\Contents\Resources\Common ###
from lxml import etree 

JMM_CHANNEL_URL = 'http://127.0.0.1:8111/JMMServerPlex/GetFilters/1'
### LOG_PATH calculated once for all calls ####################################################################                        #platform = sys.platform.lower() if "platform" in dir(sys) and callable(getattr(sys,'platform')) else "" 
LOG_PATHS = { 'win32':  [ '%LOCALAPPDATA%\\Plex Media Server\\Logs',                                       #
                          '%USERPROFILE%\\Local Settings\\Application Data\\Plex Media Server\\Logs' ],    #
              'darwin': [ '$HOME/Library/Application Support/Plex Media Server/Logs' ],                    # LINE_FEED = "\r"
              'linux':  [ '$PLEX_HOME/Library/Application Support/Plex Media Server/Logs',                 # Linux
                          '/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Logs',   # Debian, Fedora, CentOS, Ubuntu
                          '/usr/local/plexdata/Plex Media Server/Logs',                                    # FreeBSD
                          '/usr/pbi/plexmediaserver-amd64/plexdata/Plex Media Server/Logs',                # FreeNAS
                          '${JAIL_ROOT}/var/db/plexdata/Plex Media Server/Logs/',                          # FreeNAS
                          '/c/.plex/Library/Application Support/Plex Media Server/Logs',                   # ReadyNAS
                          '/share/MD0_DATA/.qpkg/PlexMediaServer/Library/Plex Media Server/Logs',          # QNAP
                          '/volume1/Plex/Library/Application Support/Plex Media Server/Logs',              # Synology, Asustor
                          '/volume2/Plex/Library/Application Support/Plex Media Server/Logs',              # Synology, if migrated a second raid volume as unique volume in new box         
                          '/raid0/data/module/Plex/sys/Plex Media Server/Logs',                            # Thecus
                          '/raid0/data/PLEX_CONFIG/Plex Media Server/Logs' ]}                              # Thecus Plex community version
platform = sys.platform.lower() if "platform" in dir(sys) and not sys.platform.lower().startswith("linux") else "linux" if "platform" in dir(sys) else Platform.OS.lower()
for LOG_PATH in LOG_PATHS[platform] if platform in LOG_PATHS else [ os.path.join(os.getcwd(),"Logs"), '$HOME']:
  if '%' in LOG_PATH or '$' in LOG_PATH:  LOG_PATH = os.path.expandvars(LOG_PATH)  # % on win only, $ on linux
  if os.path.isdir(LOG_PATH):             break                                    # os.path.exists(LOG_PATH)
else: LOG_PATH = os.path.expanduser('~')                                           # logging.basicConfig(), logging.basicConfig(filename=os.path.join(path, 'Plex Media Scanner (custom ASS).log'), level=logging.INFO) #logging.error('Failed on {}'.format(filename))

### Allow to log to the same folder Plex writes its logs in #############################################
global LOG_FILE_LIBRARY
LOG_FILE_LIBRARY = LOG_FILE = 'JMM Media Scanner.log'  # Log filename library will include the library name, LOG_FILE not and serve as reference
def Log(entry, filename=None): 
  global LOG_FILE_LIBRARY
  with open(os.path.join(LOG_PATH, filename if filename else LOG_FILE_LIBRARY), 'a') as file:
    file.write( time.strftime("%Y-%m-%d %H:%M:%S") + " " + entry + "\n")
    print entry  # when ran from console ### Allow to display ints even if equal to None at times ### def xint(s):   return str(s) if s is not None and not s=="" else "None"

### import Plex token to have a library list to put hte library name on the log filename ###
PLEX_LIBRARY_URL = "http://127.0.0.1:32400/library/sections/?X-Plex-Token=ACCOUNT_TOKEN_HERE"  # Allow to get the library name to get a log per library https://support.plex.tv/hc/en-us/articles/204059436-Finding-your-account-token-X-Plex-Token
if os.path.isfile(os.path.join(LOG_PATH, "X-Plex-Token.id")):                                  #Log("'X-Plex-Token.id' file present")
  with open(os.path.join(LOG_PATH, "X-Plex-Token.id"), 'r') as token_file:  PLEX_LIBRARY_URL = PLEX_LIBRARY_URL.replace("ACCOUNT_TOKEN_HERE", token_file.read().strip())  #Log("PLEX_LIBRARY_URL: '%s', token: '%s'" % (PLEX_LIBRARY_URL, token))
PLEX_LIBRARY = {}
try:
  result      = urllib2.urlopen(PLEX_LIBRARY_URL)
  library_xml = etree.fromstring(result.read())
  for library in library_xml.iterchildren('Directory'):
    for path in library.iterchildren('Location'):  PLEX_LIBRARY[path.get("path")] = library.get("title")
except:  Log("Place correct Plex token in X-Plex-Token.id file in logs folder or in PLEX_LIBRARY_URL variable to have a log per library - https://support.plex.tv/hc/en-us/articles/204059436-Finding-your-account-token-X-Plex-Token")

def xmlFromJMMChannel(url):
  try:
    result = urllib2.urlopen(url)
    library_xml = etree.fromstring(result.read())
    return library_xml
  except:  Log("Error fetching %s" %(url))

def Start():
  global JMM_Files_Map
  channelMainPage = xmlFromJMMChannel(JMM_CHANNEL_URL)
  allUrl = None
  try: 
    for directory in channelMainPage.iterchildren('Directory'):
      if directory.get('title') == 'All':
        allUrl = directory.get('key')
  except:  
    Log("Start - XML issue, result: %s" %(logEx()))
    return

  #Log("Start allUrl: %s" %(allUrl))

  JMM_Shows = {}
  JMM_Files_Map = {}
  channelShowsPage = xmlFromJMMChannel(allUrl.replace('/video/jmm/proxy/','').decode("hex"))
  for season in channelShowsPage.iterchildren('Directory'):
      if season.get('type') == 'season':
        seasonItem = {'title': season.get('title'), 'rating': season.get('rating'), 'summary': season.get('summary'), 'image': season.get('thumb'), 'year': season.get('year'), 'url': season.get('key').replace('/video/jmm/proxy/','').decode("hex")}
        if season.get('season'):
          seasonItem['season'] = season.get('season')
        else:
          seasonItem['season'] = '1'
        jmmId = seasonItem['title'].encode('hex')
        if not jmmId in JMM_Shows:
          JMM_Shows[jmmId] = {'seasons': {}, 'title': season.get('title'), 'rating': season.get('rating'), 'summary': season.get('summary'), 'image': season.get('thumb'), 'year': season.get('year'), 'url': season.get('key').replace('/video/jmm/proxy/','').decode("hex")}

        JMM_Shows[jmmId]['seasons'] = processSeason(seasonItem)
      elif season.get('type') == 'show':
        JMM_Shows[jmmId] = processGroup(season.get('key').replace('/video/jmm/proxy/','').decode("hex"))

  Log("JMM_Files_Map %d items" %(len(JMM_Files_Map)))

def processGroup(url):
  channelShowsPage = xmlFromJMMChannel(url)
  for show in channelShowsPage.iterchildren('Directory'):
    if show.get('type') == 'season':
      showItem = {'title': show.get('title'), 'image': show.get('thumb'), 'year': show.get('year'), 'url': show.get('key').replace('/video/jmm/proxy/','').decode("hex")}
      if show.get('season'):
        showItem['season'] = show.get('season')
      else:
        showItem['season'] = '0'
      return processSeason(showItem)

def processSeason(showItem):
  channelShowsPage = xmlFromJMMChannel(showItem['url'])
  count = 0
  seasons = {}
  for season in channelShowsPage.iterchildren('Directory'):
    url = season.get('key').replace('/video/jmm/proxy/','').decode("hex")
    count = count + 1
    seasonItem = {'title': season.get('title'), 'url': url, 'image': season.get('thumb'), 'year': showItem['year'], 'season': showItem['season'], 'showTitle': showItem['title']}
    seasons[seasonItem['title']] = processEpisodes(seasonItem, season.get('title'), url)
  
  if count == 0: #No specials, only episodes, thus no folders
    try: seasonItem = {'title': 'Episodes', 'url': showItem['url'], 'image': showItem['image'], 'year': showItem['year'], 'season': showItem['season'], 'showTitle': showItem['title']}
    except: Debug('showItem ' + str(showItem))
    seasons[seasonItem['title']] = processEpisodes(seasonItem, seasonItem['title'], showItem['url'])
  
  return seasons;

def processEpisodes(seasonItem, folder, url):
  global JMM_Files_Map
  if folder == 'Episodes':
    folder = 'Season '+seasonItem['season']

  seasonItem['title'] = folder;
  seasonItem['episodes'] = {}

  page = xmlFromJMMChannel(url)
  for video in page.iterchildren('Video'):
    if video.get('type')  == 'movie':
      episodeIndex = 1
    else:
      episodeIndex = video.get('index')
    videoItem = {'image': video.get('thumb'), 'index': episodeIndex, 'type': video.get('type'), 'title': video.get('title'), 'folder': folder, 'showTitle': seasonItem['showTitle'], 'year': seasonItem['year']}
    for media in video.iterchildren('Media'):
      for part in media.iterchildren('Part'):
        videoItem['file'] = part.get('file')
    JMM_Files_Map[videoItem['file']] = videoItem
    seasonItem['episodes'][episodeIndex] = videoItem

  return seasonItem

def logEx():
  return "reason %s, value: %s" % (sys.exc_info()[0],sys.exc_info()[1])

def Scan(path, files, mediaList, subdirs, language=None, root=None, **kwargs):
  for f in files:
    fname = f.replace('AnimeTest','Anime')
    if fname in JMM_Files_Map:
      match = JMM_Files_Map[fname]
      #Log("Got match %s is %s" %(f, JMM_Files_Map[fname]))
      if match['folder'].startswith('Season '):
        season = int(match['folder'].replace('Season ',''));
      else:
        season = 0

      try:
        tv_show = Media.Episode(match['showTitle'], season, int(match['index']), match['title'], int(match['year']))
        #Log("TV show %s" %(str(tv_show)))
        tv_show.parts.append(f); #
        mediaList.append(tv_show) 
      except:
        Log(logEx())

Start()