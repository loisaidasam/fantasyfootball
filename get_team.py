#!/usr/bin/env python

import argparse

from fantasyfootball.espn import ESPNTeam


def main():
    parser = argparse.ArgumentParser(description="Grab/print the team members")
    parser.add_argument('url', type=str, help="")
    args = parser.parse_args()
    params = ESPNTeam.parse_params_from_url(args.url)
    team = ESPNTeam(**params)
    # TODO: Continue working here, having login troubles...
    team.login('email@gmail.com', 'password')
    players = team.get_players()
    print players
    # for player in players:
    #     print player


if __name__ == '__main__':
    main()
