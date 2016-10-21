#!/usr/bin/env python

import argparse
import csv
import datetime
import logging
import os

from fantasyfootball.espn import ESPNTeam

import settings


BASE_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

LOGGING_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILENAME = os.path.join(LOGGING_DIR, 'export.log')

DATA_DIR = os.path.join(BASE_DIR, 'data')


logger = logging.getLogger('')
logger.setLevel(logging.INFO)
logger.handlers = []
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s (%(process)d): %(message)s',
                              '%Y-%m-%d %H:%M:%S')
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
file_handler = logging.FileHandler(LOG_FILENAME)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def write_data(filename, players):
    with open(filename, 'w') as fp:
        writer = csv.writer(fp)
        for i, player in enumerate(players):
            if i == 0:
                header_row = player.keys()
                writer.writerow(header_row)
            row = []
            for key in header_row:
                row.append(player.get(key))
            writer.writerow(row)
    logger.info("Wrote %s players to %s", len(players), filename)


def main():
    # parser = argparse.ArgumentParser(description="Grab/print the team members")
    # parser.add_argument('url', type=str, help="")
    # args = parser.parse_args()
    # params = ESPNTeam.parse_params_from_url(args.url)
    # settings.ESPN_URL is something like this:
    # url = "http://games.espn.com/ffl/freeagency?leagueId=<YOUR_LEAGUE_ID>&teamId=<YOUR_TEAM_ID>&seasonId=<THIS_YEAR>"
    url = settings.ESPN_URL
    params = ESPNTeam.parse_params_from_url(url)
    team = ESPNTeam(**params)
    # To get `settings.ESPN_COOKIE`, in a browser (tested w/ Chrome), open the
    # JS console and click the "Network" tab. Limit the requests to only "XHR"
    # requests. Now open your ESPN Fantasy League page and click the "Players"
    # tab. A ton of resources will probably load - wait until they've all loaded
    # and then clear them all. At the bottom of the players list, click "Next",
    # and you'll see the one resource that loads - THIS is the one you want.
    # Right click and choose "Copy as cURL". Paste the result somewhere and nab
    # the part that says "-H 'Cookie: FFL_LM_COOKIE= ...". This is what you are
    # looking for.
    team.set_cookie(settings.ESPN_COOKIE)

    # print players
    # for i, player in enumerate(players, start=1):
    #     print "%d.\t%s" % (i, player)
    # write_data('data/my_team.csv', team.get_team())

    # In [3]: datetime.datetime.now().isoformat().split('.')[0][:-3].replace('T', '-').replace(':', '-')
    # Out[3]: '2016-09-12-17-24'
    date_str = datetime.datetime.now().isoformat().split('.')[0][:-3].replace('T', '-').replace(':', '-')
    basename = 'players-%s.csv' % date_str
    filename = os.path.join(DATA_DIR, basename)
    write_data(filename, team.get_players())


if __name__ == '__main__':
    main()