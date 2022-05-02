"""SRGSSR Video API Client"""

from .srgssr_api_client import SRGSSRApiClient


class SRGSSRVideoApiClient(SRGSSRApiClient):
    """Video API client"""

    _VERSION = "v2"
    _API_NAME = "Video"
    _API_URL_NAME = "videometadata"

    @SRGSSRApiClient._renew_access_token
    def get_tv_shows(self, bu: str, character_filter: str = "", only_active_shows: bool = True) -> dict:
        """Fetching the TV Shows list. Can be filtered by the first letter
        :param bu: Business Unit (either 'srf', 'rtr', 'swi', 'rts', 'rsi')
        :param character_filter: First letter of the shows. If not speficied, returns all the shows
        :param only_active_shows: If true, only returns the active shows
        """
        params = {
            "bu": bu,
            "characterFilter": character_filter,
            "pageSize": "unlimited",  # Getting all the shows
            "onlyActiveShows": only_active_shows,
        }
        resp = self._get("tv_shows/alphabetical", params=params)
        return self._returning_func(resp)

    @SRGSSRApiClient._renew_access_token
    def get_topics(self, bu: str) -> dict:
        """Fetching the topics list
        :param bu: Business Unit (either 'srf', 'rtr', 'swi', 'rts', 'rsi')
        """
        params = {"bu": bu}
        resp = self._get("tv_topics", params=params)
        return self._returning_func(resp)

    @SRGSSRApiClient._renew_access_token
    def get_latest_episodes(self, bu: str, tv_show_id: str = "", topic_id: str = "", page_size: int = -1, next_page_id: str = "") -> dict:
        """Getting the latest episodes. Can be filtered by a show or a topic
        :param bu: Business Unit (either 'srf', 'rtr', 'swi', 'rts', 'rsi')
        :param tv_show_id: The id of the show
        :param topic_id: The id of the topic
        :param page_size: The number of episodes to return per page
        :param next_page_id: The encoded reference to the next page
        """
        params = {"bu": bu}
        if page_size > 0 and not next_page_id:
            params.update({"pageSize": page_size})
        if next_page_id:
            params.update({"next": next_page_id})
        
        url = "latest_episodes"
        if tv_show_id:
            url += f"/shows/{tv_show_id}"
        elif topic_id:
            url = f"latest_topics/{topic_id}"

        resp = self._get(url, params=params)
        return self._returning_func(resp)

    @SRGSSRApiClient._renew_access_token
    def get_media_composition(self, bu: str, video_id: str) -> dict:
        """Returns detailed metatdata for a video and information to play it
        :param bu: Business Unit (either 'srf', 'rtr', 'swi', 'rts', 'rsi')
        :param video_id: The id of the video to get info
        """
        params = {"bu": bu}

        resp = self._get(f"{video_id}/mediaComposition", params=params)
        return self._returning_func(resp)
