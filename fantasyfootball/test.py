
import unittest

from espn import ESPNFantasyFootballTeam
import settings


class TestBasic(unittest.TestCase):

    def test_espn(self):
        team = ESPNFantasyFootballTeam(settings.ESPN_API_KEY,
                                       settings.LEAGUE_ID,
                                       settings.TEAM_ID,
                                       settings.SEASON_ID)
        self.assertGreater(len(team.players), 1)


if __name__ == '__main__':
    unittest.main()
