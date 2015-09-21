#!/usr/bin/env python

import argparse

from fantasyfootball.espn import ESPNTeam


def main():
    parser = argparse.ArgumentParser(description="Grab/print the team members")
    parser.add_argument('url', type=str, help="")
    args = parser.parse_args()
    params = ESPNTeam.parse_params_from_url(args.url)
    team = ESPNTeam(**params)
    team.set_cookie('YOUR_COOKIE_HERE')
    players = team.get_players()
    # print players
    for i, player in enumerate(players, start=1):
        print "%d.\t%s" % (i, player)


if __name__ == '__main__':
    main()
