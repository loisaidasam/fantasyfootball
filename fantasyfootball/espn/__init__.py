
import json
import logging
import re

from bs4 import BeautifulSoup
import requests

from fantasyfootball.base_team import BaseTeam

LOGIN_URL_GET = 'http://games.espn.com/frontpage/football'
LOGIN_URL_POST = 'https://registerdisney.go.com/jgc/v2/client/ESPN-FANTASYLM-PROD/guest/login?langPref=en-US'
TEAM_URL_TEMPLATE = 'http://games.espn.com/ffl/clubhouse?leagueId=%s&teamId=%s&seasonId=%s'
PLAYERS_URL_TEMPLATE = 'http://games.espn.com/ffl/playertable/prebuilt/freeagency?leagueId=%s&teamId=%s&seasonId=%s&&context=freeagency&view=overview&startIndex=%s'


logger = logging.getLogger(__name__)


class InvalidPlayerIdError(Exception):
    pass


class ESPNTeam(BaseTeam):
    PLAYER_INFO_ADV_OPP_BYE = '** BYE **'

    def __init__(self, league_id, team_id, season_id):
        self.league_id = league_id
        self.team_id = team_id
        self.season_id = season_id
        self.session = requests.Session()

    @staticmethod
    def parse_params_from_url(url):
        match = re.match(r"http://games\.espn\.com/ffl/(clubhouse|freeagency)\?leagueId=(\d+)\&teamId=(\d+)\&seasonId=(\d+)",
                         url)
        if not match:
            raise Exception("Invalid URL")
        return {
            'league_id': match.group(2),
            'team_id': match.group(3),
            'season_id': match.group(4),
        }

    def login(self, email, password):
        # TODO: Work out login - for now relying on cookies method
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

    def _get_team_soup(self):
        """Helpful for debugging
        """
        url = TEAM_URL_TEMPLATE % (self.league_id,
                                   self.team_id,
                                   self.season_id)
        response = self.session.get(url, headers={'Cookie': self.cookie})
        return BeautifulSoup(response.content, "lxml")

    def _parse_player_info_basic(self, player_info_str):
        """http://stackoverflow.com/questions/4995116/only-extracting-text-from-this-element-not-its-children/4995480#4995480
        print col.find(text=True, recursive=False)
        """
        if ',' in player_info_str:
            # Player
            # Ex: `Ryan Fitzpatrick, NYJ QB`
            name, remainder = player_info_str.split(', ', 1)
            pieces = remainder.split()
            team = pieces[0]
            pos = pieces[1]
            status = len(pieces) > 2 and pieces[2] or u"OK"
            return {
                'name': name,
                'team': team,
                'pos': pos,
                'status': status,
            }
        # D/ST
        # Ex: `Browns D/ST D/ST`
        name1, name2, pos = player_info_str.split()
        return {
            'name': u" ".join([name1, name2]),
            # TODO: Fill in team
            # (Player has team listed next to their name like: `NYJ` but D/ST
            # have full team name listed like: `Browns`)
            'team': None,
            'pos': pos,
            'status': u"OK",
        }

    def _parse_player_info_advanced(self, player_cols):
        result = {'status': player_cols[2].text}
        opp = player_cols[5].text
        if '@' in opp:
            result['opp'] = opp[1:]
            result['home_away'] = 'AWAY'
        else:
            result['opp'] = opp
            result['home_away'] = 'HOME'
        index_adj = 0
        if result['opp'] == ESPNTeam.PLAYER_INFO_ADV_OPP_BYE:
            result['opp'] = 'BYE'
            result['status_et'] = None
            index_adj = -1
        else:
            result['status_et'] = player_cols[6].text
        result.update({
            'prk': player_cols[8 + index_adj].text,
            'pts': player_cols[9 + index_adj].text,
            'avg': player_cols[10 + index_adj].text,
            'last': player_cols[11 + index_adj].text,
            'proj': player_cols[13 + index_adj].text,
            'oprk': player_cols[14 + index_adj].text,
            'pct_st': player_cols[15 + index_adj].text,
            'pct_own': player_cols[16 + index_adj].text,
            'plus_minus': player_cols[17 + index_adj].text,
        })
        return result

    def get_team(self):
        """Method for getting players on your team
        """
        logger.info("get_team()")
        soup = self._get_team_soup()
        players = []
        player_rows = soup.find_all('tr', "pncPlayerRow")
        for player_num, player_row in enumerate(player_rows, start=1):
            logger.info("Grabbing player %s of %s ...",
                        player_num,
                        len(player_rows))
            player_cols = player_row.find_all('td')
            if not player_cols:
                continue
            player_info = player_cols[1].text
            player_info = player_info and player_info.strip()
            if not player_info:
                continue
            slot = player_cols[0] and player_cols[0].text
            player = self._parse_player_info_basic(player_info)
            player.update({
                'slot': slot,
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
            players.append(player)
        return players

    def _get_players_soup_piece(self, offset=0):
        logger.info("Grabbing player soup piece at offset %s", offset)
        url = PLAYERS_URL_TEMPLATE % (self.league_id,
                                      self.team_id,
                                      self.season_id,
                                      offset)
        logger.info("URL: %s", url)
        response = self.session.get(url, headers={'Cookie': self.cookie})
        return BeautifulSoup(response.content, "lxml")

    def get_players(self, max_num_requests=None):
        logger.info("get_players()")
        offset = num_requests = 0
        players = []
        players_seen = set()
        while True:
            if max_num_requests and num_requests >= max_num_requests:
                logger.info("Hit max_num_requests of %s", max_num_requests)
                break
            players_this_time = 0
            soup = self._get_players_soup_piece(offset)
            num_requests += 1
            player_rows = soup.find_all('tr', "pncPlayerRow")
            for player_num, player_row in enumerate(player_rows, start=1):
                logger.info("Grabbing player %s of %s ...",
                            player_num,
                            len(player_rows))
                player_cols = player_row.find_all('td')
                if not player_cols:
                    continue
                player_info = player_cols[0].text
                player_info = player_info and player_info.strip()
                if not player_info:
                    continue
                try:
                    player = self._parse_player_info_basic(player_info)
                except:
                    logger.exception("Error parsing player_info: %s",
                                     player_info)
                    raise
                try:
                    player_info_advanced = self._parse_player_info_advanced(player_cols)
                except:
                    logger.exception("Error parsing advanced player info. player_cols: %s /// player_row: %s",
                                     player_cols,
                                     player_row)
                    raise
                player.update(player_info_advanced)
                players.append(player)
                player_hash = (player['name'], player['team'])
                if player_hash in players_seen:
                    logger.warning("We already saw %s !", player_hash)
                    return players
                players_seen.add(player_hash)
                players_this_time += 1
            logger.info("Offset: %s, got %s players", offset, players_this_time)
            if players_this_time < 50:
                logger.info("Finishing up")
                break
            offset += 50
        return players
