from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time

# launches a Chrome browser and goes to list of team stats for tournaments

driver = webdriver.Chrome()
url = "https://gol.gg/teams/list/season-S15/split-ALL/tournament-ALL/"
driver.get(url)

# select the top checkbox to filter for only major regions
checkbox = driver.find_element(By.ID, "leagues_top")
checkbox.click()

# clicks the refresh button to reload table with filter applied
refresh_button = driver.find_element(By.ID,"btn_refresh")
refresh_button.click() 

# waits until table is present avoids stale element reference
WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table_list tbody tr")))


# swap to beautifulsoup 
soup = BeautifulSoup(driver.page_source, "html.parser")
driver.quit()

# find <tr> rows since these store the stats
table = soup.find("table", class_="table_list")
rows = table.find("tbody").find_all("tr")

# initialize headers
headers = ["Name", "Season", "Region", "Games", "WinRate", "KDA", "GPM", "GDM", "GameDuration","KillsPerGame", "DeathsPerGame", "TowersKilled", "TowersLost", "FB%", "FT%", "FOS%",
           "DRAPG", "DRA%", "VGPG", "HER%", "ATAKHAN%", "DRA@15", "TD@15", "GD@15", "PPG", "NASHPG", "NASH%", "CSM", "DPM", "WPM", "VWPM", "WCPM"]

# extract data
data = []
for row in rows:
    cols = row.find_all("td")
    row_data = [col.text.strip() for col in cols]
    data.append(row_data)


df = pd.DataFrame(data, columns=headers)
df.to_csv("team_stats_s15.csv", index=False)
