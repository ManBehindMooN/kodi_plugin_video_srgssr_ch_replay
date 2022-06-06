from string import ascii_lowercase
import sys
import os
from collections import namedtuple
from typing import Tuple
from urllib.parse import parse_qsl, quote_plus, urlparse, urlsplit

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
import inputstreamhelper

from resources.lib.utils import to_bool
from resources.lib.settings import Settings
from resources.lib.router import Router
from resources.lib.logger import Logger
from resources.lib.srgssr_api_client import (
    SRGSSRVideoApiClient,
    SRGSSRSubtitlesApiClient,
    InvalidCredentialsException,
)


MainMenuItem = namedtuple("MainMenuItem", ["name", "url", "icon"])


class Plugin:
    KODI_VERSION_MAJOR = int(xbmc.getInfoLabel("System.BuildVersion").split(".")[0])
    ADDON = xbmcaddon.Addon()
    ADDON_ID = ADDON.getAddonInfo("id")
    ADDON_URL = f"plugin://{ADDON_ID}"
    HANDLE = int(sys.argv[1])
    SRG_API_BASE_URL = "https://api.srgssr.ch"

    settings = Settings()

    def __init__(self):
        self.tr = self.ADDON.getLocalizedString
        self.icon = self.ADDON.getAddonInfo("icon")
        self.logger = Logger(self)
        self.router = Router(self)
        xbmcplugin.setContent(self.HANDLE, "tv_shows")
        self._create_work_folder()

        # check if default BU is set in the settings
        self.bu = self.settings.default_bu if self.settings.default_bu != "choose" else ""

        try:
            self.video_client, self.subs_client = self._create_api_clients()
        except InvalidCredentialsException as exc:
            xbmcgui.Dialog().ok(self.tr(30096).format(exc.api_name), self.tr(30097))
            sys.exit(1)

    def _create_work_folder(self):
        """Creating the addon work folder"""
        try:
            userdata_path = xbmcvfs.translatePath(self.ADDON.getAddonInfo("profile")).decode(
                "utf-8"
            )
        except AttributeError:
            userdata_path = xbmcvfs.translatePath(self.ADDON.getAddonInfo("profile"))

        if not os.path.isdir(userdata_path):
            os.mkdir(userdata_path)

    def _create_api_clients(self) -> Tuple[SRGSSRVideoApiClient, SRGSSRSubtitlesApiClient]:
        """Creates and returns the Video and Subtitles API clients"""
        self._check_api_credentials_set("consumer_key", "consumer_secret")
        video_client = SRGSSRVideoApiClient(
            self.SRG_API_BASE_URL,
            {
                "key": self.settings.consumer_key,
                "secret": self.settings.consumer_secret,
            },
            self,
        )

        subs_client = None
        if to_bool(self.settings.enable_subtitles):
            self._check_api_credentials_set("consumer_key_subtitles", "consumer_secret_subtitles")
            subs_client = SRGSSRSubtitlesApiClient(
                self.SRG_API_BASE_URL,
                {
                    "key": self.settings.consumer_key_subtitles,
                    "secret": self.settings.consumer_secret_subtitles,
                },
                self,
            )

        return (video_client, subs_client)

    def _check_api_credentials_set(self, key_setting: str, secret_setting: str):
        """Checks that Video or Subtitles API credentials are set, and open the settings if not"""
        while (
            getattr(self.settings, key_setting) == ""
            or getattr(self.settings, secret_setting) == ""
        ):
            xbmcgui.Dialog().ok(self.tr(30099), self.tr(30098))
            self.ADDON.openSettings()

    def _bu_menu_items(self):
        """BU menu items"""
        return [
            MainMenuItem(self.tr(30014), self.router.url("srf"), self.icon),  # TODO custom icons
            MainMenuItem(self.tr(30015), self.router.url("swi"), self.icon),
            MainMenuItem(self.tr(30016), self.router.url("rts"), self.icon),
            MainMenuItem(self.tr(30017), self.router.url("rsi"), self.icon),
            MainMenuItem(self.tr(30018), self.router.url("rtr"), self.icon),
        ]

    def _main_menu_items(self):
        """Main menu items"""
        return [
            MainMenuItem(
                "All TV Shows",
                self.router.url(mode="all_shows"),
                self.icon,  # TODO custom icons
            ),
            MainMenuItem(
                "TV Shows by Letters",
                self.router.url(mode="shows_by_letters"),
                self.icon,
            ),
            MainMenuItem(
                "Search TV Shows",
                self.router.url(mode="search_tv_shows"),
                self.icon,
            ),
            MainMenuItem(
                "Videos by Topics",
                self.router.url(mode="videos_by_topic"),
                self.icon,
            ),
            MainMenuItem(
                "Search Videos",
                self.router.url(mode="search_videos"),
                self.icon,
            ),
        ]

    def run(self):
        """Plugin main method"""
        self.logger.info("Starting SRGSSR plugin")
        self.logger.info(f"Argv[0]: {sys.argv[0]} ; Argv[1]: {sys.argv[1]} ; Argv[2]: {sys.argv[2]} ; ")
        path = urlsplit(sys.argv[0]).path or "/"
        kwargs = dict(parse_qsl(sys.argv[2].lstrip("?")))
        self.router.dispatch(path, **kwargs)
        self.logger.info("End of SRGSSR plugin")


    def bu_menu(self):
        """Builds the Business Units Menu"""
        for bu in self._bu_menu_items():
            self._add_item_to_directory(bu.name, url=bu.url, thumbnailImage=bu.icon, is_folder=True)
        xbmcplugin.endOfDirectory(self.HANDLE)

    def main_menu(self):
        """Builds the Main Menu"""
        for menu in self._main_menu_items():
            self._add_item_to_directory(menu.name, menu.url, thumbnailImage=menu.icon, is_folder=True)
        xbmcplugin.endOfDirectory(self.HANDLE)

    def all_tv_shows(self):
        """Lists all the TV Shows"""
        only_active_shows = (not to_bool(self.settings.show_inactive_shows))
        shows = self.video_client.get_tv_shows(self.bu, only_active_shows=only_active_shows)["showList"]
        self.tv_shows_menu(shows)
        xbmcplugin.endOfDirectory(self.HANDLE)
        
    def tv_shows_by_letter(self, letter: str = ""):
        if not letter:
            self._add_item_to_directory(self.tr(30019), self.router.url(mode="shows_by_letters", **{"letter": "#"}), is_folder=True)
            
            for char in ascii_lowercase:
                self._add_item_to_directory(char, self.router.url(mode="shows_by_letters", **{"letter": char}), is_folder=True)
        else:
            only_active_shows = (not to_bool(self.settings.show_inactive_shows))
            shows = self.video_client.get_tv_shows(self.bu, letter, only_active_shows=only_active_shows)["showList"]
            self.tv_shows_menu(shows)
        xbmcplugin.endOfDirectory(self.HANDLE)

    def search_tv_shows(self):
        search_string = xbmcgui.Dialog().input("Search TV Shows")
        self.logger.info(f"Search string: {search_string}")
        res = self.video_client.get_tv_shows(self.bu, string_filter=search_string)
        self.tv_shows_menu(res.get("searchResultListShow"))
        xbmcplugin.endOfDirectory(self.HANDLE)

    def tv_shows_menu(self, shows: list):
        self.logger.debug("Builds TV Shows Menu")
        for show in shows:
            image_url = show.get("imageUrl", "")

            description = show.get("description")
            if not description:  # sometimes lead contains info
                description = show.get("lead", "")

            url_args = {
                "number_of_episodes": show.get("numberOfEpisodes", 0),
                "tv_show_id": quote_plus(show.get("id")),
            }

            name = show.get("title", "")
            self._add_item_to_directory(
                name,
                self.router.url(mode="list_episodes_by_show", **url_args),
                description,
                video_info={"title": name, "plot": description, "plotoutline": description},
                thumbnailImage=image_url,
                fanart=image_url,
                is_folder=True
            )

    def videos_by_topic(self):
        topics = self.video_client.get_topics(self.bu)["topicList"]

        for topic in topics:
            image_url = topic.get("imageUrl", "")
            name = topic.get("title", "")
            topic_id = topic.get("id", "")
            self._add_item_to_directory(name, self.router.url(mode="list_videos_by_topic", **{"topic_id": topic_id}), thumbnailImage=image_url, is_folder=True)
        xbmcplugin.endOfDirectory(self.HANDLE)

    def list_videos_by_topic(self, topic_id: str, current_page: int, number_of_episodes: int, next_page_id=""):
        number_of_episodes_per_page = int(self.settings.number_of_episodes_per_page)
        res = self.video_client.get_latest_episodes(self.bu, topic_id=topic_id, page_size=number_of_episodes_per_page, next_page_id=next_page_id)

        media_list = res.get("mediaList")
        for media in media_list:
            episode = media.get("episode")
            show = media.get("show")
            self._add_video_to_directory(show, episode, media)

        next_page_url = res.get("next")
        if next_page_url:
            next_page_id = dict(parse_qsl(urlparse(next_page_url).query)).get("next")
            number_of_pages = self._compute_number_of_pages(number_of_episodes_per_page, number_of_episodes)
            next_page = current_page + 1
            liz_name = self.tr(30020).format(current_page, number_of_pages or "?")

            self._add_item_to_directory(
                liz_name,
                self.router.url(
                    mode="list_videos_by_topic",
                    **{"next_page_id": next_page_id, "current_page": current_page + 1, "topic_id": topic_id},
                ),
                label2=str(next_page),
                video_info={"title": liz_name, "plot": str(next_page), "plotoutline": str(next_page)},
                is_folder=True,
            )
        
        xbmcplugin.endOfDirectory(self.HANDLE)

    def list_episodes_by_show(self, tv_show_id: str, current_page: int, number_of_episodes: int, next_page_id=""):
        """Lists the latest episodes of a TV Show
        :param tv_show_id: The id of the TV Show
        :param current_page: Index of the current episodes page
        :param number_of_episodes: Total number of episodes of the show
        :param next_page_id: ID of the next page of episodes
        """
        xbmcplugin.setContent(self.HANDLE, "episodes")

        number_of_episodes_per_page = int(self.settings.number_of_episodes_per_page)
        res = self.video_client.get_latest_episodes(self.bu, tv_show_id, page_size=number_of_episodes_per_page, next_page_id=next_page_id)
        
        show = res.get("show")
        episodes = res.get("episodeList")

        if show and episodes:
            for episode in episodes:
                media = episode.get("mediaList")[0]
                self._add_video_to_directory(show, episode, media)

            next_page_url = res.get("next")
            if next_page_url:
                next_page_id = dict(parse_qsl(urlparse(next_page_url).query)).get("next")
                number_of_pages = self._compute_number_of_pages(number_of_episodes_per_page, number_of_episodes)
                next_page = current_page + 1
                liz_name = self.tr(30020).format(current_page, number_of_pages or "?")

                self._add_item_to_directory(
                    liz_name,
                    self.router.url(
                        mode="list_episodes_by_show", **{"next_page_id": next_page_id, "current_page": next_page, "tv_show_id": quote_plus(show.get("id"))}
                    ),
                    label2=str(next_page),
                    video_info={"title": liz_name, "plot": str(next_page), "plotoutline": str(next_page)},
                    is_folder=True,
                )
        xbmcplugin.endOfDirectory(self.HANDLE)

    def _compute_number_of_pages(self, number_of_episodes_per_page: int, number_of_episodes: int) -> int:
        return int(
            (number_of_episodes_per_page - 1 + number_of_episodes) / number_of_episodes_per_page
        )

    def search_videos(self):
        search_string = xbmcgui.Dialog().input("Search Videos")
        self.logger.info(f"Search string: {search_string}")

        res = self.video_client.search_video(self.bu, search_string)
        self.tv_shows_menu(res.get("searchResultListShow"))
        xbmcplugin.endOfDirectory(self.HANDLE)

    def play_video(self, video_id: str, media_id: str):
        """Plays the selected video
        :param video_id: The video ID
        :param media_id: The media ID
        """
        media_composition = self.video_client.get_media_composition(self.bu, media_id)
        resource = self._get_media_resource(media_composition)
        media_url = self._get_media_url(resource["url"])

        liz = xbmcgui.ListItem(path=media_url)
        liz.setProperty("isPlayable", "true")
        self._set_inputstream_params(liz, resource["protocol"].lower(), resource["mimeType"])
        self._add_subtitles(liz, video_id)
        self.logger.debug(f"Playing episode {self.bu} {media_id} (media URL: {media_url})")
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

    def _get_media_url(self, resource_url: str) -> str:
        """Parses the resource URL and constructs the media URL from it"""
        parsed_url = urlparse(resource_url)
        media_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        # add authentication token for akamaihd
        if "akamaihd" in parsed_url.netloc:
            self.logger.debug("AkamaiHD video")
            token_url = f"http://tp.srgssr.ch/akahd/token?acl={parsed_url.path}"
            response = requests.get(token_url).json()
            token = response["token"]["authparams"]
            media_url += "?" + token
        return media_url

    def _set_inputstream_params(self, listitem, protocol, mimeType):
        """If Inputstream Adaptive is enabled and available, configure it and update the ListItem"""
        is_helper = inputstreamhelper.Helper(protocol)
        if to_bool(self.settings.enable_inputstream_adaptive) and is_helper.check_inputstream():
            listitem.setContentLookup(False)
            listitem.setMimeType(mimeType)
            listitem.setProperty("inputstream", is_helper.inputstream_addon)
            listitem.setProperty("inputstream.adaptive.manifest_type", protocol)

    def _add_subtitles(self, listitem, video_id):
        """If subtitles are enable and available, add them to the ListItem"""
        if to_bool(self.settings.enable_subtitles):
            video_urn = f"urn:{self.bu}:episode:tv:{video_id}"
            resp = self.subs_client.get_subtitles(video_urn)

            subs = []
            for asset in resp["data"]["assets"]:
                if asset is not None:
                    for sub in asset["hasSubtitling"]:
                        subs.append(sub["identifier"])
            if subs:
                self.logger.debug(f"Found subtitles: {subs}")
                listitem.setSubtitles(subs)

    # ================================= Helper methods ==================================

    def _add_video_to_directory(self, show: dict, episode: dict, media: dict):
        url_args = {
            "video_id": episode.get("id"),
            "media_id": media.get("id"),
        }
        
        vid_name = episode.get("title", "") + " - " + media.get("title", "")
        vid_desc = media.get("description", "")
        duration = int(media.get("duration", 0) / 1000 / 60)

        self._add_item_to_directory(
            vid_name,
            self.router.url(mode="play_video", **url_args),
            label2=vid_desc,
            thumbnailImage=episode.get("imageUrl", ""),
            fanart=show.get("imageUrl", ""),
            video_info={"Title": vid_name, "Duration": duration, "Plot": vid_desc, "Aired": episode.get("publishedDate", "")},
            properties={"IsPlayable": "true"},
        )

    def _add_item_to_directory(
        self,
        name: str,
        url: str,
        label2: str = "",
        iconImage: str = "",
        thumbnailImage: str = "",
        poster: dict = None,
        fanart: dict = None,
        video_info: dict = None,
        properties: dict = None,
        subtitles: dict = None,
        is_folder: bool = False,
    ):
        """Helper method that creates a ListItem and adds it to the xbmcplugin Directory"""
        liz = xbmcgui.ListItem(name, label2)
        if properties:
            liz.setProperties(properties)
        if video_info:
            liz.setInfo("video", video_info)
        if poster:
            liz.setArt({"poster": poster})
        if fanart:
            liz.setArt({"fanart": fanart})
        if thumbnailImage:
            liz.setArt({"thumb": thumbnailImage})
        if iconImage:
            liz.setArt({"icon": iconImage})
        if subtitles:
            liz.setSubtitles(subtitles)

        self.logger.info(f"URL = {url}")

        xbmcplugin.addDirectoryItem(
            self.HANDLE,
            url,
            listitem=liz,
            isFolder=is_folder,
        )
