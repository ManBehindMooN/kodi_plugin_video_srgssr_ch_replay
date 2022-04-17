"""SRGSSR Video API Client"""

from requests import Response
from .srgssr_api_client import SRGSSRApiClient

class SRGSSRVideoApiClient(SRGSSRApiClient):
    """Video API client"""

    _VERSION = "v2"
    _API_NAME = "Video"
    _API_URL_NAME = "videometadata"

    @SRGSSRApiClient._renew_access_token
    def get_tv_shows(self, bu: str, character_filter: str, only_active_shows: bool = True):
        """Fetching the TV Shows list filtered by their first letter
        :param bu: Business Unit (either 'srf', 'rtr', 'swi', 'rts', 'rsi')
        :param character_filter: First letter of the shows
        :param only_active_shows: If true, only returns the active shows
        """
        params = {
            "bu": bu,
            "characterFilter": character_filter,
            "pageSize": "unlimited",    # Getting all the shows
            "onlyActiveShows": only_active_shows,
        }
        resp = self._get("tv_shows/alphabetical", params=params)
        return self._returning_func(resp)

    @SRGSSRApiClient._renew_access_token
    def get_latest_episodes(self, bu: str, tvshow_id: str, page_size: int = -1, next_page_id: str = ""):
        """Getting the latest episodes of a show
        :param bu: Business Unit (either 'srf', 'rtr', 'swi', 'rts', 'rsi')
        :param tvshow_id: The id of the show
        :param page_size: The number of episodes to return per page
        :param next_page_id: The encoded reference to the next page
        """
        params = {"bu": bu}
        if page_size > 0 and not next_page_id:
            params.update({"pageSize": page_size})
        if next_page_id:
            params.update({"next": next_page_id})
        
        resp = self._get(f"latest_episodes/shows/{tvshow_id}", params=params)
        return self._returning_func(resp)

    @SRGSSRApiClient._renew_access_token
    def get_media_composition(self, bu: str, video_id: str):
        """Returns detailed metatdata for a video and information to play it
        :param bu: Business Unit (either 'srf', 'rtr', 'swi', 'rts', 'rsi')
        :param video_id: The id of the video to get info
        """
        params = {"bu": bu}

        resp = self._get(f"{video_id}/mediaComposition", params=params)
        return self._returning_func(resp)
