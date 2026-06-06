import pandas as pd
from sklearn.preprocessing import StandardScaler

# 1. Load the dataset
# (Make sure the filename matches what is on your local machine)
df = pd.read_excel('user_a.xlsx')

# 2. Check for any missing values before we start
print("Missing values in dataset:", df.isnull().sum().sum())

# 3. Separate the answers (Class) from the data
# We will save original_labels just in case we want to compare later
original_labels = df['Class'] 
features_only = df.drop('Class', axis=1)

# 4. Standardize the features (Mean = 0, Variance = 1)
scaler = StandardScaler()
scaled_data = scaler.fit_transform(features_only)

# Convert back to a DataFrame for easy viewing
scaled_df = pd.DataFrame(scaled_data, columns=features_only.columns)

# 5. Output the results for verification
print("\nNew Data Shape:", scaled_df.shape)
print("\nFirst 3 rows of scaled data:")
print(scaled_df.head(3))

from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Initialize PCA to compress 112 features down to 2 Principal Components
pca = PCA(n_components=2)
pca_data = pca.fit_transform(scaled_data)

# 2. Create a new DataFrame for plotting
pca_df = pd.DataFrame(data=pca_data, columns=['PC1', 'PC2'])

# 3. Add the original labels back JUST for visualization 
# (The PCA didn't use them to compress, we just want to see where the old 3 commands landed)
pca_df['Original_Command'] = original_labels.values # .values ensures index alignment

# 4. Plot the 2D map of the brainwaves
plt.figure(figsize=(10, 8))
sns.scatterplot(
    x='PC1', 
    y='PC2', 
    hue='Original_Command', 
    palette='viridis', 
    data=pca_df, 
    alpha=0.7
)
plt.title('2D PCA of Brainwave Signals (112 Features Compressed)')
plt.xlabel(f'Principal Component 1 ({pca.explained_variance_ratio_[0]*100:.1f}% Variance)')
plt.ylabel(f'Principal Component 2 ({pca.explained_variance_ratio_[1]*100:.1f}% Variance)')
plt.legend(title='Original Labels')
plt.grid(True, linestyle='--', alpha=0.5)
plt.show()

# 5. Let's see how much "information" these 2 components actually kept
print(f"\nVariance captured by PC1: {pca.explained_variance_ratio_[0]*100:.2f}%")
print(f"Variance captured by PC2: {pca.explained_variance_ratio_[1]*100:.2f}%")
print(f"Total variance captured: {sum(pca.explained_variance_ratio_)*100:.2f}%")

from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

# We will test finding anywhere from 2 to 10 clusters (commands)
wcss = [] # Within-Cluster Sum of Square (measures how tight the clusters are)

print("Running K-Means tests... this might take a few seconds.")

# Loop through 2 to 10 clusters
for i in range(2, 11):
    # Initialize the model
    kmeans = KMeans(n_clusters=i, init='k-means++', max_iter=300, n_init=10, random_state=42)
    # Fit the model on the full 112-feature scaled data
    kmeans.fit(scaled_data) 
    # Save the error score
    wcss.append(kmeans.inertia_)

# Plot the results
plt.figure(figsize=(10, 6))
plt.plot(range(2, 11), wcss, marker='o', linestyle='--', color='b')
plt.title('The Elbow Method (Finding the Number of Hidden Commands)')
plt.xlabel('Number of Clusters (Commands)')
plt.ylabel('WCSS (Lower means tighter groupings)')
plt.xticks(range(2, 11))
plt.grid(True, linestyle='--', alpha=0.7)
plt.show()

# 1. Run K-Means with our chosen optimal number (5 clusters)
optimal_clusters = 5
print(f"\nGrouping data into {optimal_clusters} discovered commands...")

final_kmeans = KMeans(n_clusters=optimal_clusters, init='k-means++', n_init=10, random_state=42)
# We fit on the full 112-feature data to get the most accurate groupings
new_command_labels = final_kmeans.fit_predict(scaled_data)

# 2. Add these new discovered labels to our PCA DataFrame for plotting
pca_df['Discovered_Command'] = new_command_labels

# 3. Plot the NEW clusters on our 2D map
plt.figure(figsize=(10, 8))
sns.scatterplot(
    x='PC1', 
    y='PC2', 
    hue='Discovered_Command', 
    palette='Set1', # Using a bright color palette to distinguish the new groups
    data=pca_df, 
    alpha=0.7
)
plt.title(f'Unsupervised Learning: {optimal_clusters} Discovered Brainwave Commands')
plt.xlabel(f'Principal Component 1')
plt.ylabel(f'Principal Component 2')
plt.legend(title='New Command ID', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout() # Keeps the legend from getting cut off
plt.show()

import numpy as np

# 1. Add the discovered commands to the original 112-feature scaled dataframe
scaled_df['Discovered_Command'] = new_command_labels

# 2. Group by the new commands and calculate the average for every electrode/frequency
cluster_profiles = scaled_df.groupby('Discovered_Command').mean()

print("Profiling the 5 Discovered Commands...\n")

# 3. For each command, find the top 3 strongest signal features
for cluster_id in range(optimal_clusters):
    # Get the mean values for this specific cluster
    profile = cluster_profiles.loc[cluster_id]
    
    # Sort them to find the highest absolute values (strongest deviations from the baseline)
    top_features = profile.abs().sort_values(ascending=False).head(3)
    
    print(f"--- Command {cluster_id} ---")
    print("Defining physiological signals:")
    for feature, abs_value in top_features.items():
        # Check the original profile value to see if it's abnormally high or low
        direction = "ELEVATED" if profile[feature] > 0 else "SUPPRESSED"
        print(f"  - {feature}: {direction} (Deviation Score: {abs_value:.2f})")
    print("")

from sklearn.metrics.pairwise import cosine_similarity
import seaborn as sns
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

# 1. Push the boundary to 25 micro-commands
exploration_k_extreme = 25
print(f"\nRunning extreme exploration with {exploration_k_extreme} micro-commands...")

kmeans_extreme = KMeans(n_clusters=exploration_k_extreme, init='k-means++', n_init=10, random_state=42)
extreme_labels = kmeans_extreme.fit_predict(scaled_data)

# 2. Get the DNA (centroids) of all 25 micro-commands
centroids_extreme = kmeans_extreme.cluster_centers_

# 3. Calculate similarity
similarity_matrix_extreme = cosine_similarity(centroids_extreme)

# 4. Plot the 25x25 Heatmap
plt.figure(figsize=(14, 12))
# annot=False keeps the visual clean so we can look at the color blocks
sns.heatmap(similarity_matrix_extreme, annot=False, cmap='coolwarm', vmin=-1, vmax=1)
plt.title(f'Extreme Stress Test: {exploration_k_extreme} Micro-States Matrix')
plt.xlabel('Discovered Command ID')
plt.ylabel('Discovered Command ID')
plt.show()