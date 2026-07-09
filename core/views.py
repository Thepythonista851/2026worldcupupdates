from django.shortcuts import render
import requests
from django.core.cache import cache
import datetime

COUNTRY_FLAGS = {
    "Nigeria": "ng", "Morocco": "ma", "Senegal": "sn", "Egypt": "eg",
    "Algeria": "dz", "Cameroon": "cm", "Tunisia": "tn", "Ghana": "gh",
    "South Africa": "za", "Ivory Coast": "ci", "Argentina": "ar",
    "Brazil": "br", "France": "fr", "England": "gb", "Spain": "es",
    "Germany": "de", "USA": "us", "Mexico": "mx", "Canada": "ca",
}

def home(request):
    data = cache.get('worldcup_matches')

    if not data:
        try:
            response = requests.get("https://worldcup26.ir/get/games", timeout=12)
            data = response.json() if response.status_code == 200 else {"games": []}
        except:
            data = {"games": []}

        cache.set('worldcup_matches', data, 60)

    matches = data.get("games", [])
    today = datetime.date.today()
    filtered = []

    for m in matches:
        try:
            d = datetime.datetime.strptime(
                m['local_date'], "%m/%d/%Y %H:%M"
            ).date()

            if -1 <= (d - today).days <= 4:
                filtered.append(m)
        except:
            filtered.append(m)

    live_games = []
    upcoming_games = []
    finished_games = []

    for m in filtered:
        m['home_flag'] = COUNTRY_FLAGS.get(m.get('home_team_name_en'), 'un')
        m['away_flag'] = COUNTRY_FLAGS.get(m.get('away_team_name_en'), 'un')

        status = m.get("time_elapsed")
        if status and status not in ["notstarted", "finished"]:
            live_games.append(m)
        elif status == "notstarted":
            upcoming_games.append(m)
        else:
            finished_games.append(m)

    sorted_matches = live_games + upcoming_games + finished_games

    return render(
        request,
        "home.html",
        {
            "matches": sorted_matches[:15]
        }
    )

def about(request):
    return render(request, "about.html")