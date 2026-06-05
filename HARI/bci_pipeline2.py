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
# REAL-TIME INFERENCE: DIRECT JIOSAAVN MAPPER & OS CONTROL (Approach 2)
# ---------------------------------------------------------
print("\n--- Simulating Live JioSaavn Output (Approach 2) ---")

CONFIDENCE_THRESHOLD = 0.85  

# Memory to prevent hardware spamming
previous_state = "REST"
output_results = [] # List to hold our JSON payloads

# Map our BCI outputs to Windows OS Media Keys (Approach 2 only uses 3 keys)
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1

def press_vk(vk):
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

vk_mapping = {
    "Play / Pause": VK_MEDIA_PLAY_PAUSE,
    "Next Track": VK_MEDIA_NEXT_TRACK,
    "Previous Track": VK_MEDIA_PREV_TRACK
}

# Delay (seconds) between actions/outputs to avoid rapid toggles
ACTION_DELAY = 1.0

# Use a continuous slice of time (1000 frames) to test natural state changes
continuous_time_slice = X_smoothed.iloc[1000:2000]

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
        
    jiosaavn_action = "None"
    
    # 2. State Change Logic (Only fire when the thought shifts to a new state)
    if verified_state != previous_state:
        
        # The 1-to-1 Direct Mapping
        if verified_state == "RIGHT_HAND":
            jiosaavn_action = "Next Track"
        elif verified_state == "LEFT_HAND":
            jiosaavn_action = "Previous Track"
        elif verified_state == "REST":
            jiosaavn_action = "Play / Pause"
            
        # Update the memory so it doesn't fire again until the state changes
        previous_state = verified_state

    # 3. Build Payload, Log it, and Trigger the Hardware
    if jiosaavn_action != "None":
        payload = {
            "sample_id": int(index),
            "command": verified_state,
            "confidence": round(float(max_prob), 4),
            "jiosaavn_action": jiosaavn_action,
            "status": status
        }
        
        # Save and print the payload
        output_results.append(payload)
        print(json.dumps(payload, indent=4))

        # Only press media keys for verified predictions
        if status == "verified":
            target_vk = vk_mapping.get(jiosaavn_action)
            if target_vk:
                press_vk(target_vk)

        # Wait between actions/outputs to avoid rapid toggles
        time.sleep(ACTION_DELAY)

# 5. Save the collected outputs to result2.json
output_path = Path(__file__).with_name("result2.json")
with open(output_path, "w") as f:
    json.dump(output_results, f, indent=4)
    
print(f"\n✅ Simulation Complete. Saved {len(output_results)} actions to {output_path.name}")
# # ---------------------------------------------------------
# # REAL-TIME INFERENCE: DIRECT JIOSAAVN MAPPER (Approach 2)
# # ---------------------------------------------------------
# print("\n--- Simulating Live JioSaavn Output (Approach 2) ---")

# CONFIDENCE_THRESHOLD = 0.85  

# # Memory to prevent hardware spamming
# previous_state = "REST"
# output_results = [] # List to hold our JSON payloads

# # Use a continuous slice of time (1000 frames) to test natural state changes
# continuous_time_slice = X_smoothed.iloc[1000:2000]

# for index, row in continuous_time_slice.iterrows():
#     frame_df = pd.DataFrame([row.values], columns=X_smoothed.columns)
#     frame_scaled = scaler.transform(frame_df)
    
#     probs = calibrated_svm.predict_proba(frame_scaled)[0]
#     max_prob = np.max(probs)
#     predicted_class = calibrated_svm.classes_[np.argmax(probs)]
    
#     # 1. Verification Gate
#     if max_prob < CONFIDENCE_THRESHOLD:
#         verified_state = "REST"
#         status = "rejected_low_confidence"
#     else:
#         verified_state = predicted_class
#         status = "verified"
        
#     jiosaavn_action = "None"
    
#     # 2. State Change Logic (Only fire when the thought shifts to a new state)
#     if verified_state != previous_state:
        
#         # The 1-to-1 Direct Mapping
#         if verified_state == "RIGHT_HAND":
#             jiosaavn_action = "Next Track"
#         elif verified_state == "LEFT_HAND":
#             jiosaavn_action = "Previous Track"
#         elif verified_state == "REST":
#             jiosaavn_action = "Play / Pause"
            
#         # Update the memory so it doesn't fire again until the state changes
#         previous_state = verified_state

#     # 3. Build the Payload and save it
#     if jiosaavn_action != "None":
#         payload = {
#             "sample_id": int(index),
#             "command": verified_state,
#             "confidence": round(float(max_prob), 4),
#             "jiosaavn_action": jiosaavn_action,
#             "status": status
#         }
        
#         # Add to our list and print to terminal
#         output_results.append(payload)
#         print(json.dumps(payload, indent=4))

# # 4. Save the collected outputs to result2.json
# output_path = Path(__file__).with_name("result2.json")
# with open(output_path, "w") as f:
#     json.dump(output_results, f, indent=4)
    
# print(f"\n✅ Simulation Complete. Saved {len(output_results)} actions to {output_path.name}")