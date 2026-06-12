
import requests as requests

response = requests.get("https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard")

data = response.json()

for games in data["events"]:
    
    
    
    
    
   
    market_away = []
    
    market_home = []
   
    competitors = games["competitions"][0]["competitors"]
    away_team = competitors[1]["team"]["displayName"]
    home_team = competitors[0]["team"]["displayName"] 
    
    tv_broadcasts = games["competitions"][0]["broadcasts"]
    if "New York Yankees" not in [home_team, away_team ]:
        continue
    
    for broadcast in tv_broadcasts:
        
        
        if broadcast["market"] == "away":
            market_away.append(broadcast["names"][0])
            
        if broadcast["market"] == "home":
            market_home.append(broadcast["names"][0])
        
        
                   
    print(f" The {away_team} broadcast is {market_away} The {home_team} broadcast is {market_home}")
   
            
