"""SRGSSR Subtitles API Client"""

from .srgssr_api_client import SRGSSRApiClient

class SRGSSRSubtitlesApiClient(SRGSSRApiClient):
    """Subtitles API client"""

    @SRGSSRApiClient.renew_access_token
    def get_tv_shows(self, character_filter: str):
        """Fetching the TV Shows list filtered by their first letter
        :param character_filter: First letter of the shows
        """
        params = {
            "characterFilter": character_filter,
            "pageSize": "unlimited",    # Getting all the shows
        }
        resp = self._get("", params=params)
        return self._returning_func(resp)


        