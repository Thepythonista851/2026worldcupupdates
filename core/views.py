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
            d = datetime.datetime.strptime(m['local_date'], "%m/%d/%Y %H:%M").date()
            if (d - today).days >= -1 and (d - today).days <= 4:   # Yesterday to next 4 days
                filtered.append(m)
        except:
            filtered.append(m)
    
    return render(request, "home.html", {"matches": filtered[:15]})

def about(request):
    return render(request, "about.html")