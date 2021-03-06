"""Take a folder of date-ordered CSVs and aggregate them into one big CSV
ordered by player and then CSV
"""

import csv
import glob
import json
import logging
import os.path
import sys

import csv_position_reader
from tqdm import tqdm


logger = logging.getLogger('')
logger.setLevel(logging.INFO)
logger.handlers = []
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s (%(process)d): %(message)s',
                              '%Y-%m-%d %H:%M:%S')
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class MissingAllPlayersError(Exception):
    pass


def get_csv_files(dir_name):
    files = sorted(glob.glob(os.path.join(dir_name, '*.csv')))
    num_files = len(files)
    files = filter(lambda file: os.path.getsize(file), files)
    if len(files) < num_files:
        logger.warning("Filtered out `%s` of `%s` empty files",
                       num_files - len(files),
                       num_files)
    return files


def get_filename_player_position_cache(csv_file):
    return '%s-player-position-cache.json' % csv_file


def get_player_str_cache(player):
    return '|'.join(player)


def lookup_unique_players(csv_files, write_cache=True):
    logger.info("Getting unique players ...")
    players = set()
    for csv_file in tqdm(csv_files):
        with open(csv_file, 'r') as fp:
            reader = csv_position_reader.DictReader(fp)
            player_position_cache = {}
            for position, row in reader:
                name = row['name'].replace('*', '')
                player = (name, row['team'], row['pos'])
                players.add(player)
                player_str_cache = get_player_str_cache(player)
                player_position_cache[player_str_cache] = position
        if write_cache:
            filename = get_filename_player_position_cache(csv_file)
            with open(filename, 'w') as fp:
                json.dump(player_position_cache, fp)
    logging.info("Found `%s` players", len(players))
    return sorted(players)


def get_unique_players(dir_name_basename, csv_files):
    filename_players_cache = '%s.players-cache.json' % dir_name_basename
    try:
        with open(filename_players_cache, 'r') as fp:
            players = json.load(fp)
        logger.info("Using players cache `%s`", filename_players_cache)
        return players
    except:
        pass
    logger.warning("Unable to load players cache `%s`, building it now ...",
                   filename_players_cache)
    players = lookup_unique_players(csv_files)
    with open(filename_players_cache, 'w') as fp:
        json.dump(players, fp)
    return players


def get_player_str(player):
    name, team, pos = player
    return "%s, %s %s" % (name, team, pos)


class PlayerValueLookup(object):
    player_position_cache = None

    def __init__(self, csv_file):
        self.fp = open(csv_file, 'r')
        self.reader = csv_position_reader.DictReader(self.fp)
        self.reader.set_header()
        self.load_player_position_cache(csv_file)

    def load_player_position_cache(self, csv_file):
        try:
            filename = get_filename_player_position_cache(csv_file)
            with open(filename, 'r') as fp:
                self.player_position_cache = json.load(fp)
        except KeyboardInterrupt:
            raise
        except:
            logger.warning("Error loading player_position_cache for csv `%s`",
                           csv_file)

    def close(self):
        self.fp.close()

    def get_player_row_brute_force(self, player):
        self.fp.seek(0)
        reader = csv.DictReader(self.fp)
        name, team, pos = player
        for row in reader:
            if row['name'].replace('*', '') != name:
                continue
            if row['team'] != team:
                continue
            if row['pos'] != pos:
                continue
            return row
        return None

    def get_player_row(self, player):
        if self.player_position_cache:
            player_str_cache = get_player_str_cache(player)
            if player_str_cache in self.player_position_cache:
                position = self.player_position_cache[player_str_cache]
                self.reader.seek(position)
                position, row = self.reader.next()
                return row
            logger.debug("Player not in player_position_cache: %s",
                         player)
            # TODO: If the cache exists and the player isn't in it do we
            # fallback to brute force or just return ''?
            return None
        return self.get_player_row_brute_force(player)

    def get_player_row_value(self, player, column):
        row = self.get_player_row(player)
        return row and row[column] or ''


def get_csv_row_for_column(players, csv_file, column):
    row = [os.path.basename(csv_file)]
    num_players_missing = 0
    lookup = PlayerValueLookup(csv_file)
    for player in players:
        value = lookup.get_player_row_value(player, column)
        if not value:
            logger.debug("Missing player `%s` for csv file `%s`",
                         player,
                         csv_file)
            num_players_missing += 1
        row.append(value)
    lookup.close()
    if num_players_missing:
        logger.info("Missing `%s` of `%s` players for csv file `%s`",
                    num_players_missing,
                    len(players),
                    csv_file)
        if num_players_missing == len(players):
            # Optimization, don't write this row
            raise MissingAllPlayersError("Missing all players for csv_file!")
    return row


def aggregate_for_column(dir_name, column):
    logger.info("Aggregating data from dir `%s` / column `%s` ...",
                dir_name,
                column)
    csv_files = get_csv_files(dir_name)
    logger.info("Got `%s` CSV files", len(csv_files))
    dir_name_basename = os.path.basename(dir_name)
    players = get_unique_players(dir_name_basename, csv_files)
    filename = '%s-players-all-%s.csv' % (dir_name_basename, column)
    logger.info("Writing to `%s`", filename)
    with open(filename, 'w') as fp:
        writer = csv.writer(fp)
        row_header = ['filename'] + map(get_player_str, players)
        writer.writerow(row_header)
        logger.info("Writing CSV files ...")
        for csv_file in tqdm(csv_files):
            try:
                row = get_csv_row_for_column(players, csv_file, column)
            except KeyboardInterrupt:
                raise
            except MissingAllPlayersError:
                continue
            except:
                logger.exception("Error getting CSV row for filename `%s`",
                                 csv_file)
                continue
            writer.writerow(row)


def aggregate(dir_name):
    logger.info("Aggregating data from dir `%s` ...", dir_name)
    csv_files = get_csv_files(dir_name)
    logger.info("Got `%s` CSV files", len(csv_files))
    dir_name_basename = os.path.basename(dir_name)
    players = get_unique_players(dir_name_basename, csv_files)
    filename = '%s-players-all.csv' % dir_name_basename
    logger.info("Writing to `%s`", filename)
    with open(filename, 'w') as fp:
        writer = csv.writer(fp)
        row_header = ['player', 'filename']
        row_header_attrs = None
        for player in tqdm(players):
            player_str = get_player_str(player)
            for csv_file in csv_files:
                try:
                    lookup = PlayerValueLookup(csv_file)
                    csv_row = lookup.get_player_row(player)
                    lookup.close()
                except KeyboardInterrupt:
                    raise
                except:
                    logger.exception("Error getting CSV row for filename `%s`",
                                     csv_file)
                    continue
                if not csv_row:
                    continue
                if not row_header_attrs:
                    row_header_attrs = csv_row.keys()
                    writer.writerow(row_header + row_header_attrs)
                row = [player_str, csv_file]
                for key in row_header_attrs:
                    value = csv_row.get(key) or ''
                    if value == '--':
                        value = ''
                    row.append(value)
                writer.writerow(row)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        logger.error("Missing dir name")
        sys.exit(1)
    dir_name = sys.argv[1]
    aggregate(dir_name)
