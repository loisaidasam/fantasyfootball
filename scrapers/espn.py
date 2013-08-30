
from bs4 import BeautifulSoup
import requests


url = 'http://games.espn.go.com/ffl/clubhouse?leagueId=1209473&teamId=3&seasonId=2013'
resp = requests.get(url)

soup = BeautifulSoup(resp.content, "lxml")

# JS
# document.getElementsByClassName("pncPlayerRow")[0].getElementsByClassName("playertablePlayerName")[0].getElementsByTagName("a")[0].text

for player_row in soup.find_all("tr", "pncPlayerRow"):
    player_col = player_row.find("td", "playertablePlayerName")
    player = player_col.find("a")
    print player.string
