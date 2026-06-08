import json
from collections import defaultdict

input_filename = 'HARI2/final_epocx_128hz.json'
output_filename = 'HARI2/all_bci_commands_128hz.json'

print(f"1. Loading classifier log data from {input_filename}...")
with open(input_filename, 'r') as f:
    data = json.load(f)

print("2. Extracting true trial segments...")
all_json_outputs = []
current_segment_confidence = None

# Because confidence is segment-level (constant for all samples in a trial window),
# we can identify a new trial window simply by detecting when the confidence changes.
for row in data:
    if row['Confidence'] != current_segment_confidence:
        current_segment_confidence = row['Confidence']
        
        # Build the operations payload using the REAL data
        payload = {
            "Timestamp": round(row['Timestamp'], 3),
            "Confidence_Score": round(row['Confidence'], 3),
            "Command": row['Command'],
            # Actionable if confidence clears the 85% threshold
            "Is_Actionable": bool(row['Confidence'] > 0.85)
        }
        all_json_outputs.append(payload)

# Save the extracted segment sequence
with open(output_filename, 'w') as f:
    json.dump(all_json_outputs, f, indent=4)

print(f"-> Successfully extracted {len(all_json_outputs)} unique command segments.")
print(f"-> Saved clean operations payload to '{output_filename}'.")

print("\n3. FLAGGING INTRA-CLASS VARIABILITY (Crucial for Review)")
# Group confidences by command to show the spread
command_confidences = defaultdict(list)
for payload in all_json_outputs:
    command_confidences[payload['Command']].append(payload['Confidence_Score'])

print(f"{'Command':<12} | {'Trials':<6} | {'Min Conf':<10} | {'Max Conf':<10} | {'Mean Conf':<10}")
print("-" * 60)
for cmd, confs in command_confidences.items():
    min_c = min(confs)
    max_c = max(confs)
    mean_c = sum(confs) / len(confs)
    print(f"{cmd:<12} | {len(confs):<6} | {min_c:<10.3f} | {max_c:<10.3f} | {mean_c:<10.3f}")

print("\nPreview of the first 3 operations payloads:")
print(json.dumps(all_json_outputs[:3], indent=4))