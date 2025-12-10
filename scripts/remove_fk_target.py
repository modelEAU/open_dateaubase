#!/usr/bin/env python3
"""
Script to remove redundant fk_target_part_id fields from dictionary.json.
"""

import json
from pathlib import Path


def remove_fk_target_part_id():
    """Remove fk_target_part_id from all table_presence objects in dictionary.json."""

    dict_path = Path("src/dictionary.json")

    # Load the dictionary
    with open(dict_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Remove fk_target_part_id from all table_presence objects
    removed_count = 0
    for part in data["parts"]:
        if "table_presence" in part:
            for table_name, presence in part["table_presence"].items():
                if "fk_target_part_id" in presence:
                    del presence["fk_target_part_id"]
                    removed_count += 1

    # Save the updated dictionary
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Removed {removed_count} fk_target_part_id fields from dictionary.json")
    return removed_count


if __name__ == "__main__":
    remove_fk_target_part_id()
