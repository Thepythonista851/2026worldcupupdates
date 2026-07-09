from django.shortcuts import render
import requests
from django.core.cache import cache
import datetime


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


    # 🔥 PUT LIVE GAMES FIRST
    live_games = []
    upcoming_games = []
    finished_games = []

    for m in filtered:
        status = m.get("time_elapsed")

        if status and status not in ["notstarted", "finished"]:
            live_games.append(m)

        elif status == "notstarted":
            upcoming_games.append(m)

        else:
            finished_games.append(m)


    # Live → Upcoming → Finished
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