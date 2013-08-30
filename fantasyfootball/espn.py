
import logging
import re

from bs4 import BeautifulSoup
import requests
import holycow

from common import FantasyFootballTeam


TEAM_URL_TEMPLATE = "http://games.espn.go.com/ffl/clubhouse?leagueId=%s&teamId=%s&seasonId=%s"

logger = logging.getLogger(__name__)


class InvalidPlayerIdError(Exception):
    pass


class ESPNFantasyFootballTeam(FantasyFootballTeam):
    def __init__(self, api_key, league_id, team_id, season_id):
        self.api_key = api_key
        self.league_id = league_id
        self.team_id = team_id
        self.season_id = season_id
        
    @property
    def api(self):
        if not getattr(self, '_api', None):
            self._api = holycow.Api(self.api_key,
                                    holycow.Api.RESOURCE_SPORTS_FOOTBALL_NFL)
        return self._api

    def _get_players(self):
        """Method for getting players on your team

        In the JS console as of 2013-08-29:
        document.getElementsByClassName("pncPlayerRow")[0].getElementsByClassName("playertablePlayerName")[0].getElementsByTagName("a")[0].text
        """
        url = TEAM_URL_TEMPLATE % (self.league_id,
                                   self.team_id,
                                   self.season_id)
        resp = requests.get(url)
        soup = BeautifulSoup(resp.content, "lxml")
        players = []
        for player_row in soup.find_all("tr", "pncPlayerRow"):
            player_col = player_row.find("td", "playertablePlayerName")

            # Their name:
            # player = player_col.find("a").string

            # Their id, used by holy cow API
            player_id = player_col['id']
            matches = re.match(r"playername_(\d+)", player_id)
            if not matches:
                raise InvalidPlayerIdError("id=%s" % player_id)
            actual_id = matches.group(1)
            try:
                player = self.api.athlete(actual_id)
            except holycow.ApiRequestError:
                logger.warning("Unable to grab athlete with id=%s from holycow API", actual_id)
                full_name = player_col.find("a").string
                raw_data = {
                    'id': actual_id,
                    'full_name': full_name,
                }
                player = holycow.athlete.Athlete(raw_data)
            players.append(player)
        return players
