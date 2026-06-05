from pathlib import Path
from sklearn.model_selection import GridSearchCV
import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, accuracy_score
import ctypes
import time
# ---------------------------------------------------------
# PHASE 1: LOAD & FILTER BIOLOGICAL FEATURES (From CSV)
# ---------------------------------------------------------
print("Loading User A Dataset from CSV...")

# Load the workbook relative to this script so the file works from any cwd.
workbook_path = Path(__file__).with_name("user_a.xlsx")
df = pd.read_excel(workbook_path)

# 1. Separate the Target Labels
y_labels = df['Class']

# 2. Isolate Motor Cortex Channels (Bilateral Activation)
# We are keeping both left (FC5, F3, AF3) and right (FC6, F4, AF4) hemispheres
motor_channels = ['FC5', 'F3', 'AF3', 'FC6', 'F4', 'AF4']

# 3. Keep only the frequencies relevant to Motor Imagery (Alpha and Beta)
# We drop Delta (sleep/blinks) and Theta (deep relaxation)
selected_columns = []
for col in df.columns:
    if any(channel in col for channel in motor_channels):
        if 'alpha' in col or 'beta' in col:
            selected_columns.append(col)

X_features = df[selected_columns]

print(f"Phase 1 Complete: Extracted {len(X_features.columns)} bilateral alpha/beta features.")

# ---------------------------------------------------------
# PHASE 2: TEMPORAL SMOOTHING (Rolling Window)
# ---------------------------------------------------------
print("Applying Temporal Smoothing...")

# UPGRADE: Increased window to 5 frames for higher stability
window_size = 5 
X_smoothed = X_features.rolling(window=window_size).mean()
X_smoothed = X_smoothed.dropna()
y_labels_smoothed = y_labels.loc[X_smoothed.index]

print(f"Phase 2 Complete: Buffered dataset ready with {len(X_smoothed)} stable frames.")


# ---------------------------------------------------------
# PHASE 4: HYPERPARAMETER TUNING & ML ENGINE
# ---------------------------------------------------------
print("\nOptimizing SVM Hyperparameters (GridSearch)...")

label_mapping = {0.0: "REST", 1.0: "LEFT_HAND", 2.0: "RIGHT_HAND"}
y_mapped = y_labels_smoothed.map(lambda x: label_mapping.get(x, "REST") if isinstance(x, (int, float)) else x)

X_train, X_test, y_train, y_test = train_test_split(
    X_smoothed, y_mapped, test_size=0.2, random_state=42, stratify=y_mapped
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 1. Define the grid of parameters to test
param_grid = {
    'C': [0.1, 1, 10, 100],           # How hard the model tries to avoid misclassification
    'gamma': ['scale', 'auto', 0.1, 0.01] # How tight the decision boundaries wrap around the data
}

# 2. Run the Grid Search (this might take 10-20 seconds to compute)
base_svm = SVC(kernel='rbf', class_weight='balanced', random_state=42)
grid_search = GridSearchCV(base_svm, param_grid, cv=3, n_jobs=-1, verbose=1)
grid_search.fit(X_train_scaled, y_train)

print(f"\n✅ Grid Search Complete! Best Parameters: {grid_search.best_params_}")

# 3. Take the absolute best model and calibrate its confidence scores
best_svm = grid_search.best_estimator_
calibrated_svm = CalibratedClassifierCV(estimator=best_svm, cv=5)
calibrated_svm.fit(X_train_scaled, y_train)

predictions = calibrated_svm.predict(X_test_scaled)
print(f"Optimized Model Accuracy: {accuracy_score(y_test, predictions) * 100:.2f}%")
print("-" * 40)
print(classification_report(y_test, predictions))

# ---------------------------------------------------------
# REAL-TIME INFERENCE & JIOSAAVN COMMAND MAPPER
# ---------------------------------------------------------
print("\n--- Simulating Live JioSaavn Output ---")

CONFIDENCE_THRESHOLD = 0.85  

# Variables to track the "State Machine" (Memory)
current_thought = "REST"
thought_duration = 0

# Collect triggered actions for saving to disk
output_results = []

# Delay (seconds) after triggering an action to avoid rapid-fire events
ACTION_DELAY = 1.0

# Grab 100 continuous, chronological frames from the middle of the recording
continuous_time_slice = X_smoothed.iloc[1000:2000]

VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE

def press_vk(vk):
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

vk_mapping = {
    "Play / Pause": VK_MEDIA_PLAY_PAUSE,
    "Next Track": VK_MEDIA_NEXT_TRACK,
    "Previous Track": VK_MEDIA_PREV_TRACK,
    "Volume Up": VK_VOLUME_UP,
    "Volume Down": VK_VOLUME_DOWN
}

for index, row in continuous_time_slice.iterrows():
    frame_df = pd.DataFrame([row.values], columns=X_smoothed.columns)
    frame_scaled = scaler.transform(frame_df)

    probs = calibrated_svm.predict_proba(frame_scaled)[0]
    max_prob = np.max(probs)
    predicted_class = calibrated_svm.classes_[np.argmax(probs)]

    # 1. Verification Gate
    if max_prob < CONFIDENCE_THRESHOLD:
        verified_state = "REST"
        status = "rejected_low_confidence"
    else:
        verified_state = predicted_class
        status = "verified"

    # 2. The JioSaavn Sequence Logic (State Machine)
    jiosaavn_action = "None"

    # If the user is holding the same thought, count how long they hold it
    if verified_state == current_thought and verified_state != "REST":
        thought_duration += 1

        # "Long Hold" Logic (Volume Control)
        if thought_duration == 4:  # Triggered exactly on the 4th consecutive frame
            if current_thought == "RIGHT_HAND":
                jiosaavn_action = "Volume Up"
            elif current_thought == "LEFT_HAND":
                jiosaavn_action = "Volume Down"

    # If the user changed their thought (e.g., REST -> LEFT_HAND, or LEFT -> REST)
    elif verified_state != current_thought:
        # "Quick Click" Logic (Track Navigation)
        # We trigger this when they release the thought back to REST
        if verified_state == "REST" and thought_duration > 0 and thought_duration < 4:
            if current_thought == "RIGHT_HAND":
                jiosaavn_action = "Next Track"
            elif current_thought == "LEFT_HAND":
                jiosaavn_action = "Previous Track"

        # "Combo" Logic (Play/Pause)
        if current_thought == "LEFT_HAND" and verified_state == "RIGHT_HAND":
            jiosaavn_action = "Play / Pause"

        # Update memory for the next loop
        current_thought = verified_state
        thought_duration = 1 if verified_state != "REST" else 0

    # 3. Build the final Payload
    payload = {
        "sample_id": int(index),
        "raw_brain_state": verified_state,
        "confidence": round(float(max_prob), 4),
        "jiosaavn_trigger": jiosaavn_action,
        "status": status
    }

    # 4. Trigger and log actions
    if jiosaavn_action != "None":
            # Save and print the payload
            output_results.append(payload)
            print(json.dumps(payload, indent=4))

            # Only trigger hardware actions for verified predictions
            if status == "verified":
                target_vk = vk_mapping.get(jiosaavn_action)
                if target_vk:
                    press_vk(target_vk)

            # Wait between actions/outputs to avoid rapid toggles
            time.sleep(ACTION_DELAY)
        

# Save collected outputs to result1.json
output_path = Path(__file__).with_name("result1.json")
with open(output_path, "w") as f:
    json.dump(output_results, f, indent=4)

print(f"\n✅ Simulation Complete. Saved {len(output_results)} actions to {output_path.name}")
    # 3. Build the final Payload
#     payload = {
#         "sample_id": int(index),
#         "raw_brain_state": verified_state,
#         "confidence": round(float(max_prob), 4),
#         "jiosaavn_trigger": jiosaavn_action
#     }
    
#     # Only print if an action was actually triggered to reduce terminal spam
#     if jiosaavn_action != "None":
#         # Save action to our results list and print
#         output_results.append(payload)
#         print(json.dumps(payload, indent=4))

# # Save collected outputs to result1.json
# output_path = Path(__file__).with_name("result1.json")
# with open(output_path, "w") as f:
#     json.dump(output_results, f, indent=4)

# print(f"\n✅ Simulation Complete. Saved {len(output_results)} actions to {output_path.name}")