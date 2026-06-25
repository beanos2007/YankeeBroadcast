from fastapi import FastAPI
from datetime import datetime, timezone, timedelta
import os
import requests

app = FastAPI()


def eastern_today() -> str:
    """Today's date as YYYYMMDD in US Eastern time.

    Computed with only the standard library so there is no dependency on the
    OS timezone database (zoneinfo/tzdata) — that avoids any chance of a
    runtime crash on minimal deploy images. Handles the EDT/EST switch:
    US DST runs from the 2nd Sunday of March (07:00 UTC) to the 1st Sunday
    of November (06:00 UTC).
    """
    now = datetime.now(timezone.utc)
    year = now.year

    def nth_sunday(month: int, n: int) -> int:
        first = datetime(year, month, 1, tzinfo=timezone.utc)
        first_sunday = 1 + (6 - first.weekday()) % 7  # weekday(): Mon=0..Sun=6
        return first_sunday + (n - 1) * 7

    dst_start = datetime(year, 3, nth_sunday(3, 2), 7, tzinfo=timezone.utc)
    dst_end = datetime(year, 11, nth_sunday(11, 1), 6, tzinfo=timezone.utc)
    offset = -4 if dst_start <= now < dst_end else -5
    return (now + timedelta(hours=offset)).strftime("%Y%m%d")


@app.get("/game")
def get_game(latitude: float, longitude: float):
    # Ask ESPN for *today's* games explicitly. Without a date parameter the
    # scoreboard can return a stale/previous day's slate, which made the app
    # show an old matchup (e.g. the Tigers instead of today's opponent).
    response = requests.get(
        "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
        params={"dates": eastern_today()},
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


if __name__ == "__main__":
    # Lets the app start with `python main.py`. Reads Railway's $PORT but
    # falls back to 8000 if it is unset/empty, so a missing PORT can never
    # crash startup (the "--port requires an argument" loop).
    import uvicorn

    port = int(os.environ.get("PORT") or 8000)
    uvicorn.run(app, host="0.0.0.0", port=port)
