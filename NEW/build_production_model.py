import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from imblearn.over_sampling import RandomOverSampler
import joblib

# 1. Load the raw reference dataset
print("Loading the complete Reference Dataset...")
df = pd.read_csv('final_epocx.csv')
eeg_channels = ['AF3', 'F7', 'F3', 'FC5', 'T7', 'P7', 'O1', 'O2', 'P8', 'T8', 'FC6', 'F4', 'F8', 'AF4']

samples_per_epoch = 512
num_epochs = len(df) // samples_per_epoch

epoch_features = []
epoch_commands = []

# 2. Extract the 60 continuous epochs
print("Extracting 2-second telemetry blocks...")
for i in range(num_epochs):
    start_idx = i * samples_per_epoch
    end_idx = start_idx + samples_per_epoch
    window = df.iloc[start_idx:end_idx]
    command = window['Command'].iloc[0]
    
    features = {}
    for ch in eeg_channels:
        features[f'{ch}_mean'] = window[ch].mean()
        features[f'{ch}_std'] = window[ch].std()
        
    epoch_features.append(features)
    epoch_commands.append(command)

X = pd.DataFrame(epoch_features)
y = pd.Series(epoch_commands)

# 3. Balance the entire reference dictionary
print("\nApplying RandomOverSampler to guarantee all 9 commands are recognized...")
ros = RandomOverSampler(random_state=42)
X_balanced, y_balanced = ros.fit_resample(X, y)

print(f"Total production data points: {len(X_balanced)}")
print(y_balanced.value_counts())

# 4. Train the Final Production Engine
print("\nTraining the final Random Forest engine on 100% of the data...")
production_model = RandomForestClassifier(n_estimators=100, random_state=42)
production_model.fit(X_balanced, y_balanced)

# 5. Export the Code Hand-off Artifact
model_filename = 'bci_engine.pkl'
joblib.dump(production_model, model_filename)

print(f"\n=== SUCCESS ===")
print(f"The 9-Command BCI Engine has been successfully exported as '{model_filename}'!")
print("This file is ready to be handed off to the operations team for live ingestion.")