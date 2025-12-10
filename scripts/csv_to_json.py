"""
One-time migration script: CSV -> JSON

Usage:
    uv run python scripts/csv_to_json.py

This will:
1. Read src/dictionary.csv
2. Parse into JSON structure
3. Validate with Pydantic
4. Write to src/dictionary.json
5. Print validation report
"""

import csv
import json
import sys
from pathlib import Path
from collections import defaultdict

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from open_dateaubase.models import Dictionary


def csv_to_json():
    csv_path = project_root / "src/dictionary.csv"
    json_path = project_root / "src/dictionary.json"

    parts = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

        # Find all *_present columns
        present_columns = [col for col in fieldnames
                          if col.endswith('_present') and col != 'Parts_present']

        for row in rows:
            part_id = row['Part_ID']
            part_type = row['Part_type']

            # Skip Parts table self-referential fields (they describe the schema itself)
            # These are the fields that only appear in the "Parts" table with Parts_present
            if row.get('Parts_present') and not any(row.get(col) for col in present_columns):
                print(f"Skipping Parts table field: {part_id}")
                continue

            # Base fields
            part_data = {
                "Part_ID": part_id,
                "Label": row['Label'],
                "Description": row['Description'],
                "Part_type": part_type
            }

            # Type-specific fields
            if part_type in ['key', 'property', 'compositeKeyFirst',
                             'compositeKeySecond', 'parentKey']:
                part_data["SQL_data_type"] = row.get('SQL_data_type') or None
                part_data["Is_required"] = row.get('Is_required') == 'True'
                part_data["Default_value"] = row.get('Default_value') or None
                part_data["Value_set_part_ID"] = row.get('Value_set_part_ID') or None
                part_data["Sort_order"] = int(row['Sort_order']) if row.get('Sort_order') else None

                if part_type == 'parentKey':
                    part_data["Ancestor_part_ID"] = row.get('Ancestor_part_ID')

                # Build table_presence
                table_presence = {}
                for present_col in present_columns:
                    table_id = present_col.replace('_present', '')
                    role = row.get(present_col, '').strip()

                    if role:
                        order_col = f"{table_id}_order"
                        required_col = f"{table_id}_required"

                        order = int(row.get(order_col, 999)) if row.get(order_col) else 999
                        required = row.get(required_col) == 'True'

                        table_presence[table_id] = {
                            "role": role,
                            "required": required,
                            "order": order
                        }

                part_data["table_presence"] = table_presence

                # Skip fields with empty table_presence (these are schema metadata fields)
                if not table_presence:
                    print(f"Skipping field with no table presence: {part_id}")
                    continue

            elif part_type == 'valueSetMember':
                part_data["Member_of_set_part_ID"] = row.get('Member_of_set_part_ID')
                part_data["Sort_order"] = int(row['Sort_order']) if row.get('Sort_order') else None

            elif part_type == 'valueSet':
                part_data["Sort_order"] = None

            elif part_type == 'table':
                # Skip the Parts table - it was only for self-documentation in CSV format
                if part_id == 'Parts':
                    print(f"Skipping Parts table (no longer needed)")
                    continue
                part_data["Sort_order"] = None

            parts.append(part_data)

    # Create dictionary structure
    dict_data = {"parts": parts}

    # Validate with Pydantic
    print("Validating with Pydantic...")
    try:
        dictionary = Dictionary.model_validate(dict_data)
        print(f"✓ Validation successful! {len(dictionary.parts)} parts loaded.")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        raise

    # Write to JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(dict_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Dictionary written to {json_path}")

    # Print summary
    from collections import Counter
    type_counts = Counter(part.part_type for part in dictionary.parts)
    print("\nPart type summary:")
    for part_type, count in sorted(type_counts.items()):
        print(f"  {part_type}: {count}")

    # Print table count
    table_count = len([p for p in dictionary.parts if p.part_type == "table"])
    print(f"\nTotal tables: {table_count}")

    # Print value set count
    vs_count = len([p for p in dictionary.parts if p.part_type == "valueSet"])
    print(f"Total value sets: {vs_count}")


if __name__ == "__main__":
    csv_to_json()
