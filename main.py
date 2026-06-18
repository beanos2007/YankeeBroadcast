from fastapi import FastAPI
import requests as requests
app = FastAPI()

@app.get("/game")

def get_game(latitude: float, longitude: float):

    response = requests.get("https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard")

    data = response.json()

    for games in data["events"]:
    
    
    
        market_away = []
    
        market_home = []

        market_national = []
        
        competitors = games["competitions"][0]["competitors"]
        away_team = competitors[1]["team"]["displayName"]
        home_team = competitors[0]["team"]["displayName"] 
    
        tv_broadcasts = games["competitions"][0]["broadcasts"]
        if "New York Yankees" not in [home_team, away_team ]:
            continue
        coordinate_response = requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json", headers={"User-Agent": "YankeeBroadcastApp"})

        data = coordinate_response.json()
        zip_code = data["address"]["postcode"]

        zipcode_response = requests.get(f"https://content.mlb.com/data/blackouts/{zip_code}.json")

        blackouts = zipcode_response.json()
        
        for broadcast in tv_broadcasts:
        
            
            if broadcast["market"] == "away":
                market_away.append(broadcast["names"][0])
            
            if broadcast["market"] == "home":
                market_home.append(broadcast["names"][0])
            if broadcast["market"] == "national":
                market_national.extend(broadcast["names"])
        
        if "NYY" in blackouts["teams"]  and "MLB.TV" in market_national:
                market_national.remove("MLB.TV")  
        return {
            "away_team": away_team,
            "home_team": home_team,
            "away_broadcasts": market_away,
            "home_broadcasts": market_home,
            "national_broadcasts": market_national
        }
    return {"latitude": latitude, "longitude": longitude}
