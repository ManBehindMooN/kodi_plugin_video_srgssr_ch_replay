from string import ascii_lowercase
import sys
from urllib.parse import urlencode, parse_qsl, quote_plus, urlparse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import inputstreamhelper

from resources.lib.settings import Settings
from resources.lib.logger import Logger
from resources.lib.srgssr_video_api_client import SRGSSRVideoApiClient


class Plugin:
    KODI_VERSION_MAJOR = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
    ADDON = xbmcaddon.Addon()
    ADDON_ID = ADDON.getAddonInfo("id")
    ADDON_URL = f"plugin://{ADDON_ID}"
    HANDLE = int(sys.argv[1])
    SRG_API_BASE_URL = "https://api.srgssr.ch"

    settings = Settings()

    def __init__(self):
        # strings translation
        self.tr = self.ADDON.getLocalizedString

        self.logger = Logger(self)

        xbmcplugin.setPluginCategory(self.HANDLE, "News")
        xbmcplugin.setContent(self.HANDLE, "tvshows")

        # Check that DownDog account credentials are passed
        while self.settings.consumer_key == "" or self.settings.consumer_secret == "":
            xbmcgui.Dialog().ok(self.tr(31001), self.tr(31002))
            self.ADDON.openSettings()

        self.vclient = SRGSSRVideoApiClient(
            self.SRG_API_BASE_URL,
            {"key": self.settings.consumer_key, "secret": self.settings.consumer_secret},
            self,
        )
   
    def run(self):
        """Plugin main method"""
        self.logger.info("Starting SRGSSR plugin")
        self.router(sys.argv[2][1:])    # passes the params (without the ?) to the router
        self.logger.info("End of SRGSSR plugin")

    def router(self, paramstring: str):
        """Routes to the different pages or actions of the plugin
        :param paramstring: The URL parameters (after the ?)
        """
        params = dict(parse_qsl(paramstring))

        mode = params.get("mode", "")
        bu = params.get("channel")

        if mode == "playEpisode":
            media_id = params.get("mediaId", "")
            self.play_episode(bu, media_id)
        elif mode == "listEpisodes":
            tvshow_id = params.get("tvShowId")
            current_page = int(params.get("currentPage", 1))
            number_of_episodes = int(params.get("numberOfEpisodes", 0))
            next_page_id = params.get("nextPageId", "")
            self.list_episodes(bu, tvshow_id, current_page, number_of_episodes, next_page_id)
        elif mode == "listTvShowsByLetter":
            letter = params.get("letter")
            self.list_tv_shows(bu, letter)
        elif mode == "searchTvShows":
            self.search_tv_shows()
        elif mode == "chooseTvShowOption":
            self.choose_tv_show_option(bu)
        else:
            # Called without params
            self.choose_business_unit()

    def choose_business_unit(self):
        """List the Business Units"""
        nextMode = "chooseTvShowOption"
        business_units = [
            ("srf", self.tr(30014)),
            ("swi", self.tr(30015)),
            ("rts", self.tr(30016)),
            ("rsi", self.tr(30017)),
            ("rtr", self.tr(30018)),
        ]

        for bu in business_units:
            self._add_menu_to_directory(bu[1], {"channel": bu[0], "mode": nextMode})
        xbmcplugin.endOfDirectory(self.HANDLE, succeeded=True)

    def choose_tv_show_option(self, bu: str):
        """List the letters to filter tv shows"""
        nextMode = "listTvShowsByLetter"
        url_args = {"channel": bu, "mode": nextMode}

        url_args.update({"letter": "#"})
        self._add_menu_to_directory(self.tr(30019), url_args)
        
        for char in ascii_lowercase:
            url_args.update({"letter": char})
            self._add_menu_to_directory(char, url_args)
        
        url_args.update({"mode": "searchTvShows"})
        url_args.pop("letter")
        self._add_menu_to_directory(self.tr(30021), url_args)
        xbmcplugin.endOfDirectory(self.HANDLE, succeeded=True)

    def list_tv_shows(self, bu: str, char_filter: str):
        """Lists the TV shows filtered by the first letter"""
        nextMode = "listEpisodes"
        xbmcplugin.setContent(self.HANDLE, "tvshows")

        shows = self.vclient.get_tv_shows(bu, char_filter)["showList"]
        for show in shows:
            image_url = show.get("imageUrl", "")
            
            description = show.get("description")
            if not description:     # sometimes lead contains info
                description = show.get("lead", "")

            url_args = {
                "channel": bu,
                "mode": nextMode,
                "numberOfEpisodes": show.get("numberOfEpisodes", 0),
                "tvShowId": quote_plus(show.get("id")),
            }

            self._add_tvshow_to_directory(
                name=show.get("title", ""),
                desc=description,
                image_url=image_url,
                url_args=url_args,
            )

        xbmcplugin.addSortMethod(self.HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory(self.HANDLE, succeeded=True)

    def list_episodes(self, bu: str, tvshow_id: str, current_page, number_of_episodes, next_page_id=""):
        """Lists the latest episodes of a TV Show
        :param bu: Business Unit (either 'srf', 'rtr', 'swi', 'rts', 'rsi')
        :param tvshow_id: The id of the TV Show
        :param current_page: Index of the current episodes page
        :param number_of_episodes: Total number of episodes of the show
        :param next_page_id: ID of the next page of episodes
        """
        xbmcplugin.setContent(self.HANDLE, "episodes")
        number_of_episodes_per_page = int(self.settings.number_of_episodes_per_page)
        
        self.logger.debug(f"Next page url from router: {next_page_id}")
        res = self.vclient.get_latest_episodes(bu, tvshow_id, number_of_episodes_per_page, next_page_id)
        show = res.get("show")
        episodes = res.get("episodeList")

        if show and episodes:
            for episode in episodes:
                media = episode.get("mediaList")[0]
                
                url_args = {
                    "channel": bu,
                    "mode": "playEpisode",
                    "mediaId": media.get("id"),
                }
                
                self._add_episode_to_directory(
                    name=episode.get("title", "") + " - " + media.get("title", ""),
                    desc=media.get("description", ""),
                    length=int(media.get("duration", 0)/1000/60),
                    pubdate=episode.get("publishedDate", ""),
                    tvshow_image_url=show.get("imageUrl", ""),
                    image_url=episode.get("imageUrl", ""),
                    url_args=url_args,
                )
            
            next_page_url = res.get("next")
            if next_page_url:
                next_page_id = dict(parse_qsl(urlparse(next_page_url).query)).get("next")
                self.logger.debug(f"NEXT from API: {next_page_id}")
                number_of_pages = int((number_of_episodes_per_page - 1 + number_of_episodes) / number_of_episodes_per_page)
                self._add_next_page_to_directory(
                    name=self.tr(30020).format(current_page, number_of_pages or "?"),
                    desc=str(current_page + 1),
                    url_args={"channel": bu, "mode": "listEpisodes", "nextPageId": next_page_id, "tvShowId": quote_plus(show.get("id")),}
                )
        
        xbmcplugin.endOfDirectory(self.HANDLE, succeeded=True)
    
    def play_episode(self, bu: str, media_id: str):
        """Plays the selected episode
        :param bu: Business Unit (either 'srf', 'rtr', 'swi', 'rts', 'rsi')
        :param media_id: The media ID
        """
        media_composition = self.vclient.get_media_composition(bu, media_id)
        resource = self._get_media_resource(media_composition)
        parsed_url = urlparse(resource["url"])
        media_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        # TODO: How auth works? DRM? 

        liz = xbmcgui.ListItem(path=media_url)
        liz.setProperty("isPlayable", "true")
        self._set_inputstream_params(liz, resource["protocol"].lower(), resource["mimeType"])
        # TODO: add subtitles
        xbmcplugin.setResolvedUrl(self.HANDLE, True, liz)

    
    def _get_media_resource(self, media_composition) -> dict:
        """Parses the media composition object to find the best resource and return it"""
        resourceList = media_composition["chapterList"][0]["resourceList"]
        sdHlsResources = []
        for resource in resourceList:
            if resource["protocol"] == "HLS":
                if resource["quality"] == "HD":
                    return resource
                else:
                    sdHlsResources.append(resource)

        if not sdHlsResources:
            return resourceList[0]
        else:
            return sdHlsResources[0]

    def _set_inputstream_params(self, listitem, protocol, mimeType):
        """If Inputstream Adaptive is available, configure it"""

        is_helper = inputstreamhelper.Helper(protocol)
        if self.settings.enable_inputstream_adaptive and is_helper.check_inputstream():
            listitem.setContentLookup(False)
            listitem.setMimeType(mimeType)
            listitem.setProperty("inputstream", is_helper.inputstream_addon)
            listitem.setProperty("inputstream.adaptive.manifest_type", protocol)


    # ================================= Helper methods ==================================

    def _url(self, **kwargs):
        """Constructs the plugin's URL"""
        return f"{self.ADDON_URL}?{urlencode(kwargs)}"

    def _add_menu_to_directory(self, name, url_args=None):
        """Helper method that adds a "Menu" Item to the xbmcplugin Directory
        :param name: The name of the item
        :param url_args: A dictionary containing the URL arguments
        """
        if url_args is None:
            url_args = {}
        
        liz = xbmcgui.ListItem(name)
        xbmcplugin.addDirectoryItem(
            self.HANDLE,
            url=self._url(**url_args),
            listitem=liz,
            isFolder=True,
        )

    def _add_tvshow_to_directory(self, name, desc="", image_url="", url_args=None):
        """Helper method that adds a TVShow Item to the xbmcplugin Directory"""
        if url_args is None:
            url_args = {}
        
        liz = xbmcgui.ListItem(name, desc)
        liz.setArt({"poster": image_url, "banner": image_url, "fanart": image_url, "thumb": image_url})
        liz.setInfo(type="video", infoLabels={"title": name, "plot": desc, "plotoutline": desc})
        xbmcplugin.addDirectoryItem(
            self.HANDLE,
            url=self._url(**url_args),
            listitem=liz,
            isFolder=True,
        )

    def _add_episode_to_directory(self, name, desc="", length="", pubdate="", tvshow_image_url="", image_url="", url_args=None):
        """Helper method that adds a Video Item to the xbmcplugin Directory"""
        if url_args is None:
            url_args = {}
        
        liz = xbmcgui.ListItem(name, desc)
        liz.setArt({"poster": image_url, "banner": image_url, "fanart": tvshow_image_url, "thumb": image_url})
        liz.setInfo(type="Video", infoLabels={"Title": name, "Duration": length, "Plot": desc, "Aired": pubdate})
        liz.setProperty("IsPlayable", "true")
        xbmcplugin.addDirectoryItem(self.HANDLE, url=self._url(**url_args), listitem=liz)
    
    def _add_next_page_to_directory(self, name, desc, url_args=None):
        """Helper method that adds a "next page" Item to the xbmcplugin Directory"""
        if url_args is None:
            url_args = {}
        
        liz = xbmcgui.ListItem(name, desc)
        liz.setInfo(type="Video", infoLabels={"title": name, "plot": desc, "plotoutline": desc})
        xbmcplugin.addDirectoryItem(
            self.HANDLE,
            url=self._url(**url_args),
            listitem=liz,
            isFolder=True,
        )
