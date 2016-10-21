#!/usr/bin/env python

import csv
import json
import sys


def parse_teams_generator(teams):
    for team in teams:
        yield team['children'][0]['text']


def parse_team_players_generator(team, team_players):
    position = None
    for player_num, player in enumerate(team_players, start=1):
        # print "player_num %s" % player_num
        # print player
        position = player['children'][0].get('children', [{}])[0].get('text') or position
        name = player['children'][1]['children'][0]['text']
        rank = player['children'][1]['text']
        if '.' in rank:
            rank = rank.split('.')[0]
        data = (team, name, position, rank)
        # print data
        yield data


def parse_json(data):
    results = []
    data = data['children'][0]
    data_teams = data['children'][0]['children']
    teams = list(parse_teams_generator(data_teams))
    # print "Teams: %s" % teams
    data_teams_players = data['children'][1]['children']
    for team, data_team_players in zip(teams, data_teams_players):
        # children[0].children[0].children
        data_team_players = data_team_players['children'][0]['children'][0]['children']
        generator = parse_team_players_generator(team, data_team_players)
        results += list(generator)
    return results


def main():
    if len(sys.argv) < 2:
        print "Usage: ./depth_chart_json_to_csv.py <filename.json>"
        exit(1)
    filename = sys.argv[1]
    with open(filename, 'r') as fp:
        data = json.load(fp)
    player_data = parse_json(data)
    filename_csv = '%s.csv' % filename
    with open(filename_csv, 'w') as fp:
        writer = csv.writer(fp)
        for row in player_data:
            writer.writerow(row)
            # print row


if __name__ == '__main__':
    main()
