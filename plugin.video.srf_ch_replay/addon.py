import sys
import json
import urllib.request
import urllib.parse
import socket
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import traceback
from io import StringIO
import gzip
from urllib.parse import urlparse
from string import ascii_lowercase

# imports for new API
import requests
import base64
import datetime


#'Base settings'
#'Start of the plugin functionality is at the end of the file'
addon = xbmcaddon.Addon()
addonID = 'plugin.video.srf_ch_replay'
pluginhandle = int(sys.argv[1])
socket.setdefaulttimeout(30)
xbmcplugin.setPluginCategory(pluginhandle, "News")
xbmcplugin.setContent(pluginhandle, "tvshows")
addon_work_folder = xbmcvfs.translatePath("special://profile/addon_data/" + addonID)
if not os.path.isdir(addon_work_folder):
    os.mkdir(addon_work_folder)
FavoritesFile = xbmcvfs.translatePath("special://profile/addon_data/" + addonID + "/" + addonID + ".favorites")
numberOfEpisodesPerPage = str(addon.getSetting("numberOfShowsPerPage"))
useOfficialApi = addon.getSetting("useOfficialApi") == "true"
consumerKey = addon.getSetting("consumerKey")
consumerSecret = addon.getSetting("consumerSecret")
tr = addon.getLocalizedString
default_channel = 'srf'


#####################################
# NEW SRF Podcast Plugin api methods
#####################################

SRG_API_HOST = "api.srgssr.ch"

# TODO (milestone 3) other than srf channel -> not stable yet; this should be investigated
def choose_channel():
    nextMode = 'chooseTvShowLetter'
    _add_channel(default_channel, tr(30014), nextMode)
    _add_channel('swi', tr(30015), nextMode)
    _add_channel('rts', tr(30016), nextMode)
    _add_channel('rsi', tr(30017), nextMode)
    _add_channel('rtr', tr(30018), nextMode)
    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def list_tv_shows_new(channel, letter):
    PATH = "/videometadata/v2/tv_shows/alphabetical"
    query = {"bu": channel, "characterFilter": letter}
    response = _srg_get(PATH, query=query)
    shows = response["showList"]
    mode = 'listEpisodes'

    for show in shows:
        showid = show.get('id')
        title = show.get('title')
        desc = show.get('description')
        picture = show.get('imageUrl')
        _add_show(title, showid, mode, desc, picture, "", channel)

    xbmcplugin.addSortMethod(pluginhandle, 1)
    xbmcplugin.endOfDirectory(pluginhandle)
    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def list_episodes_new(channel, showid, showbackground, page):
    PATH = f"/videometadata/v2/latest_episodes/shows/{showid}"
    query = {"bu": channel}
    if page:
        query.update({"next": page})
    else:
        query.update({"pageSize": numberOfEpisodesPerPage})
    response = _srg_get(PATH, query=query)
    show = response['show']
    episodeList = response["episodeList"]

    for episode in episodeList:
        title = show.get('title') + ' - ' + episode.get('title')
        desc = episode.get('description')
        pubdate = episode.get('publishedDate')
        media = episode.get('mediaList')[0]
        url = media.get('id')
        picture = media.get('imageUrl')
        length = int(media.get('duration', 0)) / 1000 / 60
        _addLink(title, url, 'playepisode', desc, picture, length, pubdate, showbackground, channel)

    next_page_url = response.get('next')
    if next_page_url:
        next_param = urllib.parse.parse_qs(urllib.parse.urlparse(next_page_url).query).get('next')[0]
        # TODO: No page number available ==> can be calculated with the numberOfShowsPerPage param
        _addnextpage(tr(30005).format("?", "?"), showid, 'listEpisodes', '', showbackground, next_param, channel)

    xbmcplugin.endOfDirectory(pluginhandle)


def _add_channel(channelId, name, mode):
    directoryurl = sys.argv[0] + "?channel=" + str(channelId) + "&mode=" + str(mode)
    liz = xbmcgui.ListItem(name)
    return xbmcplugin.addDirectoryItem(pluginhandle, url=directoryurl, listitem=liz, isFolder=True)


def _srg_get(path, query):
    token = _srg_api_auth_token()
    if token:
        r = _srg_api_get(path, bearer=token, query=query, exp_code=200)
    return r.json()


def _srg_api_get(path, *, query=None, bearer, exp_code=None):
    headers = {}
    if bearer:
        headers.update({"Authorization": f"Bearer {bearer}"})
    return _http_request(SRG_API_HOST, 'GET', path, query, headers, None, exp_code)


def _srg_api_auth_token():
    
    token_ts = addon.getSetting('srgssrTokenTS')
    if token_ts: 
        delta_ts = datetime.datetime.utcnow() - datetime.datetime.fromisoformat(token_ts)
        token = addon.getSetting('srgssrToken')
        if delta_ts < datetime.timedelta(days=25) and token:
            return token

    query = {"grant_type": "client_credentials"}
    headers = {"Authorization": "Basic " + str(base64.b64encode(f"{consumerKey}:{consumerSecret}".encode("utf-8")), "utf-8")}
    r = _http_request(SRG_API_HOST, 'POST', "/oauth/v1/accesstoken", query=query, headers=headers, exp_code=200)
    access_token = r.json()["access_token"]
    addon.setSetting('srgssrToken', access_token)
    addon.setSetting('srgssrTokenTS', datetime.datetime.utcnow().isoformat())
    return access_token


def _http_request(host, method, path, query=None, headers={}, body_dict=None, exp_code=None):
    uri = f'https://{host}{path}'
    xbmc.log(f"request: {method} {uri}")
    res = requests.request(method, uri, params=query, headers=headers, json=body_dict)
    if exp_code:
        if type(exp_code) is not list:
            exp_code = [exp_code]
        if (res.status_code not in exp_code):
            raise Exception(str(res.status_code) + ':' + res.text)
    return res


#####################################
# OLD SRF Podcast Plugin api methods
#####################################

def list_all_tv_shows(letter):
    """
    this method list all available TV shows
    """
    url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/srf/tv/assetGroup/'
    response = json.load(_open_srf_url(url))
    shows = response["AssetGroups"]["Show"]
    title = ''
    desc = ''
    picture = ''
    page = 1
    mode = 'listEpisodes'
    for show in shows:
        try:
            title = show['title']
        except:
            title = tr(30007)
        try:
            desc = show['description']
        except:
            desc = tr(30008)
        try:
            picture = show['Image']['ImageRepresentations']['ImageRepresentation'][0]['url']
        except:
            picture = ''

        firstTitleLetter = title[:1]
        if (firstTitleLetter.lower() == letter) or (not firstTitleLetter.isalpha() and not str(letter).isalpha()):
            _add_show(title, show['id'], mode, desc, picture, page, default_channel)

    xbmcplugin.addSortMethod(pluginhandle, 1)
    xbmcplugin.endOfDirectory(pluginhandle)
    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def list_all_episodes(showid, showbackground, page):
    """
    this method list all episodes of the selected show
    """
    url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/srf/assetSet/listByAssetGroup/' + showid + '.json?pageNumber=' + str(page) + "&pageSize=" + str(numberOfEpisodesPerPage)
    response = json.load(_open_srf_url(url))
    maxpage = 1
    try:
        maxpage = response["AssetSets"]["@maxPageNumber"]
    except:
        maxpage = 0

    show = response["AssetSets"]["AssetSet"]

    for episode in show:
        title = episode['title']
        url = ''
        desc = ''
        picture = ''
        pubdate = episode['publishedDate']

        try:
            desc = episode['Assets']['Video'][0]['AssetMetadatas']['AssetMetadata'][0]['description']
        except:
            desc = tr(30008)
        try:
            picture = episode['Assets']['Video'][0]['Image']['ImageRepresentations']['ImageRepresentation'][0]['url']
        except:
            # no picture
            picture = ''
        try:
            length = int(episode['Assets']['Video'][0]['duration']) / 1000 / 60
        except:
            length = 0
        try:
            url = episode['Assets']['Video'][0]['id']
        except:
            url = tr(30009)
        try:
            titleextended = ' - ' + episode['Assets']['Video'][0]['AssetMetadatas']['AssetMetadata'][0]['title']
        except:
            titleextended = ''

        _addLink(title + titleextended, url, 'playepisode', desc, picture, length, pubdate, showbackground, default_channel)

    # check if another page is available
    page = int(page)
    maxpage = int(maxpage)
    if page < maxpage or maxpage == 0 and len(show) == int(numberOfEpisodesPerPage):
        page = page + 1
        _addnextpage(tr(30005).format(page, maxpage), showid, 'listEpisodes', '', showbackground, page, default_channel)

    xbmcplugin.endOfDirectory(pluginhandle)


#####################################
# Common methods
#####################################

def play_episode(episodeid):
    """
    this method plays the selected episode
    """

    besturl = ''

    try:
        url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/srf/video/play/' + episodeid + '.json'
        response = json.load(_open_srf_url(url))
        playlistVector = response['Video']['Playlists']['Playlist']

        # filter objects with list comprehensions
        playlist = [obj for obj in playlistVector if obj['@protocol'] == 'HTTP-HLS']

        playlistVector = playlist[0]
        urls = playlistVector['url']

        besturl = urls[0]['text']
        for tempurl in urls:
            if tempurl['@quality'] == 'HD':
                besturl = tempurl['text']
                break

    except:
        xbmc.log(traceback.format_exc())

    if besturl == '':
        try:
            url = 'http://il.srgssr.ch/integrationlayer/1.0/ue/srf/video/play/' + episodeid + '.json'
            response = json.load(_open_srf_url(url))
            urls = response['Video']['Playlists']['Playlist'][0]['url']

            besturl = urls[0]['text']
            for tempurl in urls:
                if tempurl['@quality'] == 'HD':
                    besturl = tempurl['text']
                    break

        except:
            xbmc.log(traceback.format_exc())

    # add authentication token for akamaihd
    if "akamaihd" in urlparse(besturl).netloc:
        url = "http://tp.srgssr.ch/akahd/token?acl=" + urlparse(besturl).path
        response = json.load(_open_srf_url(url))
        token = response["token"]["authparams"]
        besturl = besturl + '?' + token

    listitem = xbmcgui.ListItem(path=besturl)
    xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)


def _open_srf_url(urlstring):
    request = urllib.request.Request(urlstring)
    request.add_header('Accept-encoding', 'gzip')
    response = ''
    try:
        response = urllib.request.urlopen(urlstring)
        if response.info().get('Content-Encoding') == 'gzip':
            buf = StringIO(response.read())
            f = gzip.GzipFile(fileobj=buf)
            response = StringIO(f.read())
    except Exception as e:
        xbmc.log(traceback.format_exc())
        xbmcgui.Dialog().ok(tr(30006), str(e.__class__.__name__), str(e))
    return response


def choose_tv_show_letter(channel):
    nextMode = 'listTvShows'
    _add_letter(channel, '#', tr(30019), nextMode)
    for c in ascii_lowercase:
        _add_letter(channel, c, c, nextMode)
    xbmcplugin.endOfDirectory(handle=pluginhandle, succeeded=True)


def _add_letter(channel, letter, letterDescription, mode):
    directoryurl = sys.argv[0] + "?mode=" + str(mode) + "&channel=" + str(channel) + "&letter=" + letter
    liz = xbmcgui.ListItem(letterDescription)
    return xbmcplugin.addDirectoryItem(pluginhandle, url=directoryurl, listitem=liz, isFolder=True)


def _add_show(name, url, mode, desc, iconimage, page, channel):
    """
    helper method to create a folder with subitems
    """
    directoryurl = sys.argv[0] + "?url=" + urllib.parse.quote_plus(url) + "&mode=" + str(mode) + "&showbackground=" + urllib.parse.quote_plus(iconimage) + "&page=" + str(page) + "&channel=" + str(channel)
    liz = xbmcgui.ListItem(name)
    liz.setLabel2(desc)
    liz.setArt({'poster': iconimage, 'banner': iconimage, 'fanart': iconimage, 'thumb': iconimage})
    liz.setInfo(type="Video", infoLabels={"title": name, "plot": desc, "plotoutline": desc})
    xbmcplugin.setContent(pluginhandle, 'tvshows')
    ok = xbmcplugin.addDirectoryItem(pluginhandle, url=directoryurl, listitem=liz, isFolder=True)
    return ok


def _addLink(name, url, mode, desc, iconurl, length, pubdate, showbackground, channel):
    """
    helper method to create an item in the list
    """
    linkurl = sys.argv[0] + "?url=" + urllib.parse.quote_plus(url) + "&mode=" + str(mode) + "&channel=" + str(channel)
    liz = xbmcgui.ListItem(name)
    liz.setLabel2(desc)
    liz.setArt({'poster': iconurl, 'banner': iconurl, 'fanart': showbackground, 'thumb': iconurl})
    liz.setInfo(type='Video', infoLabels={"Title": name, "Duration": length, "Plot": desc, "Aired": pubdate})
    liz.setProperty('IsPlayable', 'true')
    xbmcplugin.setContent(pluginhandle, 'episodes')
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=linkurl, listitem=liz)
    return ok


def _addnextpage(name, url, mode, desc, showbackground, page, channel):
    """
    helper method to create a folder with subitems
    """
    directoryurl = sys.argv[0] + "?url=" + urllib.parse.quote_plus(url) + "&mode=" + str(mode) + "&showbackground=" + urllib.parse.quote_plus(showbackground) + "&page=" + str(page) + "&channel=" + str(channel)
    liz = xbmcgui.ListItem(name)
    liz.setLabel2(desc)
    #liz.setArt({'poster' : '' , 'banner' : '', 'fanart' : showbackground, 'thumb' : ''})
    liz.setInfo(type="Video", infoLabels={"title": name, "plot": desc, "plotoutline": desc})
    xbmcplugin.setContent(pluginhandle, 'episodes')
    ok = xbmcplugin.addDirectoryItem(pluginhandle, url=directoryurl, listitem=liz, isFolder=True)
    return ok


def _parameters_string_to_dict(parameters):
    """
    helper method to retrieve parameters in a dict from the arguments given to this plugin by xbmc
    """
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict


#####################################
# Start
#####################################
params = _parameters_string_to_dict(sys.argv[2])
mode = params.get('mode', '')
url = params.get('url', '')
showbackground = urllib.parse.unquote_plus(params.get('showbackground', ''))
page = params.get('page', '')
channel = params.get('channel', default_channel)
letter = params.get('letter', '')

if useOfficialApi:
    if mode == 'playepisode':
        play_episode(url)
    elif mode == 'listEpisodes':
        list_episodes_new(channel, url, showbackground, page)
    elif mode == 'listTvShows':
        list_tv_shows_new(channel, letter)
    elif mode == 'chooseTvShowLetter':
        choose_tv_show_letter(channel)
    else:
        choose_tv_show_letter(channel)
        # TODO (milestone 3) other channels than SRF are not stable yet
        # choose_channel()
else:
    if mode == 'playepisode':
        play_episode(url)
    elif mode == 'listEpisodes':
        list_all_episodes(url, showbackground, page)
    elif mode == 'listTvShows':
        list_all_tv_shows(letter)
    else:
        choose_tv_show_letter(channel)
