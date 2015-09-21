
import json
import logging
import re

from bs4 import BeautifulSoup
import requests

from fantasyfootball.base_team import BaseTeam

LOGIN_URL_GET = 'http://games.espn.go.com/frontpage/football'
LOGIN_URL_POST = 'https://registerdisney.go.com/jgc/v2/client/ESPN-FANTASYLM-PROD/guest/login?langPref=en-US'
TEAM_URL_TEMPLATE = 'http://games.espn.go.com/ffl/clubhouse?leagueId=%s&teamId=%s&seasonId=%s'


logger = logging.getLogger(__name__)


class InvalidPlayerIdError(Exception):
    pass


class ESPNTeam(BaseTeam):
    def __init__(self, league_id, team_id, season_id):
        self.league_id = league_id
        self.team_id = team_id
        self.season_id = season_id
        self.session = requests.Session()

    def login(self, email, password):
        self.session.get(LOGIN_URL_GET)
        payload = {'loginValue': email, 'password': password}
        headers = {'Content-type': 'application/json;charset=UTF-8'}
        response = self.session.post(LOGIN_URL_POST,
                                     data=json.dumps(payload),
                                     headers=headers)
        if response.status_code != 200:
            raise Exception("Login failed!")
        return response

    @staticmethod
    def parse_params_from_url(url):
        match = re.match(r"http://games\.espn\.go\.com/ffl/clubhouse\?leagueId=(\d+)\&teamId=(\d+)\&seasonId=(\d+)",
                         url)
        if not match:
            raise Exception("Invalid URL")
        return {
            'league_id': match.group(1),
            'team_id': match.group(2),
            'season_id': match.group(3),
        }

    def get_players(self):
        """Method for getting players on your team

        In the JS console as of 2013-08-29:
        document.getElementsByClassName("pncPlayerRow")[0].getElementsByClassName("playertablePlayerName")[0].getElementsByTagName("a")[0].text
        """
        url = TEAM_URL_TEMPLATE % (self.league_id,
                                   self.team_id,
                                   self.season_id)
        response = self.session.get(url)
        return response.content
        # soup = BeautifulSoup(response.content, "lxml")
        # players = []
        # for player_row in soup.find_all("tr", "pncPlayerRow"):
        #     player_col = player_row.find("td", "playertablePlayerName")

        #     # Their name:
        #     # player = player_col.find("a").string

        #     # Their id, used by holy cow API
        #     player_id = player_col['id']
        #     matches = re.match(r"playername_(\d+)", player_id)
        #     if not matches:
        #         raise InvalidPlayerIdError("id=%s" % player_id)
        #     actual_id = matches.group(1)
        #     try:
        #         player = self.api.athlete(actual_id)
        #     except holycow.ApiRequestError:
        #         logger.warning("Unable to grab athlete with id=%s from holycow API", actual_id)
        #         full_name = player_col.find("a").string
        #         raw_data = {
        #             'id': actual_id,
        #             'full_name': full_name,
        #         }
        #         player = holycow.athlete.Athlete(raw_data)
        #     players.append(player)
        # return players
