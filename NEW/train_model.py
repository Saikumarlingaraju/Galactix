import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# 1. Load the balanced dataset
print("Loading ML-ready BCI data...")
df = pd.read_csv('balanced_bci_features.csv')

# Separate features (X) and labels (y)
# We drop 'Label' and 'Command' to keep only the 28 numerical features (14 means, 14 stds)
X = df.drop(['Label', 'Command'], axis=1)
y = df['Command']

# 2. Train/Test Split
# We keep 80% of the data for studying, and hide 20% for the final exam
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

print(f"Training on {len(X_train)} samples, Testing on {len(X_test)} samples...\n")

# 3. Train the AI Model
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)

# 4. Give the AI its final exam
y_pred = rf_model.predict(X_test)

# 5. Output the Report Card
accuracy = accuracy_score(y_test, y_pred)
print(f"=== MODEL ACCURACY: {accuracy * 100:.2f}% ===\n")
print("Detailed Classification Report:")
print(classification_report(y_test, y_pred))

# 6. Bonus: Which electrodes matter the most? (Feature Importance)
importances = rf_model.feature_importances_
indices = np.argsort(importances)[-10:] # Get the top 10 most important features

plt.figure(figsize=(10, 6))
plt.title('Top 10 Most Important Brainwave Features for Navigation')
plt.barh(range(len(indices)), importances[indices], align='center', color='teal')
plt.yticks(range(len(indices)), [X.columns[i] for i in indices])
plt.xlabel('Relative Importance (How much the AI relied on this electrode)')
plt.tight_layout()
plt.show()