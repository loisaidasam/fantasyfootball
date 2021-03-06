
import json
import logging
import re

from bs4 import BeautifulSoup
import requests
from unidecode import unidecode

from fantasyfootball.base_team import BaseTeam

LOGIN_URL_GET = 'http://games.espn.com/frontpage/football'
LOGIN_URL_POST = 'https://registerdisney.go.com/jgc/v2/client/ESPN-FANTASYLM-PROD/guest/login?langPref=en-US'
TEAM_URL_TEMPLATE = 'http://games.espn.com/ffl/clubhouse?leagueId=%s&teamId=%s&seasonId=%s'
URL_TEMPLATE_PLAYERS = 'http://games.espn.com/ffl/playertable/prebuilt/freeagency?leagueId=%s&teamId=%s&seasonId=%s&avail=-1&context=freeagency&view=overview&startIndex=%s'
URL_TEMPLATE_SCOREBOARD = 'http://games.espn.com/ffl/scoreboard?leagueId=%s&seasonId=%s'

# PARSER = 'lxml'
PARSER = 'html5lib'

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
        return BeautifulSoup(response.content, PARSER)

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
        result = {}
        # For rambunxious team names...
        owner = unidecode(player_cols[2].text)
        result['owner'] = owner
        assert len(player_cols) >= 17
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
        url = URL_TEMPLATE_PLAYERS % (self.league_id,
                                      self.team_id,
                                      self.season_id,
                                      offset)
        logger.info("URL: %s", url)
        response = self.session.get(url, headers={'Cookie': self.cookie})
        return BeautifulSoup(response.content, PARSER)

    def get_header_row(self, player):
        KEYS_DESIRED = "name,team,pos,status,owner,opp,home_away,status_et,prk,pts,avg,last,proj,oprk,pct_st,pct_own,plus_minus".split(',')
        logger.info("Getting header row based on %s desired keys: %s",
                    len(KEYS_DESIRED),
                    KEYS_DESIRED)
        keys_actual = player.keys()
        header_row = []
        # Fill up all the keys we want first
        for key in KEYS_DESIRED:
            if key not in keys_actual:
                logger.warning("Missing header row key! %s", key)
                continue
            header_row.append(key)
        # Then fill in unknown/new ones
        for key in keys_actual:
            if key in header_row:
                # Cool
                continue
            logger.info("Unknown/new header row key! %s", key)
            header_row.append(key)
        logger.info("Got header row w/ %s keys", len(header_row))
        return header_row

    def players_generator(self, max_num_requests=None):
        logger.info("players_generator()")
        offset = num_requests = 0
        players_seen = set()
        while True:
            if max_num_requests and num_requests >= max_num_requests:
                logger.info("Hit max_num_requests of %s", max_num_requests)
                return
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
                    continue
                try:
                    player_info_advanced = self._parse_player_info_advanced(player_cols)
                except:
                    logger.exception("Error parsing advanced player info. player_cols: %s /// player_row: %s",
                                     player_cols,
                                     player_row)
                    continue
                player.update(player_info_advanced)
                player_hash = (player['name'], player['team'])
                if player_hash in players_seen:
                    logger.warning("We already saw %s !", player_hash)
                    return
                yield player
                players_seen.add(player_hash)
                players_this_time += 1
            logger.info("Offset: %s, got %s players", offset, players_this_time)
            # if players_this_time < 50:
            #     logger.info("Only got %s players (less than 50) - all done here",
            #                 players_this_time)
            #     return
            if not players_this_time:
                logger.info("Didn't get any players! All done here")
                return
            offset += 50

    def get_players(self, max_num_requests=None):
        logger.info("get_players()")
        return list(self.players_generator(max_num_requests))

    def get_scoreboard(self):
        soup = self._get_scoreboard_soup_piece()
        matchups = soup.find_all(class_='matchup')
        results = []
        for matchup in matchups:
            names = [name.find('a').text for name in matchup.find_all(class_='name')]
            assert len(names) == 2
            scores = [score.text for score in matchup.find_all(class_='score')]
            assert len(scores) == 2
            records = [record.text for record in matchup.find_all(class_='record')]
            assert len(records) == 2
            owners = [owner.text for owner in matchup.find_all(class_='owners')]
            assert len(owners) == 2
            details = matchup.find(class_='scoringDetails')
            labels = self._get_details_labels(details)
            matchup_teams_data = details.find_all(class_='playersPlayed')
            assert len(matchup_teams_data) == 2
            team1 = self._get_matchup_team_data(names[0],
                                                scores[0],
                                                records[0],
                                                owners[0],
                                                labels,
                                                matchup_teams_data[0])
            team2 = self._get_matchup_team_data(names[1],
                                                scores[1],
                                                records[1],
                                                owners[1],
                                                labels,
                                                matchup_teams_data[1])
            result = [team1, team2]
            results.append(result)
        return results

    def _get_scoreboard_soup_piece(self):
        logger.info("Grabbing scoreboard soup piece")
        url = URL_TEMPLATE_SCOREBOARD % (self.league_id, self.season_id)
        logger.info("URL: %s", url)
        response = self.session.get(url, headers={'Cookie': self.cookie})
        return BeautifulSoup(response.content, PARSER)

    def _get_details_labels(self, details):
        labels_divs = details.find(class_='labels').find_all('div')
        return [self._get_label_div_title(div) for div in labels_divs]

    def _get_label_div_title(self, div):
        title = div.get('title')
        if title:
            return title
        title = div.text
        if title.endswith(':'):
            return title[:-1]
        return title

    def _get_matchup_team_data(self, name, score, record, owner, labels,
                               team_data):
        result = {
            'name': name,
            'score': score,
            'record': record,
            'owner': owner,
            'data': {},
        }
        divs = team_data.find_all('div')
        assert len(labels) == len(divs)
        for label, div in zip(labels, divs):
            result['data'][label] = div.text
        return result
