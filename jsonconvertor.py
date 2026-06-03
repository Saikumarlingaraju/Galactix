import pandas as pd
import numpy as np
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.metrics import accuracy_score, classification_report

# ---------------------------------------------------------
# 1. LOAD AND CLEAN DATA (Implementing EDA Insights)
# ---------------------------------------------------------
print("Loading dataset...")
df = pd.read_csv('features_raw.csv')

# INSIGHT 1: Drop FC2 due to extreme variance (87.65 μV) and impossible correlations.
# We also drop the empty trailing column if it exists.
columns_to_drop = ['FC2'] 
if 'Unnamed: 32' in df.columns:
    columns_to_drop.append('Unnamed: 32')

df_clean = df.drop(columns=columns_to_drop)
print(f"Dropped bad channels. Remaining active sensors: {len(df_clean.columns)}")

# ---------------------------------------------------------
# 2. INJECT MOCK LABELS (Temporary solution until LSL timing is recorded)
# ---------------------------------------------------------
# 8064 rows / 6 classes = 1344 rows per class
labels = (['neutral'] * 1344 + 
          ['push'] * 1344 + 
          ['pull'] * 1344 + 
          ['left'] * 1344 + 
          ['right'] * 1344 + 
          ['lift'] * 1344)
df_clean['Label'] = labels

# Separate the remaining 31 sensor columns (X) from the target answers (y)
X = df_clean.drop(columns=['Label'])
y = df_clean['Label']

# Split into Training Data (80%) and Testing Data (20%)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ---------------------------------------------------------
# 3. PREPROCESSING (INSIGHT 3: Standardizing Midline Channels)
# ---------------------------------------------------------
# INSIGHT 3: Scaling is critical here. It tones down the loud, potentially 
# muscular frontocentral channels and boosts the quiet, stable midline 
# channels (Cz, Oz, Fz) so the SVM relies on true neural signals.
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ---------------------------------------------------------
# 4. TRAIN THE CLASSIFIER (Updated to get per-command accuracy)
# ---------------------------------------------------------
print("Training the SVM Classifier... (This might take a moment)")
svm_model = SVC(kernel='rbf', C=1.0, random_state=42) 
svm_model.fit(X_train_scaled, y_train)

# Generate predictions for the test set
predictions = svm_model.predict(X_test_scaled)

# Calculate overall accuracy
overall_accuracy = accuracy_score(y_test, predictions)

# Generate a detailed dictionary containing the accuracy of every single command
detailed_report = classification_report(y_test, predictions, output_dict=True)

print(f"Model Training Complete! Overall Accuracy: {overall_accuracy * 100:.2f}%\n")

# ---------------------------------------------------------
# 5. REAL-TIME JSON INFERENCE ENGINE (Updated for detailed stats)
# ---------------------------------------------------------
def process_live_eeg_to_json(eeg_feature_vector, overall_acc, class_report):
    # 1. Convert to DataFrame
    live_df = pd.DataFrame([eeg_feature_vector], columns=X.columns)
    
    # 2. Scale the data
    scaled_vector = scaler.transform(live_df)
    
    # 3. Predict the thought
    ml_prediction = svm_model.predict(scaled_vector)[0]
    
    # 4. Define all available actions
    command_mapping = {
        "push": "play/pause",
        "left": "next track",
        "right": "previous track",
        "pull": "volume up",
        "lift": "volume down",
        "neutral": "none"
    }
    
    # 5. Build the detailed list with individual accuracies
    individual_commands_list = []
    for cmd, action in command_mapping.items():
        # Look up the specific accuracy (recall) for this command from the report
        # It defaults to 0.0 if the command isn't found for some reason
        cmd_accuracy = class_report.get(cmd, {}).get('recall', 0.0) * 100
        
        individual_commands_list.append({
            "mental_command": cmd,
            "action_triggered": action,
            "training_accuracy": f"{cmd_accuracy:.2f}%"
        })
    
    # 6. Build the final output dictionary
    output_data = {
        "system_status": {
            "overall_accuracy": f"{overall_acc * 100:.2f}%",
            "active_sensors": len(live_df.columns)
        },
        "commands_status": individual_commands_list,
        "live_prediction": {
            "mental_command": ml_prediction,
            "action_triggered": command_mapping.get(ml_prediction, "unknown")
        }
    }
    
    # 7. Return formatted JSON
    return json.dumps(output_data, indent=4)

# ---------------------------------------------------------
# 6. SIMULATE LIVE DATA FEED
# ---------------------------------------------------------
print("--- Simulating Live Headset WebSockets Feed ---")

# Grab a sample row from our test data
sample_live_data = X_test.iloc[150].values 

# Feed the live data AND the performance metrics into the function
final_json_output = process_live_eeg_to_json(sample_live_data, overall_accuracy, detailed_report)

print(final_json_output)

output_path = Path(__file__).with_name('live_bci_output.json')
output_path.write_text(final_json_output + '\n', encoding='utf-8')
print(f"Saved JSON output to: {output_path}")