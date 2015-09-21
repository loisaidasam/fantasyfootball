
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

    def login(self, email, password):
        # TODO: Work out login
        self.session.get(LOGIN_URL_GET)
        payload = {'loginValue': email, 'password': password}
        headers = {'Content-type': 'application/json;charset=UTF-8'}
        response = self.session.post(LOGIN_URL_POST,
                                     data=json.dumps(payload),
                                     headers=headers)
        if response.status_code != 200:
            raise Exception("Login failed!")
        return response

    def set_cookie(self, cookie):
        # For now, using this cookie method
        self.cookie = cookie

    def get_players(self):
        """Method for getting players on your team

        In the JS console as of 2013-08-29:
        document.getElementsByClassName("pncPlayerRow")[0].getElementsByClassName("playertablePlayerName")[0].getElementsByTagName("a")[0].text
        """
        url = TEAM_URL_TEMPLATE % (self.league_id,
                                   self.team_id,
                                   self.season_id)
        response = self.session.get(url, headers={'Cookie': self.cookie})
        soup = BeautifulSoup(response.content, "lxml")
        players = []
        for player_row in soup.find_all('tr', "pncPlayerRow"):
            player_cols = player_row.find_all('td')
            if not all([player_cols, player_cols[0], player_cols[1]]):
                continue
            # Their name:
            pos = player_cols[0].text
            name_anchor = player_cols[1].find('a')
            name = name_anchor and name_anchor.text
            players.append({
                'name': name,
                'pos': pos,
            })
        return players
