"""Routing in the plugin menus"""

import os.path
from urllib.parse import urlencode

import xbmcplugin

class Router:

    def __init__(self, plugin):
        self.plugin = plugin

    def url(self, bu: str ="", mode: str ="", **kwargs):
        """Constructs the plugin's URL"""
        if not bu:
            bu = self.plugin.bu
        path = f"{bu}/{mode}"
        return f"{self.plugin.ADDON_URL}/{path}?{urlencode(kwargs)}"

    def dispatch(self, path: str, **kwargs):
        """Dispatch to the plugin menu
        :param path: url path
        :param kwargs: url params
        """
        self.plugin.logger.debug(f"Route dispatcher: path={path}, kwargs: {kwargs}")
        if self._bu(path):
            self.plugin.bu = self._bu(path)
        mode = self._mode(path)
        self.plugin.logger.debug(f"Mode: {mode}, BU:{self.plugin.bu}")

        if not self.plugin.bu:
            self.plugin.bu_menu()
        else:
            xbmcplugin.setPluginCategory(self.plugin.HANDLE, self.plugin.bu.upper())

            if not mode:
                self.plugin.main_menu()
            elif mode == "all_shows":
                self.plugin.all_tv_shows()
            elif mode == "shows_by_letters":
                letter = kwargs.get("letter", "")
                self.plugin.tv_shows_by_letter(letter)
            elif mode == "videos_by_topic":
                self.plugin.videos_by_topic()
            elif mode == "list_videos_by_topic":
                self.plugin.list_videos_by_topic(
                    kwargs["topic_id"],
                    int(kwargs.get("current_page", 0)),
                    int(kwargs.get("number_of_episodes", 0)),
                    kwargs.get("next_page_id", ""),
                )
            elif mode == "search_tv_shows":
                self.plugin.search_tv_shows()
            elif mode == "search_videos":
                self.plugin.search_videos()
            elif mode == "list_episodes_by_show":
                self.plugin.list_episodes_by_show(
                    kwargs["tv_show_id"],
                    int(kwargs.get("current_page", 0)),
                    int(kwargs.get("number_of_episodes", 0)),
                    kwargs.get("next_page_id", ""),
                )
            elif mode == "play_video":
                video_id = kwargs.get("video_id", "")
                media_id = kwargs.get("media_id", "")
                self.plugin.play_video(video_id, media_id)

    def _bu(self, path: str):
        """Gets the channel from the path"""
        return path.split("/")[1]
    
    def _mode(self, path: str):
        """Gets the mode (choosed submenu) from the path"""
        parts = path.split("/")
        return parts[2] if len(parts) >= 3 else ""