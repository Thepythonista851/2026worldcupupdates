from django.shortcuts import render
import requests
from django.core.cache import cache
import datetime
from zoneinfo import ZoneInfo

COUNTRY_FLAGS = {
    "Nigeria": "ng", "Morocco": "ma", "Senegal": "sn", "Egypt": "eg",
    "Algeria": "dz", "Cameroon": "cm", "Tunisia": "tn", "Ghana": "gh",
    "South Africa": "za", "Ivory Coast": "ci", "Argentina": "ar",
    "Brazil": "br", "France": "fr", "England": "gb", "Spain": "es",
    "Germany": "de", "USA": "us", "Mexico": "mx", "Canada": "ca",
}

# Maps a city (as returned by the API's city_en field) to its IANA timezone.
# This is what lets us correctly convert each match's LOCAL stadium kickoff
# time into a true UTC timestamp, instead of wrongly assuming it's already UTC.
CITY_TIMEZONES = {
    "East Rutherford": "America/New_York",      # MetLife Stadium
    "Philadelphia": "America/New_York",         # Lincoln Financial Field
    "Boston": "America/New_York",               # Gillette Stadium
    "Miami": "America/New_York",                # Hard Rock Stadium
    "Atlanta": "America/New_York",              # Mercedes-Benz Stadium
    "Dallas": "America/Chicago",                # AT&T Stadium
    "Houston": "America/Chicago",               # NRG Stadium
    "Kansas City": "America/Chicago",           # Arrowhead Stadium
    "Los Angeles": "America/Los_Angeles",       # SoFi Stadium
    "San Francisco": "America/Los_Angeles",     # Levi's Stadium
    "Seattle": "America/Los_Angeles",           # Lumen Field
    "Mexico City": "America/Mexico_City",       # Estadio Azteca
    "Guadalajara": "America/Mexico_City",       # Estadio Akron
    "Monterrey": "America/Monterrey",           # Estadio BBVA
    "Toronto": "America/Toronto",               # BMO Field
    "Vancouver": "America/Vancouver",           # BC Place
}

DEFAULT_TZ = "UTC"


def _match_city_to_tz(city_en):
    """Find the timezone for a stadium's city, matching loosely on substring
    since the API may return 'East Rutherford, NJ' etc."""
    if not city_en:
        return DEFAULT_TZ
    for city_key, tz in CITY_TIMEZONES.items():
        if city_key.lower() in city_en.lower():
            return tz
    return DEFAULT_TZ


def _get_stadium_timezones():
    """Fetch (and cache) the stadium list, building stadium_id -> timezone."""
    mapping = cache.get('stadium_timezones')
    if mapping:
        return mapping

    mapping = {}
    try:
        response = requests.get("https://worldcup26.ir/get/stadiums", timeout=12)
        if response.status_code == 200:
            stadiums = response.json()
            # API may return a list directly or wrapped in a key; handle both.
            if isinstance(stadiums, dict):
                stadiums = stadiums.get("stadiums", [])
            for s in stadiums:
                sid = str(s.get("id"))
                mapping[sid] = _match_city_to_tz(s.get("city_en"))
    except Exception:
        mapping = {}

    # Cache for a long time — stadium/timezone assignments don't change.
    cache.set('stadium_timezones', mapping, 60 * 60 * 24)
    return mapping


def _to_utc_iso(local_date_str, stadium_id, stadium_timezones):
    """Convert 'MM/DD/YYYY HH:MM' stadium-local time into a true UTC ISO string."""
    try:
        naive = datetime.datetime.strptime(local_date_str, "%m/%d/%Y %H:%M")
        tz_name = stadium_timezones.get(str(stadium_id), DEFAULT_TZ)
        localized = naive.replace(tzinfo=ZoneInfo(tz_name))
        utc_dt = localized.astimezone(ZoneInfo("UTC"))
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def home(request):
    data = cache.get('worldcup_matches')
    if not data:
        try:
            response = requests.get("https://worldcup26.ir/get/games", timeout=12)
            data = response.json() if response.status_code == 200 else {"games": []}
        except:
            data = {"games": []}
        cache.set('worldcup_matches', data, 60)

    stadium_timezones = _get_stadium_timezones()

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

        # Correctly converted, true UTC kickoff time - the browser can now
        # safely convert this to the viewer's local time with new Date().
        m['kickoff_utc'] = _to_utc_iso(
            m.get('local_date'), m.get('stadium_id'), stadium_timezones
        )

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