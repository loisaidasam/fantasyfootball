
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

    def _get_players_soup(self):
        """Helpful for debugging
        """
        url = TEAM_URL_TEMPLATE % (self.league_id,
                                   self.team_id,
                                   self.season_id)
        response = self.session.get(url, headers={'Cookie': self.cookie})
        return BeautifulSoup(response.content, "lxml")

    def get_players(self):
        """Method for getting players on your team
        """
        soup = self._get_players_soup()
        players = []
        for player_row in soup.find_all('tr', "pncPlayerRow"):
            player_cols = player_row.find_all('td')
            if not player_cols:
                continue
            player_info = player_cols[1].text
            player_info = player_info and player_info.strip()
            if not player_info:
                continue
            slot = player_cols[0] and player_cols[0].text
            if ',' in player_info:
                # Player
                name, remainder = player_info.split(', ')
                pieces = remainder.split()
                team = pieces[0]
                pos = pieces[1]
                status = len(pieces) > 2 and pieces[2] or u"OK"
            else:
                # DST
                name1, name2, _ = player_info.split()
                name = u" ".join([name1, name2])
                status = u"OK"
            players.append({
                'name': name,
                'pos': pos,
                'team': team,
                'slot': slot,
                'status': status,
                'opp': player_cols[4].text,
                'status_et': player_cols[5].text,
                'prk': player_cols[7].text,
                'pts': player_cols[8].text,
                'avg': player_cols[9].text,
                'last': player_cols[10].text,
                'proj': player_cols[12].text,
                'oprk': player_cols[13].text,
                'pct_st': player_cols[14].text,
                'pct_own': player_cols[15].text,
                'plus_minus': player_cols[16].text,
            })
        return players
