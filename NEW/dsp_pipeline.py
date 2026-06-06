import pandas as pd
import numpy as np
from imblearn.over_sampling import RandomOverSampler
from collections import Counter

# 1. Load the raw Emotiv EPOC X dataset
print("Loading raw dataset...")
df = pd.read_csv('final_epocx.csv')

# The 14 Emotiv electrode channels
eeg_channels = ['AF3', 'F7', 'F3', 'FC5', 'T7', 'P7', 'O1', 'O2', 'P8', 'T8', 'FC6', 'F4', 'F8', 'AF4']

# 2. EPOCHING: Chop the continuous stream into 2-second blocks (512 samples)
samples_per_epoch = 512
num_epochs = len(df) // samples_per_epoch

print(f"Slicing raw data into {num_epochs} distinct 2-second Epochs...")

epoch_features = []
epoch_labels = []
epoch_commands = []

for i in range(num_epochs):
    # Slice the dataframe for the current 2-second window
    start_idx = i * samples_per_epoch
    end_idx = start_idx + samples_per_epoch
    window = df.iloc[start_idx:end_idx]
    
    # We grab the label/command from the first row of the window 
    label = window['Label'].iloc[0]
    command = window['Command'].iloc[0]
    
    # Feature Extraction: Calculate Mean and Standard Deviation for all 14 channels
    features = {}
    for ch in eeg_channels:
        features[f'{ch}_mean'] = window[ch].mean()
        features[f'{ch}_std'] = window[ch].std()
        
    epoch_features.append(features)
    epoch_labels.append(label)
    epoch_commands.append(command)

# Create the new "Snapshot" dataframe
features_df = pd.DataFrame(epoch_features)
print("\n--- Before Oversampling (Class Imbalance) ---")
print(pd.Series(epoch_commands).value_counts())

# 3. APPLY RANDOM OVERSAMPLING: Balance the dataset by duplicating minority classes
print("\nApplying RandomOverSampler to balance the dataset...")
ros = RandomOverSampler(random_state=42)

# Fit and resample
X_resampled, y_resampled = ros.fit_resample(features_df, epoch_labels)

# 4. Reconstruct the balanced dataset
label_to_command = dict(zip(epoch_labels, epoch_commands))

balanced_df = pd.DataFrame(X_resampled, columns=features_df.columns)
balanced_df['Label'] = y_resampled
balanced_df['Command'] = balanced_df['Label'].map(label_to_command)

print("\n--- After Oversampling (Perfectly Balanced) ---")
print(balanced_df['Command'].value_counts())

# 5. Save for the ML Team
output_filename = 'balanced_bci_features.csv'
balanced_df.to_csv(output_filename, index=False)
print(f"\nPipeline Complete! Saved ML-ready data to {output_filename}")