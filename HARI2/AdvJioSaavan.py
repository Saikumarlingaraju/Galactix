import json
import ctypes
import time
import random
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------------------------------------------------------
# CONFIGURATION & MAPPING
# ---------------------------------------------------------
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE

COMMAND_MAP = {
    "Push": ("Play / Pause", VK_MEDIA_PLAY_PAUSE),
    "Left": ("Previous Track", VK_MEDIA_PREV_TRACK),
    "Right": ("Next Track", VK_MEDIA_NEXT_TRACK),
    "Lift": ("Volume Up", VK_VOLUME_UP),
    "Drop": ("Volume Down", VK_VOLUME_DOWN),
    "Pull": ("Search", "MACRO") 
}

SEARCH_TERMS = [
    "Shape of You",
    "Tum Hi Ho",
    "Aashiqui 2",
    "Taaza Tunes"
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
        self.previous_command = "Neutral"
        self.last_volume_time = 0.0  
        
    def process(self, current_timestamp, current_command):
        if current_command == "Neutral":
            self.previous_command = "Neutral"
            return False
            
        if current_command == self.previous_command:
            if current_command in ["Lift", "Drop"]:
                if (current_timestamp - self.last_volume_time) >= 3.0:
                    self.last_volume_time = current_timestamp
                    return True 
            return False 
            
        self.previous_command = current_command
        if current_command in ["Lift", "Drop"]:
            self.last_volume_time = current_timestamp
            
        return True

bci_filter = BCISignalFilter()

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
    """Visually types, waits for results to actually load, and clicks the first song."""
    search_term = random.choice(SEARCH_TERMS)
    print(f"   -> [Selenium] Translating thought to text: '{search_term}'")
    
    try:
        # 1. Target the Search Bar
        search_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.rbt-input-main"))
        )
        driver.execute_script("arguments[0].click();", search_box)
        driver.execute_script("arguments[0].value = '';", search_box)
        
        # 2. Type with delay
        for char in search_term:
            box = driver.find_element(By.CSS_SELECTOR, "input.rbt-input-main")
            box.send_keys(char)
            time.sleep(0.05) 
        
        box = driver.find_element(By.CSS_SELECTOR, "input.rbt-input-main")
        box.send_keys(Keys.ENTER)      
        
        # 3. CRITICAL FIX: Wait until the results list is NOT empty
        print(f"   -> [Selenium] Waiting for search results to load...")
        song_list_xpath = "//main//a[contains(@href, '/song/')]"
        
        # This will wait up to 20 seconds for at least ONE song link to appear in the DOM
        first_result = WebDriverWait(driver, 20).until(
            lambda d: d.find_elements(By.XPATH, song_list_xpath) and d.find_elements(By.XPATH, song_list_xpath)[0]
        )
        
        # Click the first song link found
        driver.execute_script("arguments[0].click();", first_result)
        print(f"   -> [Selenium] Result found and clicked. Loading track page...")
        
        # 4. Final Play Trigger
        time.sleep(3.0) 
        play_btn_xpath = "//*[contains(text(), 'Start Radio') or contains(@class, 'js-play-button')]"
        play_btn = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, play_btn_xpath))
        )
        driver.execute_script("arguments[0].click();", play_btn)
        
        print(f"   -> [Selenium] SUCCESS: '{search_term}' is now playing!")
        
    except Exception as e:
        print(f"   -> [Error] Visual search failed: {e}")
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
            
            payload = {
                "sample_id": int(timestamp),
                "raw_brain_state": command,
                "confidence": round(float(confidence), 4),
                "jiosaavn_trigger": action_name,
                "status": "verified"
            }
            
            print(json.dumps(payload, indent=4))
            
            if action_target == "MACRO":
                visual_search_macro()
                time.sleep(10.0)  
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