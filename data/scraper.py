from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
import time
import random
import pandas as pd
import os
import re

class StatsScraper:
    def __init__(self, csv_path = "combined_match_stats.csv", id_path = "game_ids.txt"):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
        self.all_data = []
        self.csv_path = csv_path
        # column names on csv file
        self.columns = ["GameID", "Team", "Result", "Game Time", "Side" ,"Patch", "Tournament", "Date", "Region", "Champion", "Player", "Role", "Level", "Kills", "Deaths", "Assists", "KDA",
            "CS", "CS in Team's Jungle", "CS in Enemy Jungle", "CSM", "Golds", "GPM", "GOLD%", "Vision Score", "Wards placed", "Wards destroyed", "Control Wards Purchased",
            "Detector Wards Placed", "VSPM", "WPM", "VWPM", "WCPM", "VS%", "Total damage to Champion", "Physical Damage", "Magic Damage", "True Damage", "DPM", "DMG%", "K+A Per Minute", "KP%",
            "Solo kills", "Double kills", "Triple kills", "Quadra kills", "Penta kills", "GD@15", "CSD@15", "XPD@15", "LVLD@15", "Objectives Stolen", "Damage dealt to turrets",
            "Damage dealt to buildings", "Total heal", "Total Heals On Teammates", "Damage self mitigated", "Total Damage Shielded On Teammates", "Time ccing others",
            "Total Time CC Dealt", "Total damage taken", "Total Time Spent Dead", "Consumables purchased", "Items Purchased", "Shutdown bounty collected", "Shutdown bounty lost"
        ]
        self.id_path = id_path
        self.scraped_game_ids = self._load_saved_game_ids()
        self._ensure_csv_headers()
    
    # loads previously scraped game ids to avoid duplicates
    def _load_saved_game_ids(self) -> set[int]:
        if not os.path.exists(self.id_path):
            return set()
        with open(self.id_path, "r") as f:
            return set(int(line.strip()) for line in f if line.strip().isdigit())
    
    # creates csv file with headers if it doesn't exist     
    def _ensure_csv_headers(self):
        if not os.path.exists(self.csv_path):
            pd.DataFrame(columns=self.columns).to_csv(self.csv_path, index = False)

    # scrapes the website for specific stats and then adds to a dictionary
    def scrape_game(self, game_id: int):
        # skips if game is already scraped
        if game_id in self.scraped_game_ids:
            print(f"Skipping game {game_id}, already scraped.")
            return 
        
        # get stats from the team
        team_stats = self.get_team_stats(game_id)

        #get individual stats
        link = f"https://gol.gg/game/stats/{game_id}/page-fullstats/"
        response = requests.get(link, headers = self.headers)
        soup = BeautifulSoup(response.text,"html.parser")

        table = soup.find("table")
        if not table:
            return
        
        # extract champion names from <thead>
        thead = table.find("thead")
        champions = []
        if thead:
            # skip first <th> since it is a label
            ths = thead.find_all("th")[1:]  
            for th in ths:
                img = th.find("img")
                if img and img.has_attr("alt"):
                    champ_name = img["alt"]
                    if champ_name == "K":
                        champ_name = "Ksante"
                    elif champ_name == "Cho":
                        champ_name = "Chogath"
                    elif champ_name == "Kai":
                        champ_name = "Kaisa"
                    if champ_name == "Rek":
                        champ_name = "Reksai"
                    champions.append(champ_name)
        
        rows = table.find_all("tr")[1:]

        data_per_champ = {}
        
        # sets first 5 champions to Blue since blue side is the one scraped first 
        for i in range(len(champions)):
            if i < 5:
                side = "Blue"
            else:
                side = "Red"
            if side == "Blue":
                team = team_stats["BlueTeam"]
                result = team_stats["BlueResult"]
            else:
                team = team_stats["RedTeam"]
                result = team_stats["RedResult"]
            
            data_per_champ[i] = { "GameID": game_id, "Team": team, "Result": result, "Game Time": team_stats.get("Game Time", ""), "Side": side, "Patch":team_stats.get("Patch", ""),
                                  "Tournament": team_stats.get("Tournament", ""), "Date": team_stats.get("Date", ""), "Region": team_stats.get("Region", ""), "Champion": champions[i] 
                                  }

        # gets <td> cells from <tr> rows
        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue
            # gets the stat label name
            stat_name = cells[0].get_text(strip=True)
            # skips first label cell 
            for i, cell in enumerate(cells[1:]):
                data_per_champ[i][stat_name] = cell.get_text(strip=True)
        self.all_data.extend(data_per_champ.values())

        self.scraped_game_ids.add(game_id)
        with open(self.id_path, "a") as f:
            f.write(str(game_id) + "\n")
    
    # saves data to csv
    def save(self):
        if not self.all_data:
            print("No data to save.")
            return

        df = pd.DataFrame(self.all_data)

        # ensure all columns exist in the right order
        for col in self.columns:
            if col not in df.columns:
                df[col] = ""

        df = df[self.columns]
        df.to_csv(self.csv_path, mode="a", index=False, header=False)

        self.all_data.clear()
    
    # scrapes team stats (not available on the stats for individuals)
    def get_team_stats(self, game_id:int) -> dict:
        link = f"https://gol.gg/game/stats/{game_id}/page-game/"
        response = requests.get(link, headers = self.headers)
        soup = BeautifulSoup(response.text, "html.parser")

        # initialize dictionary for team level stats
        team_stats = {"BlueTeam": "", "RedTeam": "", "BlueResult": "", "RedResult": "", "Game Time": "", "Side": "", "Patch": "", "Tournament": "", "Date": "", "Region": ""}
        
        # extracts game time
        time_div = soup.find("div", class_= "col-6 text-center")
        if time_div:
            h1 = time_div.find("h1")
            if h1:
                team_stats["Game Time"] = h1.get_text(strip = True)

        # extracts patch version
        patch_div = soup.find("div", class_= "col-3 text-right")
        if patch_div:
            team_stats["Patch"] = patch_div.get_text(strip = True)
        
        # extracts date string in YYYY-MM-DD format
        date_div = soup.find("div", class_= "col-12 col-sm-5 text-right")
        if date_div:
            date_text = date_div.get_text(strip = True)
            match = match = re.search(r"\d{4}-\d{2}-\d{2}", date_text)
            if match:
                team_stats["Date"] = match.group(0)

        # extracts tournament name and region
        tournament_div = soup.find("div", class_="col-12 col-sm-7")
        if tournament_div:
            a_tag = tournament_div.find("a")
            if a_tag:
                team_stats["Tournament"] = a_tag.get_text(strip = True)
                full_text = tournament_div.get_text(strip=True)
                match = re.search(r"\(([^)]+)\)", full_text)
                if match:
                    team_stats["Region"] = match.group(1)

        # extracts blue side team name and results             
        blue_div = soup.find("div", class_="col-12 blue-line-header")
        if blue_div:
            a_tag = blue_div.find("a")
            if a_tag:
                team_stats["BlueTeam"] = a_tag.get_text(strip = True)
            if "-" in blue_div.text:
                team_stats["BlueResult"] = blue_div.text.split("-")[-1].strip()
        
        #extracts red side team name and results
        red_div = soup.find("div", class_="col-12 red-line-header")
        if red_div:
            a_tag = red_div.find("a")
            if a_tag:
                team_stats["RedTeam"] = a_tag.get_text(strip = True)
            if "-" in red_div.text:
                team_stats["RedResult"] = red_div.text.split("-")[-1].strip()
            
        return team_stats

        
    
def get_matchlist_links() -> list[str]:
    # launches a Chrome browser and goes to list of tournaments 
    driver = webdriver.Chrome()
    driver.get("https://gol.gg/tournament/list/")

    # select the top checkbox to filter for only major regions
    checkbox = driver.find_element(By.ID, "leagues_top")
    checkbox.click()


    # clicks the refresh button to reload table with filter applied
    refresh_button = driver.find_element(By.ID,"btn_refresh")
    refresh_button.click() 

    # waits until table is present avoids stale element reference
    WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table_list.footable.toggle-square-filled a")))

    # get the links from the table
    links = driver.find_elements(By.CSS_SELECTOR, "table.table_list.footable.toggle-square-filled a")
    tournament_links = []

    # gets each individual tournament's matchlist from major regions
    for link in links:
        href = link.get_attribute("href")
        if href is not None:
            # converts stats page to matchlist url
            href = href.replace("tournament-stats", "tournament-matchlist")
            tournament_links.append(href)
    
    driver.quit()
    return tournament_links

def get_games_links(tournament_link: str) -> list[str]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    response = requests.get(tournament_link, headers = headers)
    
    
    soup = BeautifulSoup(response.text,"html.parser")
    table = soup.select_one('table.table_list.footable.toggle-square-filled')
    games_links = []
    if not table:
        return []
    
    # extracts all relevant game links
    for a_tag in table.find_all("a"):
        href = a_tag.get("href")
        if href and (href.endswith("/page-game/") or href.endswith("/page-summary/")):
            if href.endswith("/page-game/"):
                href = href.replace("/page-game/", "/page-summary/")
            games_links.append(href)
    return games_links

    # extracts unique game ids from a list of links
def get_game_id(links: list[str]) -> list[int]:
    base_url = "https://gol.gg"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    game_ids = []
    for link in links:
        # get the game id from the link using regex
        match = re.search(r"/game/stats/(\d+)", link)
        if not match:
            continue
        game_ids.append(int(match.group(1)))
        base_game_id = int(match.group(1))

        # checks to see if there is more than just game 1 in the page (looks for game 2/3/4/5 and appends)
        full_url = f"{base_url}{link.lstrip('..')}"
        response = requests.get(full_url, headers=headers)
        soup = BeautifulSoup(response.text,"html.parser")
        nav = soup.find("div", id = "gameMenuToggler")
        if nav:
            for a_tag in nav.find_all("a", class_= "nav-link"):
                href = a_tag.get("href","")
                match = re.search(r"/game/stats/(\d+)/page-game", href)
                if match:
                    game_id = int(match.group(1))
                    if game_id != base_game_id:
                        game_ids.append(game_id)

    return sorted(game_ids)

def main():
    links = get_matchlist_links()[::-1]
    games_links = []
    link = links[-1]
    # iterate through all the links to get all the game links
    #for link in links:
    games_links.extend(get_games_links(link))
    # sleep for random duration to avoid overloading server
    time.sleep(random.uniform(1, 3))
        
    scraper = StatsScraper()
    ids = get_game_id(games_links)
    batch_size = 10
    for i, id in enumerate(ids,1):
        scraper.scrape_game(id)
        # only save onto csv file every 10 games
        if i % batch_size == 0:
            scraper.save()
        # sleep for random duration to avoid overloading server
        time.sleep(random.uniform(1, 3))

    # save remaining games onto csv file
    scraper.save()


if __name__ == "__main__":
    main()
    
