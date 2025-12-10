# The Dictionary: A Self-Documenting Database Schema

## Purpose

The dictionary (stored as `dictionary.json` at the project root) serves as a comprehensive metadata repository that defines every component of your database model. It acts as a single source of truth from which you can generate SQL schemas, documentation, and entity-relationship diagrams.

**Key Principle**: Each unique field concept gets exactly ONE entry in the dictionary, even if that field appears in multiple tables. The `table_presence` object indicates where each field appears and in what role.

The dictionary is self-referential: it contains the definitions needed to describe itself, making it bootstrapped and internally consistent.

## Understanding the Structure

### JSON Format

The dictionary uses a hierarchical JSON structure that eliminates sparse columns. Each part has only the metadata it needs:

```json
{
  "parts": [
    {
      "Part_ID": "Contact_ID",
      "Label": "Contact ID",
      "Description": "Identifier for contacts",
      "Part_type": "key",
      "SQL_data_type": "int",
      "table_presence": {
        "contact": {
          "role": "key",
          "required": true,
          "order": 1
        },
        "project_has_contact": {
          "role": "compositeKeySecond",
          "required": false,
          "order": 2
        }
      }
    }
  ]
}
```

### Core Fields

Every part has these core metadata fields:

- **Part_ID**: Unique identifier for this field/table/value
- **Label**: Human-readable name
- **Description**: Detailed explanation of what this part represents
- **Part_type**: Classification (`table`, `key`, `property`, `compositeKeyFirst`, `compositeKeySecond`, `parentKey`, `valueSet`, `valueSetMember`)
- **Value_set_part_ID**: If this property is constrained by a value set, which set (optional)
- **Member_of_set_part_ID**: If this is a value set member, which set it belongs to (required for valueSetMember)
- **Ancestor_part_ID**: For `parentKey` type, the Part_ID of the ancestor being referenced (enables hierarchical relationships within the same table)
- **SQL_data_type**: SQL data type (e.g., `int`, `nvarchar(100)`, `datetime`) (optional)
- **Is_required**: Whether this field is mandatory (NOT NULL) (optional)
- **Default_value**: Default value for the field (optional)
- **Sort_order**: Display order for documentation/UI (optional)

### Table Presence Object

For fields (keys and properties), the `table_presence` object maps table names to metadata about how the field appears:

```json
"table_presence": {
  "table_name": {
    "role": "key|property|compositeKeyFirst|compositeKeySecond",
    "required": true|false,
    "order": 1
  }
}
```

**Roles**:

- **`key`**: This field is the primary key in this table
- **`compositeKeyFirst`**: First part of a composite primary key
- **`compositeKeySecond`**: Second part of a composite primary key
- **`property`**: This field is a regular column in this table

**Example**: `Equipment_ID` has:

```json
{
  "Part_ID": "Equipment_ID",
  "table_presence": {
    "equipment": {"role": "key", "required": true, "order": 1},
    "metadata": {"role": "property", "required": false, "order": 5},
    "project_has_equipment": {"role": "compositeKeySecond", "required": false, "order": 2}
  }
}
```

## Reading the Dictionary

### Find acceptable values for a field

To determine what values a field can accept, check if it references a valueSet:

```python exec="true" source="above" result="console"
from open_dateaubase.data_model.helpers import DictionaryManager
mgr = DictionaryManager.load("dictionary.json")

# Get the value set for a field
field = mgr._find_part("Site_type")
if field and hasattr(field, 'value_set_part_id'):
    value_set_id = field.value_set_part_id
    print(f"Field 'Site_type' uses value set: {value_set_id}")
else:
    print("Field 'Site_type' has no value set constraint")
```

```python exec="true" source="above" result="console"
from open_dateaubase.data_model.helpers import DictionaryManager
mgr = DictionaryManager.load("dictionary.json")

# Get all valid values for that set
members = mgr.get_value_set_members("Site_type")
for member in members:
    print(f"{member['Part_ID']}: {member['Label']} - {member['Description']}")
```

### Get all columns in a table

To retrieve all columns that appear in a specific table:

```python exec="true" source="above" result="console"
from open_dateaubase.data_model.helpers import DictionaryManager
mgr = DictionaryManager.load("dictionary.json")

# Get all columns in the site table
columns = mgr.get_table_columns("site")
for col in columns:
    print(f"{col['Part_ID']}: {col['Label']} ({col['SQL_data_type']}) - {col['Role']} - Required: {col['Is_required']}")
```

Or to see what role each field plays:

```python exec="true" source="above" result="console"
from open_dateaubase.data_model.helpers import DictionaryManager
mgr = DictionaryManager.load("dictionary.json")

# Show role information for each field in the site table
columns = mgr.get_table_columns("site")
for col in columns:
    print(f"{col['Part_ID']}: {col['Label']} - Role: {col['Role']}")
```

### Find which tables contain a specific field

To see all tables where `Equipment_ID` appears:

```python exec="true" source="above" result="console"
from open_dateaubase.data_model.helpers import DictionaryManager
mgr = DictionaryManager.load("dictionary.json")

# Find all tables where Equipment_ID appears
tables = mgr.get_field_tables("Equipment_ID")
for table_info in tables:
    print(f"Table: {table_info['Table_ID']}, Role: {table_info['Role']}, Required: {table_info['Required']}, Order: {table_info['Order']}")
```

### Find all primary keys in the database

```python exec="true" source="above" result="console"
from open_dateaubase.data_model.helpers import DictionaryManager
mgr = DictionaryManager.load("dictionary.json")

# Get all primary keys
primary_keys = mgr.get_primary_keys()
for pk in primary_keys:
    print(f"{pk['Part_ID']}: {pk['Label']} ({pk['SQL_data_type']}) - Primary in: {pk['Primary_in_tables']}")
```

Or to see just the key names:

```python exec="true" source="above" result="console"
from open_dateaubase.data_model.helpers import DictionaryManager
mgr = DictionaryManager.load("dictionary.json")

# Just the key names
primary_keys = mgr.get_primary_keys()
for pk in primary_keys:
    print(f"{pk['Part_ID']}: {pk['Label']}")
```

### List all tables in the model

```python exec="true" source="above" result="console"
from open_dateaubase.data_model.helpers import DictionaryManager
mgr = DictionaryManager.load("dictionary.json")

# List all tables
tables = mgr.list_tables()
for table_id in tables:
    table = mgr._find_part(table_id)
    print(f"{table_id}: {table.label} - {table.description}")
```

### Find fields that appear in multiple tables

```python exec="true" source="above" result="console"
from open_dateaubase.data_model.helpers import DictionaryManager
mgr = DictionaryManager.load("dictionary.json")

# Find fields that appear in multiple tables
shared_fields = mgr.get_shared_fields()
for field in shared_fields[:10]:  # Show first 10
    print(f"{field['Part_ID']}: {field['Label']} ({field['Part_type']}) - Used in {field['Table_count']} tables")
    for table in field['Tables']:
        print(f"  - {table['Table_ID']}: {table['Role']}")
    print()
```

## Editing the Dictionary

The dictionary should be edited using the `DictionaryManager` helper class, which ensures validation and consistency.

### Adding a New Value Set

```python
from open_dateaubase.data_model.helpers import DictionaryManager

mgr = DictionaryManager.load("dictionary.json")

# Create a new value set
mgr.create_value_set("Status_set", "Status Values", "Valid status values for records")

# Add members to the set
mgr.add_value_set_member("Status_set", "active", "Active", "Record is currently active", order=1)
mgr.add_value_set_member("Status_set", "inactive", "Inactive", "Record is currently inactive", order=2)
mgr.add_value_set_member("Status_set", "pending", "Pending", "Record is pending review", order=3)

# Save the changes
mgr.save()
```

### Adding a New Table

```python
from open_dateaubase.data_model.helpers import DictionaryManager

mgr = DictionaryManager.load("dictionary.json")

# Create the table
mgr.create_table("observation", "Observation", "Environmental observation records")

# Add primary key
mgr.add_field_to_table(
    table_id="observation",
    field_id="Observation_ID",
    label="Observation ID",
    description="Primary key for observations",
    role="key",
    sql_data_type="int",
    required=True,
    order=1
)

# Add regular fields
mgr.add_field_to_table(
    table_id="observation",
    field_id="Observation_date",
    label="Observation Date",
    description="Date when observation was made",
    role="property",
    sql_data_type="datetime",
    required=True,
    order=2
)

mgr.add_field_to_table(
    table_id="observation",
    field_id="Value",
    label="Value",
    description="Observed value",
    role="property",
    sql_data_type="float",
    required=False,
    order=3
)

# Save the changes
mgr.save()
```

### Adding Fields to an Existing Table

The `add_field_to_table()` method handles both new and existing fields automatically:

- **If the field already exists** (like `Site_ID` used in multiple tables), it updates the field's `table_presence` to include this table
- **If the field doesn't exist**, it creates a new field part

```python
from open_dateaubase.data_model.helpers import DictionaryManager

mgr = DictionaryManager.load("dictionary.json")

# Add a foreign key (Site_ID likely already exists in the dictionary)
mgr.add_field_to_table(
    table_id="observation",
    field_id="Site_ID",
    label="Site ID",
    description="Foreign key to site",
    role="property",
    sql_data_type="int",
    required=True,
    order=4
)

# Add a new field with value set constraint
mgr.add_field_to_table(
    table_id="observation",
    field_id="Status",
    label="Status",
    description="Current status of observation",
    role="property",
    sql_data_type="nvarchar(50)",
    required=False,
    value_set_id="Status_set",
    order=5
)

# Add another new field
mgr.add_field_to_table(
    table_id="observation",
    field_id="Notes",
    label="Notes",
    description="Additional notes about observation",
    role="property",
    sql_data_type="nvarchar(500)",
    required=False,
    order=6
)

mgr.save()
```

### Adding a Hierarchical Relationship (Parent Key)

For tables with parent-child relationships within the same table:

```python
from open_dateaubase.data_model.helpers import DictionaryManager

mgr = DictionaryManager.load("dictionary.json")

# Add a parent key for hierarchical structure
mgr.add_parent_key(
    table_id="site",
    parent_key_id="Parent_Site_ID",
    ancestor_key_id="Site_ID",
    label="Parent Site ID",
    description="Reference to parent site in hierarchy",
    sql_data_type="int",
    required=False,
    order=10
)

mgr.save()
```

This creates:

- A new `Parent_Site_ID` field of type `parentKey`
- With `Ancestor_part_ID` pointing to `Site_ID`
- Appearing in the `site` table as a `property`

### Handling Name Collisions

If a non-ID field name appears in multiple tables with different meanings (e.g., `Description`, `City`):

- Create **separate Part_ID entries** with table prefixes
- Examples: `site_City`, `contact_City`, `purpose_Description`, `project_Description`
- Each gets its own part with `table_presence` set for only that table
- Labels can be the same or differentiated: "City", "City", etc.

```python
from open_dateaubase.data_model.helpers import DictionaryManager

mgr = DictionaryManager.load("dictionary.json")

# Add site-specific description
mgr.add_field_to_table(
    table_id="site",
    field_id="site_Description",
    label="Description",
    description="Description of the site",
    role="property",
    sql_data_type="nvarchar(500)",
    required=False,
    order=6
)

# Add project-specific description (different content)
mgr.add_field_to_table(
    table_id="project",
    field_id="project_Description",
    label="Description",
    description="Description of the project",
    role="property",
    sql_data_type="nvarchar(500)",
    required=False,
    order=7
)

mgr.save()
```

**Exception**: ID fields (`*_ID`) always use the same Part_ID across tables and are tracked via `table_presence`.

### Regenerating Documentation and SQL

After editing the dictionary, regenerate all outputs:

```bash
# Regenerate documentation
uv run python scripts/orchestrate_docs.py

# Or regenerate specific components
uv run python scripts/generate_dictionary_reference.py dictionary.json docs/reference
uv run python scripts/generate_erd.py dictionary.json docs/reference
uv run python scripts/generate_sql.py dictionary.json sql_generation_scripts mssql
```

## Naming Conventions

The following naming rules apply:

### Part_IDs

- **Tables**: Singular nouns, lowercase, words separated by underscores
  - Examples: `watershed`, `sampling_point`, `equipment_model`, `weather_condition`

- **Primary Keys**: `[Table_name]_ID` with capitalized first letters
  - Examples: `Watershed_ID`, `Sampling_point_ID`, `Equipment_model_ID`
  - Rule: These appear in multiple tables with the same Part_ID

- **Foreign Keys**: Use the exact same Part_ID as the referenced primary key
  - Example: `site` table references `watershed` via `Watershed_ID`
  - The dictionary shows this with different roles in `table_presence`

- **Regular Fields**: Descriptive names, mixed case with underscores
  - Examples: `Site_name`, `Street_number`, `Latitude_GPS`, `Purchase_date`

- **Table-Prefixed Fields**: When non-ID names collide across tables
  - Format: `tablename_FieldName`
  - Examples: `site_City`, `contact_City`, `purpose_Description`

### Junction Tables (Many-to-Many)

- Format: `[table1]_has_[table2]` where both tables are singular
- Examples: `project_has_equipment`, `project_has_contact`, `equipment_model_has_procedure`
- Primary keys are composite (two `compositeKey*` fields)

### Value Sets and Members

- **Value Sets**: descriptive name + `Set` or `_set` suffix
  - Part_type: `valueSet`
  - Examples: `Part_type_set`, `Site_type_set`, `StatusSet`

- **Members**: short, descriptive identifiers
  - Part_type: `valueSetMember`
  - Member_of_set_part_ID: points to the set
  - Examples: `table`, `key`, `property`, `valueSet`, `valueSetMember`, `active`, `inactive`
