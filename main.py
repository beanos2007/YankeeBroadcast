from fastapi import FastAPI
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

app = FastAPI()


@app.get("/game")
def get_game(latitude: float, longitude: float):
    # Ask ESPN for *today's* games explicitly. Without a date parameter the
    # scoreboard can return a stale/previous day's slate, which made the app
    # show an old matchup (e.g. the Tigers instead of today's opponent).
    # MLB schedules by U.S. Eastern date, so anchor "today" to that.
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d")
    response = requests.get(
        "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
        params={"dates": today},
    )
    data = response.json()

    for game in data["events"]:
        competitors = game["competitions"][0]["competitors"]
        away_team = competitors[1]["team"]["displayName"]
        home_team = competitors[0]["team"]["displayName"]
        tv_broadcasts = game["competitions"][0]["broadcasts"]

        if "New York Yankees" not in [home_team, away_team]:
            continue

        market_away = []
        market_home = []
        market_national = []

        for broadcast in tv_broadcasts:
            if broadcast["market"] == "away":
                market_away.append(broadcast["names"][0])
            if broadcast["market"] == "home":
                market_home.append(broadcast["names"][0])
            if broadcast["market"] == "national":
                market_national.extend(broadcast["names"])

        # Reverse-geocode the user's location to a ZIP for the blackout lookup.
        # Use a separate variable so we don't clobber the scoreboard `data`.
        geo = requests.get(
            f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json",
            headers={"User-Agent": "YankeeBroadcastApp"},
        ).json()
        zip_code = geo.get("address", {}).get("postcode")

        # Some coordinates (open water, remote areas) have no ZIP — treat those
        # as "not blacked out" instead of crashing with a 500.
        is_blacked_out = False
        if zip_code:
            blackouts = requests.get(
                f"https://content.mlb.com/data/blackouts/{zip_code}.json"
            ).json()
            is_blacked_out = "NYY" in blackouts.get("teams", [])
            if is_blacked_out and "MLB.TV" in market_national:
                market_national.remove("MLB.TV")

        return {
            "away_team": away_team,
            "home_team": home_team,
            "away_broadcasts": market_away,
            "home_broadcasts": market_home,
            "national_broadcasts": market_national,
            "is_blacked_out": is_blacked_out,
        }
