import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from imblearn.over_sampling import RandomOverSampler

# 1. Load the raw dataset and re-epoch to get the clean, unbalanced data
print("Loading and slicing raw dataset...")
df = pd.read_csv('final_epocx.csv')
eeg_channels = ['AF3', 'F7', 'F3', 'FC5', 'T7', 'P7', 'O1', 'O2', 'P8', 'T8', 'FC6', 'F4', 'F8', 'AF4']

samples_per_epoch = 512
num_epochs = len(df) // samples_per_epoch

epoch_features = []
epoch_commands = []

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

# 2. THE CRITICAL FIX: Split the data BEFORE oversampling
print("Splitting data into strictly isolated Train and Test sets...")
# We use stratify=y to ensure the test set gets a fair representation of the commands
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Balance ONLY the training data
print("Applying Oversampling ONLY to the training data...")
ros = RandomOverSampler(random_state=42)
X_train_balanced, y_train_balanced = ros.fit_resample(X_train, y_train)

print(f"\nTraining on {len(X_train_balanced)} balanced samples...")
print(f"Testing on {len(X_test)} strictly unseen, original samples...\n")

# 4. Train the AI Model
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train_balanced, y_train_balanced)

# 5. The True Final Exam
y_pred = rf_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"=== TRUE MODEL ACCURACY: {accuracy * 100:.2f}% ===\n")
# zero_division=0 prevents errors if a rare class didn't make it into the test predictions
print(classification_report(y_test, y_pred, zero_division=0))