import pyautogui
import time


class MediaController:
    def __init__(self, power_threshold=0.5):
        # Only trigger commands if the BCI command power exceeds this threshold
        self.power_threshold = power_threshold
        # Prevent rapid-fire triggers
        self.last_action_time = 0
        self.cooldown = 1.5

    def execute_command(self, action, power):
        """Maps BCI commands to OS media keys."""
        current_time = time.time()

        # Check threshold and cooldown
        if power < self.power_threshold or (current_time - self.last_action_time) < self.cooldown:
            return

        if action == "push":
            print(f"Executing: PLAY/PAUSE (Power: {power})")
            pyautogui.press('playpause')
            self.last_action_time = current_time

        elif action == "left":
            print(f"Executing: PREVIOUS TRACK (Power: {power})")
            pyautogui.press('prevtrack')
            self.last_action_time = current_time

        elif action == "right":
            print(f"Executing: NEXT TRACK (Power: {power})")
            pyautogui.press('nexttrack')
            self.last_action_time = current_time


# --- Testing the Wrapper ---
if __name__ == "__main__":
    controller = MediaController(power_threshold=0.6)

    print("Testing Media Controller. Have JioSaavn open and active.")
    time.sleep(2)

    # Simulate receiving a high-confidence "push" command
    controller.execute_command("push", 0.85)
import pyautogui
import time

class MediaController:
    def __init__(self, power_threshold=0.5):
        # Only trigger commands if the BCI command power exceeds this threshold
        self.power_threshold = power_threshold
        # Prevent rapid-fire triggers
        self.last_action_time = 0 
        self.cooldown = 1.5 

    def execute_command(self, action, power):
        """Maps BCI commands to OS media keys."""
        current_time = time.time()
        
        # Check threshold and cooldown
        if power < self.power_threshold or (current_time - self.last_action_time) < self.cooldown:
            return

        if action == "push":
            print(f"Executing: PLAY/PAUSE (Power: {power})")
            pyautogui.press('playpause')
            self.last_action_time = current_time
            
        elif action == "left":
            print(f"Executing: PREVIOUS TRACK (Power: {power})")
            pyautogui.press('prevtrack')
            self.last_action_time = current_time
            
        elif action == "right":
            print(f"Executing: NEXT TRACK (Power: {power})")
            pyautogui.press('nexttrack')
            self.last_action_time = current_time

# --- Testing the Wrapper ---
if __name__ == "__main__":
    controller = MediaController(power_threshold=0.6)
    
    print("Testing Media Controller. Have JioSaavn open and active.")
    time.sleep(2)
    
    # Simulate receiving a high-confidence "push" command
    controller.execute_command("push", 0.85)