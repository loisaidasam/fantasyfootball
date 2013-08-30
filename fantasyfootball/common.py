

class FantasyFootballTeam(object):

    def _get_players(self):
        raise NotImplementedError("To be implemented by subclasses")

    @property
    def players(self):
        if not getattr(self, '_players', None):
            self._players = self._get_players()
        return self._players

