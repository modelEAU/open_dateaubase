"""Remove the Parts table entry from dictionary.json since it's no longer needed."""

import json
from pathlib import Path

json_path = Path("src/dictionary.json")

# Load dictionary
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Count before
before_count = len(data['parts'])

# Remove Parts table entry
data['parts'] = [p for p in data['parts'] if p['Part_ID'] != 'Parts']

# Count after
after_count = len(data['parts'])

# Save
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Removed Parts table entry")
print(f"Parts count: {before_count} → {after_count}")
