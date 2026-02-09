# Database Views

Virtual tables defined by SQL queries.

No views currently appear in dictionary.

---

## Adding Views to the Dictionary

Views are defined using two `Part_type` values: `view` for the view definition itself, and `viewColumn` for each column in the view.

### Step 1: Identify Source Tables and Fields

Determine which tables and fields your view needs. For example, to create a view linking metadata records to parameter names and equipment identifiers:

```python exec="true" source="above" result="console"
from open_dateaubase.data_model.helpers import DictionaryManager

mgr = DictionaryManager.load("src/open_dateaubase/dictionary.json")

# Find the fields you need
print("=== Metadata table fields ===")
cols = mgr.get_table_columns("metadata")
for col in cols:
    print(f"{col['Part_ID']}: {col['Label']}")

print("\n=== Parameter table fields ===")
cols = mgr.get_table_columns("parameter")
for col in cols:
    print(f"{col['Part_ID']}: {col['Label']}")

print("\n=== Equipment table fields ===")
cols = mgr.get_table_columns("equipment")
for col in cols:
    print(f"{col['Part_ID']}: {col['Label']}")
```

### Step 2: Design the SQL View Definition

Write the SQL SELECT statement that defines your view. The view should join tables and select the desired columns. For example:

```sql
SELECT m.Metadata_ID, p.Parameter, e.Equipment_identifier
FROM metadata m
LEFT JOIN parameter p ON m.Parameter_ID = p.Parameter_ID
LEFT JOIN equipment e ON m.Equipment_ID = e.Equipment_ID
```

### Step 3: Add View Parts to the Dictionary

Add the view and its columns to `src/open_dateaubase/dictionary.json`:

```json
{
  "Part_ID": "metadata_parameter_equipment_view",
  "Label": "Metadata Parameter Equipment View",
  "Description": "View showing metadata records with linked parameter names and equipment identifiers",
  "Part_type": "view",
  "View_definition": "SELECT m.Metadata_ID, p.Parameter, e.Equipment_identifier FROM metadata m LEFT JOIN parameter p ON m.Parameter_ID = p.Parameter_ID LEFT JOIN equipment e ON m.Equipment_ID = e.Equipment_ID"
},
{
  "Part_ID": "metadata_parameter_equipment_view_Metadata_ID",
  "Label": "Metadata ID",
  "Description": "Unique identifier for the metadata record",
  "Part_type": "viewColumn",
  "Source_field_part_ID": "Metadata_ID",
  "SQL_data_type": "int",
  "view_presence": {
    "metadata_parameter_equipment_view": {
      "order": 1
    }
  }
},
{
  "Part_ID": "metadata_parameter_equipment_view_Parameter",
  "Label": "Parameter",
  "Description": "Name of the parameter from the parameter table",
  "Part_type": "viewColumn",
  "Source_field_part_ID": "Parameter",
  "SQL_data_type": "nvarchar(255)",
  "view_presence": {
    "metadata_parameter_equipment_view": {
      "order": 2
    }
  }
},
{
  "Part_ID": "metadata_parameter_equipment_view_Equipment",
  "Label": "Equipment Identifier",
  "Description": "Identifier of the equipment from the equipment table",
  "Part_type": "viewColumn",
  "Source_field_part_ID": "Equipment_identifier",
  "SQL_data_type": "nvarchar(255)",
  "view_presence": {
    "metadata_parameter_equipment_view": {
      "order": 3
    }
  }
}
```

### View Part Fields

For `view` type parts:

| Field | Description |
|-------|-------------|
| **Part_ID** | Unique identifier for the view (lowercase with underscores) |
| **Label** | Human-readable name |
| **Description** | Detailed explanation of what the view shows |
| **Part_type** | Must be `view` |
| **View_definition** | The SQL SELECT statement defining the view |

### ViewColumn Part Fields

For `viewColumn` type parts:

| Field | Description |
|-------|-------------|
| **Part_ID** | Unique identifier for the view column |
| **Label** | Human-readable column name |
| **Description** | Description of what this column represents |
| **Part_type** | Must be `viewColumn` |
| **Source_field_part_ID** | The Part_ID of the source field this column derives from |
| **SQL_data_type** | SQL data type (e.g., `int`, `nvarchar(255)`) |
| **view_presence** | Object mapping view name to display order |

### Regenerate Outputs

After adding views, regenerate the documentation:

```bash
uv run python scripts/orchestrate_docs.py
```

This generates:
- `docs/reference/views.md` with view documentation and column listings
- `docs/assets/erd_interactive.html` with views rendered in the ERD (distinct blue styling)
- SQL schemas with `CREATE VIEW` statements
