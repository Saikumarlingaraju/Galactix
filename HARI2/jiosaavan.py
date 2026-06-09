import json
import ctypes
import time
import random
import pyautogui 
from pathlib import Path

# ---------------------------------------------------------
# CONFIGURATION & MAPPING
# ---------------------------------------------------------

SEARCH_BAR_X = 1199  
SEARCH_BAR_Y = 56

FIRST_SONG_X = 1155  
FIRST_SONG_Y = 141

PLAY_BUTTON_X = 148 # big play button X
PLAY_BUTTON_Y = 211 # big play button Y
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
    "Pull": ("Search Random Song", "MACRO") 
}

SONG_LIST = [
    "Shape of You",
    "Phir Se",
    "Tum Hi Ho",
    "Endhayya Saami",
    "Firestorm"
]

CONFIDENCE_THRESHOLD = 0.5

# ---------------------------------------------------------
# HARDWARE CONTROL & MACROS
# ---------------------------------------------------------
def press_vk(vk):
    """Simulate a simple OS-level media key press."""
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

def perform_search_macro():
    """Simulate human interaction with a 3-click UI sequence."""
    song = random.choice(SONG_LIST)
    print(f"   -> [UI Macro] Initiating search for: '{song}'")
    
    # CLICK 1: Focus the Search Bar
    pyautogui.click(x=SEARCH_BAR_X, y=SEARCH_BAR_Y)
    time.sleep(0.5) 
    
    # Clear any existing text
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    
    # Type the song name
    pyautogui.write(song, interval=0.1)
    
    # Wait for the dropdown menu to load the new results
    time.sleep(2.5) 
    
    # CLICK 2: Click the top result in the dropdown list
    pyautogui.click(x=FIRST_SONG_X, y=FIRST_SONG_Y)
    
    # Wait for the Album/Song detail page to fully render
    time.sleep(3.0)
    
    # CLICK 3: Click the Big Play Button on the album art
    pyautogui.click(x=PLAY_BUTTON_X, y=PLAY_BUTTON_Y)
    
    print(f"   -> [UI Macro] Clicked Play. '{song}' should now be playing.")

# ---------------------------------------------------------
# JSON PARSER & EXECUTOR
# ---------------------------------------------------------
def process_bci_json(file_path):
    print(f"Loading BCI commands from: {file_path.name}")
    
    with open(file_path, 'r') as file:
        bci_data = json.load(file)
        
    print(f"Scanning {len(bci_data)} frames for actionable commands...\n")
    print("-" * 50)
    
    for entry in bci_data:
        timestamp = entry.get("Timestamp", 0.0)
        command = entry.get("Command", "Neutral")
        confidence = entry.get("Confidence_Score", 0.0)
        
        if command == "Neutral" or confidence < CONFIDENCE_THRESHOLD:
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
                perform_search_macro()
                # Give it time to settle before processing the next BCI command
                time.sleep(10.0) 
            else:
                press_vk(action_target)
                time.sleep(5.0) 
                
            print("-" * 30)

if __name__ == "__main__":
    json_path = Path(__file__).with_name("all_bci_commands_128hz.json")
    
    if json_path.exists():
        process_bci_json(json_path)
    else:
        print(f"Error: Could not find {json_path.name}.")