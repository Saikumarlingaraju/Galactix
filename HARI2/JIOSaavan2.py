import json
import ctypes
import time
import random
import requests
import urllib.parse
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ---------------------------------------------------------
# CONFIGURATION & MAPPING
# ---------------------------------------------------------
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_VOLUME_UP = 0xAF

COMMAND_MAP = {
    "Push": ("Play / Pause", VK_MEDIA_PLAY_PAUSE),
    "Left": ("Previous Track", VK_MEDIA_PREV_TRACK),
    "Right": ("Next Track", VK_MEDIA_NEXT_TRACK),
    "Neutral": ("Volume Up", VK_VOLUME_UP),     
    "Lift": ("Return to Home", "HOME_MACRO"),   
    "Pull": ("Search Album/Playlist", "MACRO") 
}

SEARCH_TARGETS = [
    {
        "query": "Telugu"
    },
    {
        "query": "Telugu Songs"
    },
    {
        "query": "Telugu Hits"
    }
]

INITIAL_PLAYLISTS = [
    "https://www.jiosaavn.com/featured/hindi-hit-songs/ZodsPn39CSjwxP8tCU-flw__",
    "https://www.jiosaavn.com/featured/taaza-tunes/Me5RridRfDk_"
]

CONFIDENCE_THRESHOLD = 0.5

# ---------------------------------------------------------
# EDGE DETECTOR (State Machine to prevent spam)
# ---------------------------------------------------------
class BCISignalFilter:
    def __init__(self):
        # Changed baseline so Neutral can be evaluated as a real command
        self.previous_command = "START" 
        self.last_volume_time = 0.0  
        
    def process(self, current_timestamp, current_command):
        # If the command is repeating (e.g., continuous Neutral or Drop)
        if current_command == self.previous_command:
            # Apply the 3-second cooldown to our new volume commands
            if current_command in ["Neutral", "Drop"]: 
                if (current_timestamp - self.last_volume_time) >= 3.0:
                    self.last_volume_time = current_timestamp
                    return True 
            return False # Ignore spam
            
        # If it's a completely new command
        self.previous_command = current_command
        if current_command in ["Neutral", "Drop"]:
            self.last_volume_time = current_timestamp
            
        return True

bci_filter = BCISignalFilter()

def xpath_literal(value):
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'

    parts = value.split("'")
    return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"

# ---------------------------------------------------------
# EDGE WEBDRIVER SETUP & QUEUE PRE-LOADING
# ---------------------------------------------------------
print("Booting up the Edge WebDriver...")
edge_options = Options()
edge_options.add_argument("--start-maximized")
edge_options.add_argument("--autoplay-policy=no-user-gesture-required")

driver = webdriver.Edge(options=edge_options)

# PRE-CACHE THE QUEUE
initial_playlist = random.choice(INITIAL_PLAYLISTS)
print("Injecting initial playlist to pre-pack the queue...")
driver.get(initial_playlist)

try:
    play_btn = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".js-play-button"))
    )
    time.sleep(2.0) 
    driver.execute_script("arguments[0].click();", play_btn)
    
    print("Queue populated! Giving the internet 5 seconds to buffer the music...")
    time.sleep(5.0) 
    
except Exception as e:
    print(f"[Warning] Could not auto-start the initial playlist: {e}")

print("-" * 50)

# ---------------------------------------------------------
# HARDWARE CONTROL & MACROS
# ---------------------------------------------------------
def press_vk(vk):
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

def visual_search_macro():
    """Hybrid approach: Slower visual typing, Enter key simulation, and guaranteed multi-track queues."""
    target = random.choice(SEARCH_TARGETS)
    search_term = target["query"]
    print(f"   -> [Phase 1: Visual] Searching for: '{search_term}'")
    
    # 1. THE VISUAL ILLUSION (Typing via ActionChains)
    try:
        print("   -> [Selenium] Hunting for search UI...")
        
        search_selectors = [
            (By.CSS_SELECTOR, "input[placeholder*='Search']"),
            (By.CSS_SELECTOR, "input[placeholder*='search']"),
            (By.CSS_SELECTOR, "input[type='search']"),
            (By.CSS_SELECTOR, "input[type='text']"), 
            (By.ID, "searchBox"),
            (By.CSS_SELECTOR, ".rbt-input-main"),
            (By.XPATH, "//input[contains(@class, 'search')]")
        ]
        
        search_box = None
        for by_type, selector in search_selectors:
            try:
                search_box = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                if search_box and search_box.is_displayed():
                    break
            except Exception:
                continue
                
        if search_box is None:
            raise TimeoutException("Search input field vanished from active page DOM structure.")
            
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_box)
        time.sleep(0.2)

        actions = ActionChains(driver)
        actions.move_to_element(search_box).click().perform()
        time.sleep(0.2)
        
        actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
        time.sleep(0.2)

        print("   -> [Selenium] Typing query at human speed...")
        for char in search_term:
            actions.send_keys(char).perform()
            time.sleep(0.2) # SLOWED DOWN: Was 0.05, now 0.2 seconds per character
            
        time.sleep(0.4)
        
        print("   -> [Selenium] Hitting ENTER for visual feedback...")
        actions.send_keys(Keys.RETURN).perform()
        
        # Let the user watch the search results load for a moment before the API jump
        time.sleep(1.5) 
        
    except Exception as e:
        print(f"   -> [Warning] Visual UI interaction bypassed: {e}")

    # 2. THE INTERNAL PATH (API Bypass - Multi-Track Enforcement)
    print("   -> [Phase 2: Internal] Fetching multi-track queue via JioSaavn API...")
    try:
        encoded_query = urllib.parse.quote(search_term)
        api_url = f"https://www.jiosaavn.com/api.php?__call=autocomplete.get&query={encoded_query}&_format=json&_marker=0&ctx=web6dot0"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"API returned status code: {response.status_code}")
            
        data = response.json()
        
        # Force the selection of Playlists or Albums to ensure multiple songs.
        # We completely ignore the 'songs' array so it never plays a single track.
        valid_targets = []
        
        if 'playlists' in data and isinstance(data['playlists']['data'], list):
            valid_targets.extend(data['playlists']['data'])
            
        if 'albums' in data and isinstance(data['albums']['data'], list):
            valid_targets.extend(data['albums']['data'])
            
        if not valid_targets:
            raise Exception("No albums or playlists found for this query. Cannot guarantee a multi-track queue.")
            
        # Grab the top 3 valid multi-track results and pick one randomly for variety
        top_targets = valid_targets[:3]
        selected_target = random.choice(top_targets)
        
        top_result_url = selected_target['url']
        exact_album_url = top_result_url.replace("http://www.jiosaavn.com", "https://www.jiosaavn.com")
        
        print(f"   -> [Phase 3: Execution] Direct jump to populated queue: {exact_album_url}")
        
        # 3. DIRECT EXECUTION
        driver.get(exact_album_url)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        time.sleep(2.5) 

        print("   -> [Selenium] Resolving interactive playback buttons...")
        play_button_selectors = [
            ".js-play-button",
            "#player_play_pause",
            "button[aria-label='Play']",
            "span[aria-label='Play']",
            "[role='button'][aria-label='Play']"
        ]

        play_btn = None
        for selector in play_button_selectors:
            try:
                play_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                if play_btn:
                    break
            except Exception:
                continue

        if play_btn is None:
            raise TimeoutException("Could not isolate structural playback nodes on destination page.")

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", play_btn)
        time.sleep(0.5)
        
        try:
            play_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", play_btn)

        time.sleep(3.0)
        print(f"   -> [Selenium] SUCCESS: Playing multi-track content from query: '{search_term}'")
        
    except Exception as e:
        print(f"   -> [Error] Hybrid macro routing pipeline failed: {e}")

def go_home_macro():
    """Bypass the UI and hard-navigate directly to the root domain."""
    print("   -> [Selenium] BCI Command 'Lift' received: Routing to Home screen...")
    try:
        driver.get("https://www.jiosaavn.com/")
        print("   -> [Selenium] SUCCESS: Navigated to Home.")
    except Exception as e:
        print(f"   -> [Error] Failed to route home: {e}")
# ---------------------------------------------------------
# JSON PARSER & EXECUTOR
# ---------------------------------------------------------
def process_bci_json(file_path):
    print(f"Loading BCI commands from: {file_path.name}")
    with open(file_path, 'r') as file:
        bci_data = json.load(file)
        
    for entry in bci_data:
        timestamp = entry.get("Timestamp", 0.0)
        command = entry.get("Command", "Neutral")
        confidence = entry.get("Confidence_Score", 0.0)
        
        if confidence < CONFIDENCE_THRESHOLD:
            continue
            
        if not bci_filter.process(timestamp, command):
            continue
            
        if command in COMMAND_MAP:
            action_name, action_target = COMMAND_MAP[command]
            
            # Clean AIML Department Output Log
            print(f"Action Triggered : Right {command} , Action Performed: {action_name} ({confidence})")
            
            if action_target == "MACRO":
                visual_search_macro()
                time.sleep(10.0)  
            elif action_target == "HOME_MACRO":
                go_home_macro()
                time.sleep(2.0)
            else:
                press_vk(action_target)
                time.sleep(2.0)
                
            print("-" * 30)

if __name__ == "__main__":
    json_path = Path(__file__).with_name("all_bci_commands_128hz.json")
    if json_path.exists():
        process_bci_json(json_path)
    else:
        print(f"Error: Could not find {json_path.name}.")