"""Take a folder of date-ordered CSVs and aggregate them into one big CSV with
players in the header row and the dates as subsequent rows
"""

import csv
import glob
import json
import logging
import os.path
import sys

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


def get_csv_row_from_line(line, *args, **kwargs):
    return csv.reader([line], *args, **kwargs).next()


class PositionDictReader(object):
    """Return successive pairs of file position, dict

    Need to implement our own CSV reader, as the default one uses a read-ahead
    cache on the file pointer, making `fp.tell()` yield inaccurate results.

    https://stackoverflow.com/questions/14145082/file-tell-inconsistency/14145118#14145118
    https://stackoverflow.com/questions/19151/build-a-basic-python-iterator/24377#24377
    https://stackoverflow.com/questions/12109622/how-to-know-the-byte-position-of-a-row-of-a-csv-file-in-python/12110160#12110160
    """
    def __init__(self, fp, *args, **kwargs):
        self.fp = fp
        self.line_iterator = iter(self.fp.readline, '')
        self.header = None
        self.args = args
        self.kwargs = kwargs

    def __iter__(self):
        return self

    def get_next_row(self):
        line = self.line_iterator.next()
        return get_csv_row_from_line(line, *self.args, **self.kwargs)

    def set_header(self):
        self.fp.seek(0)
        self.header = self.get_next_row()

    def get_next_row_dict(self):
        row = self.get_next_row()
        return dict(zip(self.header, row))

    def next(self):
        if not self.header:
            self.set_header()
        position = self.fp.tell()
        row_dict = self.get_next_row_dict()
        return position, row_dict

    def seek(self, position):
        self.fp.seek(position)


def get_player_str_cache(player):
    return '|'.join(player)


def get_unique_players(csv_files, write_cache=True):
    logger.info("Getting unique players ...")
    players = set()
    for csv_file in tqdm(csv_files):
        with open(csv_file, 'r') as fp:
            reader = PositionDictReader(fp)
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


def get_player_str(player):
    name, team, pos = player
    return "%s, %s %s" % (name, team, pos)


class PlayerValueLookup(object):
    player_position_cache = None

    def __init__(self, csv_file):
        self.fp = open(csv_file, 'r')
        self.reader = PositionDictReader(self.fp)
        self.reader.set_header()
        self.load_player_position_cache(csv_file)

    def load_player_position_cache(self, csv_file):
        try:
            filename = get_filename_player_position_cache(csv_file)
            with open(filename, 'r') as fp:
                self.player_position_cache = json.load(fp)
        except:
            logger.warning("Error loading player_position_cache for csv `%s`",
                           csv_file)

    def close(self):
        self.fp.close()

    def get_player_row_value_brute_force(self, player, column):
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
            if row[column] == '--':
                return ''
            return row[column]
        return ''

    def get_player_row_value(self, player, column):
        if self.player_position_cache:
            player_str_cache = get_player_str_cache(player)
            if player_str_cache in self.player_position_cache:
                position = self.player_position_cache[player_str_cache]
                self.reader.seek(position)
                row = self.reader.get_next_row_dict()
                if row[column] == '--':
                    return ''
                return row[column]
            logger.debug("Player not in player_position_cache: %s",
                         player)
            # TODO: If the cache exists and the player isn't in it do we
            # fallback to brute force or just return ''?
            return ''
        return self.get_player_row_value_brute_force(player, column)


def get_csv_row(players, csv_file, column):
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


def aggregate(dir_name, column):
    logger.info("Aggregating data from dir `%s` / column `%s` ...",
                dir_name,
                column)
    csv_files = get_csv_files(dir_name)
    logger.info("Got `%s` CSV files", len(csv_files))
    dir_name_basename = os.path.basename(dir_name)
    filename_players_cache = '%s.players-cache.json' % dir_name_basename
    try:
        with open(filename_players_cache, 'r') as fp:
            players = json.load(fp)
        logger.info("Using players cache `%s`", filename_players_cache)
    except:
        logger.warning("Unable to load players cache `%s`, building it now ...",
                       filename_players_cache)
        players = get_unique_players(csv_files)
        with open(filename_players_cache, 'w') as fp:
            json.dump(players, fp)
    filename = '%s-players-all-%s.csv' % (dir_name_basename, column)
    logger.info("Writing to `%s`", filename)
    with open(filename, 'w') as fp:
        writer = csv.writer(fp)
        row_header = ['filename'] + map(get_player_str, players)
        writer.writerow(row_header)
        logger.info("Writing CSV files ...")
        for csv_file in tqdm(csv_files):
            try:
                row = get_csv_row(players, csv_file, column)
            except KeyboardInterrupt:
                raise
            except MissingAllPlayersError:
                continue
            except:
                logger.exception("Error getting CSV row for filename `%s`",
                                 csv_file)
                continue
            writer.writerow(row)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        logger.error("Missing dir name / column ('proj' or 'last')")
        sys.exit(1)
    dir_name = sys.argv[1]
    column = sys.argv[2]
    aggregate(dir_name, column)
