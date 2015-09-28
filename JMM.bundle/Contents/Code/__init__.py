# -*- coding: utf-8 -*-
### JMM Metadata Agent v0.1

import os, re, time, datetime, string, thread, threading, urllib, sys, traceback # Functions used per module: os (read), re (sub, match), time (sleep), datetim (datetime).
### AniDB, TVDB, AniDB mod agent for XBMC XML's, and Plex URL and path variable definition ###########################################################################
JMM_CHANNEL_URL = 'http://127.0.0.1:8111/JMMServerPlex/GetFilters/1'

### Global variables ###
lastRequestTime = None  #ValueError if in Start()
JMM_Shows, JMM_Files_Map = None, None

### Pre-Defined ValidatePrefs function Values in "DefaultPrefs.json", accessible in Settings>Tab:Plex Media Server>Sidebar:Agents>Tab:Movies/TV Shows>Tab:HamaTV #######
def ValidatePrefs():
  result, msg = ('Success', 'JMM - Provided preference values are ok')
  for key in ['jmmServer']: #for key, value in enumerate(settings):
    try:    temp = Prefs[key] 
    except: result, msg = ('Error', "Couldn't get values '%s', probably a missing/empty/outdated 'DefaultPrefs.json' so replace it" % key)
  if result=='Error':  Log.Error(msg)
  return MessageContainer(result, msg)
   
### Pre-Defined Start function #########################################################################################################################################
def Start():
  Log.Debug('### JMM Metadata Agent Started ##############################################################################################################')
  msgContainer = ValidatePrefs()  ##if key not in Prefs: Log.Error("Couldn't get values '%s', probably a missing/empty/outdated 'DefaultPrefs.json' so replace it" % key)
  global JMM_file_tree, JMM_Shows, JMM_Files_Map  # only this one to make search after start faster
  HTTP.CacheTime                   = CACHE_1HOUR * 24 * 7                  # Cache time for Plex XML and html pages
  channelMainPage = JMMAgent().xmlFromJMMChannel(JMM_CHANNEL_URL)
  allUrl = None
  try: 
    for directory in channelMainPage.findall('./Directory'): #/MediaContainer/Directory/@key[@title="All"]
      if directory.attrib['title'] == 'All':
        allUrl = directory.attrib['key']
  except:  
    Log.Debug("Start - XPath issue, result: %s" %(logEx()))
    return

  Log.Debug("Start allUrl: %s" %(allUrl))

  JMM_Shows = {}
  JMM_Files_Map = {}
  channelShowsPage = JMMAgent().xmlFromJMMChannel(allUrl.replace('/video/jmm/proxy/','').decode("hex"))
  for season in channelShowsPage.findall('./Directory'): #/MediaContainer/Directory/@key[@title="All"]
      if season.attrib['type'] == 'season':
        seasonItem = {'title': season.attrib['title'], 'rating': season.attrib['rating'], 'summary': season.attrib['summary'], 'image': season.attrib['thumb'], 'year': season.attrib['year'], 'url': season.attrib['key'].replace('/video/jmm/proxy/','').decode("hex")}
        if 'season' in season.attrib:
          seasonItem['season'] = season.attrib['season']
        else:
          seasonItem['season'] = '1'
        jmmId = seasonItem['title'].encode('hex')
        #Log.Debug('Season ' + str(seasonItem))
        if not jmmId in JMM_Shows:
          JMM_Shows[jmmId] = {'seasons': {}, 'title': season.attrib['title'], 'rating': season.attrib['rating'], 'summary': season.attrib['summary'], 'image': season.attrib['thumb'], 'year': season.attrib['year'], 'url': season.attrib['key'].replace('/video/jmm/proxy/','').decode("hex")}

        JMM_Shows[jmmId]['seasons'] = processSeason(seasonItem)
        Log.Debug('Complete Season ' + str(JMM_Shows[jmmId]))
      elif season.attrib['type'] == 'show':
        JMM_Shows[jmmId] = processGroup(season.attrib['key'].replace('/video/jmm/proxy/','').decode("hex"))
        Log.Debug('Complete Season ' + str(JMM_Shows[jmmId]))

  Log.Debug("JMM_Files_Map %d items" %(len(JMM_Files_Map)))
  Log.Debug('### JMM Metadata Agent Ended ################################################################################################################')
  time.strptime("30 Nov 00", "%d %b %y")  # Avoid "AttributeError: _strptime" on first call [http://bugs.python.org/issue7980]

def processGroup(url):
  channelShowsPage = JMMAgent().xmlFromJMMChannel(url)
  for season in channelShowsPage.findall('./Directory'): #/MediaContainer/Directory/@key[@title="All"]
    if season.attrib['type'] == 'season':
      seasonItem = {'title': season.attrib['title'], 'image': season.attrib['thumb'], 'year': season.attrib['year'], 'url': season.attrib['key'].replace('/video/jmm/proxy/','').decode("hex")}
      if 'season' in season.attrib:
        seasonItem['season'] = season.attrib['season']
      else:
        seasonItem['season'] = '0'
      Log.Debug('Group ' + str(seasonItem))
      return processSeason(seasonItem)

def processSeason(showItem):
  channelShowsPage = JMMAgent().xmlFromJMMChannel(showItem['url'])
  count = 0
  seasons = {}
  for season in channelShowsPage.findall('./Directory'): #/MediaContainer/Directory/@key[@title="All"]
    url = season.attrib['key'].replace('/video/jmm/proxy/','').decode("hex")
    count = count + 1
    seasonItem = {'title': season.attrib['title'], 'url': url, 'image': season.attrib['thumb'], 'year': showItem['year'], 'season': showItem['season'], 'showTitle': showItem['title']}
    seasons[seasonItem['title']] = processEpisodes(seasonItem, season.attrib['title'], url)
  
  if count == 0: #No specials, only episodes, thus no folders
    try: seasonItem = {'title': 'Episodes', 'url': showItem['url'], 'image': showItem['image'], 'year': showItem['year'], 'season': showItem['season'], 'showTitle': showItem['title']}
    except: Log.Debug('showItem ' + str(showItem))
    seasons[seasonItem['title']] = processEpisodes(seasonItem, seasonItem['title'], showItem['url'])
  
  return seasons;

def processEpisodes(seasonItem, folder, url):
  global JMM_Files_Map
  if folder == 'Episodes':
    folder = 'Season '+seasonItem['season']

  seasonItem['title'] = folder;
  seasonItem['episodes'] = {}

  page = JMMAgent().xmlFromJMMChannel(url)
  for video in page.findall('./Video'):
    if video.attrib['type']  == 'movie':
      episodeIndex = 1
    else:
      episodeIndex = video.attrib['index']
    videoItem = {'image': video.attrib['thumb'], 'index': episodeIndex, 'type': video.attrib['type'], 'title': video.attrib['title'], 'folder': folder, 'showTitle': seasonItem['showTitle'], 'year': seasonItem['year']}
    for part in video.findall('./Media/Part'):
      videoItem['file'] = part.attrib['file']
    #Log.Debug('Video ' + str(videoItem))
    JMM_Files_Map[videoItem['file']] = videoItem
    seasonItem['episodes'][episodeIndex] = videoItem

  return seasonItem


def logBT():
  return ''.join(traceback.format_stack(sys.exc_info()[2]))

def logEx():
  return "reason %s, value: %s" % (sys.exc_info()[0],sys.exc_info()[1])

### Metadata agent ################################################################################################################################################
class JMMAgent(Agent.TV_Shows):
  name, primary_provider, fallback_agent, contributes_to, languages, accepts_from = ('JMMTV', True, False, None, [Locale.Language.English,], ['com.plexapp.agents.localmedia', 'com.plexapp.agents.opensubtitles'] )
  ### Serie search ###
  def search(self, results,  media, lang, manual):
    global JMM_Files_Map
    Log.Debug("=== Search - Begin - ================================================================================================")
    Log.Info("search() - Title: '%s', name: '%s', filename: '%s', manual:'%s'" % (media.show, media.name, media.filename, str(manual)))      #if media.filename is not None: filename = String.Unquote(media.filename) #auto match only
    if media.filename is not None: 
      filename = String.Unquote(media.filename)
      if filename in JMM_Files_Map:
        match = JMM_Files_Map[filename]
        Log.Debug('Found match: %s' %(str(match)))
        results.Append(MetadataSearchResult(id="%s-%s" % ('jmm', match['showTitle'].encode('hex')),  name=match['showTitle'], year=match['year'], lang=Locale.Language.English, score=100)) #episode=match['index'], season=match['folder'],
    Log.Debug("=== Search - End - ==================================================================================================")

  def update(self, metadata, media, lang, force ):
    global JMM_Shows
    
    Log.Debug("=== Update - Begin - ================================================================================================")
    jmmid = None
    if   metadata.id.startswith("jmm"):  jmmid = metadata.id [len("jmm-"):]
    Log.Debug("update - metadata ID: '%s', JMMID: '%s', Title: '%s',(%s, %s, %s)" % (metadata.id, jmmid, metadata.title, "[...]", "[...]", force) )
      
    if jmmid in JMM_Shows:
      match = JMM_Shows[jmmid]
      Log.Debug('Found match: %s' %(str(match)))
      if not match['image'] in metadata.posters:
        self.metadata_download(metadata.posters,match['image'])
      metadata.summary = match['summary']
      metadata.rating = float (match['rating'])
      metadata.title = match['title']

    Log.Debug("=== Update - End - ==================================================================================================")

  ### Pull down the XML from web and cache it or from local cache for a given anime ID ####################################################################
  def xmlFromJMMChannel(self, url, cache=None):
    #Log.Debug("xmlFromJMMChannel() - url: " + url)    
    result = ''    
    try:    
      result = XML.ElementFromURL(url, headers={'Accept-Encoding':'gzip', 'content-type':'charset=utf8'}, timeout=60, cacheTime=60*30)  #
    except:  
      Log("xmlFromJMMChannel - XML issue, result: '%s', url: '%s', '%s'" %(result, url, logEx()))
      return ""

    return result       

  def metadata_download (self, metatype, url, num=99, filename="", url_thumbnail=None):  #if url in metatype:#  Log.Debug("metadata_download - url: '%s', num: '%s', filename: '%s'*" % (url, str(num), filename)) # Log.Debug(str(metatype))   #  return
    Log.Debug("metadata_download - url: '%s', num: '%d', filename: '%s'" % (url, num, filename))
    file = None #if filename empty no local save
    if filename and Data.Exists(filename):  ### if stored locally load it# Log.Debug("media_download - url: '%s', num: '%s', filename: '%s' was in Hama local disk cache" % (url, str(num), filename))
      try:     file = Data.Load(filename)
      except:  Log.Debug("media_download - could not load file present in cache")
    if file == None: ### if not loaded locally download it
      try:
        if self.http_status_code(url) != 200:  Log.Debug("metadata_download - metadata_download failed, url: '%s', num: '%d', filename: %s" % (url, num, filename));  return
        file = HTTP.Request(url_thumbnail if url_thumbnail else url, cacheTime=None).content
      except:  Log.Debug("metadata_download - error downloading"); return
      else:  ### if downloaded, try saving in cache but folders need to exist
        if not filename == "" and not filename.endswith("/"):
          try:     Data.Save(filename, file)
          except:  Log.Debug("metadata_download - Plugin Data Folder not created for filename '%s', no local cache, or download failed ##########" % (filename))
    try:
      proxy_item = Proxy.Preview(file, sort_order=num) if url_thumbnail else Proxy.Media(file, sort_order=num)
      if url not in metatype or metatype[ url ] != proxy_item:  metatype[ url ] = proxy_item
    except: Log.Debug("metadata_download - issue adding picture to plex - url downloaded: '%s', filename: '%s'" % (url_thumbnail if url_thumbnail else url, filename))
    #metatype.validate_keys( url_thumbnail if url_thumbnail else url ) remove many posters, to avoid

  def http_status_code(self, url):
    a=urllib.urlopen(url)
    if a is not None: return a.getcode()
