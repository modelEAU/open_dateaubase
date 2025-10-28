# The Parts Table: A Self-Documenting Database Schema

## Purpose

The Parts table (stored as `dictionary.csv`) serves as a comprehensive metadata repository that defines every component of your database model. It acts as a single source of truth from which you can generate SQL schemas, documentation, and entity-relationship diagrams.

**Key Principle**: Each unique field concept gets exactly ONE row in the dictionary, even if that field appears in multiple tables. The `TableName_present` columns indicate where each field appears and in what role.

The Parts table is self-referential: it contains the definitions needed to describe itself, making it bootstrapped and internally consistent.

## Understanding the Structure

### Core Columns

Every part has these core metadata columns:

- **Part_ID**: Unique identifier for this field/table/value
- **Label**: Human-readable name
- **Description**: Detailed explanation of what this part represents
- **Part_type**: Classification (`table`, `key`, `property`, `compositeKeyFirst`, `compositeKeySecond`, `parentKey`, `valueSet`, `valueSetMember`)
- **Value_set_part_ID**: If this property is constrained by a value set, which set
- **Member_of_set_part_ID**: If this is a value set member, which set it belongs to
- **Ancestor_part_ID**: For `parentKey` type, the Part_ID of the ancestor being referenced (enables hierarchical relationships within the same table)
- **SQL_data_type**: SQL data type (e.g., `int`, `nvarchar(100)`, `ntext`)
- **Is_required**: Whether this field is mandatory (NOT NULL)
- **Default_value**: Default value for the field
- **Sort_order**: Display order for documentation/UI

### Table Presence Columns

For each table in the database, there are `TableName_present` columns that indicate if and how a field appears in that table:

- **`key`**: This field is the primary key in this table
- **`compositeKeyFirst`**: First part of a composite primary key
- **`compositeKeySecond`**: Second part of a composite primary key
- **`property`**: This field is a regular column in this table
- **(empty)**: This field does not appear in this table

**Example**: `Equipment_ID` has a single row with:

- `equipment_present = key` (primary key in equipment table)
- `metadata_present = property` (foreign key in metadata table)
- `project_has_equipment_present = compositeKeySecond` (part of composite key)

### Table Metadata Columns

For tracking additional metadata, each table also has:

- **TableName_required**: Whether this part is required in that table
- **TableName_order**: Display order of this part in that table

## Reading the Dictionary

### Find acceptable values for a field

To determine what values a field can accept, check if it references a valueSet:

```sql
-- Get the valueSet for a field
SELECT Value_set_part_ID
FROM Parts
WHERE Part_ID = 'Site_type';
```

```sql
-- Get all valid values for that set
SELECT Part_ID, Label, Description
FROM Parts
WHERE Member_of_set_part_ID = 'Site_type_set'
ORDER BY Sort_order;
```

### Get all columns in a table

To retrieve all columns that appear in a specific table:

```sql
SELECT Part_ID, Label, SQL_data_type, Is_required
FROM Parts
WHERE site_present != ''  -- Field appears in site table
  AND Part_type IN ('key', 'property', 'compositeKeyFirst', 'compositeKeySecond')
ORDER BY site_order;
```

Or to see what role each field plays:

```sql
SELECT Part_ID, Label, site_present AS role_in_site
FROM Parts
WHERE site_present != ''
ORDER BY site_order;
```

### Find which tables contain a specific field

To see all tables where `Equipment_ID` appears:

```sql
SELECT Part_ID,
  CASE WHEN equipment_present != '' THEN 'equipment (' || equipment_present || ')' END,
  CASE WHEN metadata_present != '' THEN 'metadata (' || metadata_present || ')' END,
  CASE WHEN project_has_equipment_present != '' THEN 'project_has_equipment (' || project_has_equipment_present || ')' END
FROM Parts
WHERE Part_ID = 'Equipment_ID';
```

### Find all primary keys in the database

```sql
SELECT Part_ID, Label
FROM Parts
WHERE Part_type = 'key'
ORDER BY Part_ID;
```

Or to see which table each key belongs to (checking all `_present` columns):

```sql
SELECT Part_ID, Label, SQL_data_type
FROM Parts
WHERE Part_type = 'key'
  AND Parts_present IS NULL  -- Exclude Parts table metadata fields
ORDER BY Part_ID;
```

### List all tables in the model

```sql
SELECT Part_ID, Label, Description
FROM Parts
WHERE Part_type = 'table'
ORDER BY Label;
```

### Find fields that appear in multiple tables

```sql
-- This query identifies fields (especially ID fields) used across tables
-- by counting non-empty _present columns
SELECT Part_ID, Label, Part_type
FROM Parts
WHERE Part_type IN ('key', 'property')
  AND (
    -- Count number of tables where this field appears
    -- (You'd need to list all _present columns)
    (equipment_present != '') +
    (metadata_present != '') +
    (project_present != '') -- etc.
  ) > 1;
```

## Editing the Dictionary

### Adding a New Field to an Existing Table

1. Check if a field with this name already exists (search for Part_ID)
2. If it exists and is an ID field, just update the appropriate `TableName_present` column
3. If it doesn't exist or is a different concept, add a new row:
   - **Part_ID**: Field name (or `TableName_FieldName` if name collision)
   - **Label**: Human-readable label
   - **Description**: What the field represents
   - **Part_type**: Usually `property`, `key` for primary keys
   - **SQL_data_type**: The SQL data type
   - **Is_required**: TRUE if NOT NULL
   - **Sort_order**: Position in table definition
   - **TableName_present**: Set to `key`, `property`, `compositeKeyFirst`, or `compositeKeySecond`

### Adding a New Table

1. Add a table definition row:
   - **Part_ID**: Table name (lowercase with underscores)
   - **Label**: Title case version
   - **Part_type**: `table`

2. Add the primary key field (or composite key fields)

3. Add all property fields, setting `TableName_present` for each

4. Add `TableName_present`, `TableName_required`, and `TableName_order` columns to the Parts table metadata

### Handling Name Collisions

If a non-ID field name appears in multiple tables (e.g., `Description`, `City`):

- Create **separate Part_ID entries** with table prefixes
- Examples: `site_City`, `contact_City`, `purpose_Description`, `project_Description`
- Each gets its own row with `TableName_present` set for only that table
- Labels should include both parts: "Site City", "Contact City", etc.

**Exception**: ID fields (`*_ID`) always use the same Part_ID across tables, with multiple `_present` columns filled in.

### Handling Hierarchical Relationships (parentKey)

When a table has a hierarchical structure (parent-child within the same table):

- Create a **new Part_ID** for the parent reference (don't reuse the table's primary key Part_ID)
- Set **Part_type** to `parentKey`
- Set **Ancestor_part_ID** to the Part_ID of the field being referenced (usually the table's primary key)
- The field appears in the table as a regular `property` in the `TableName_present` column

**Example**: For a hierarchical `site` table where sites can have parent sites:

```csv
Part_ID,Part_type,Ancestor_part_ID,site_present,...
Site_ID,key,,key,...
Parent_site_ID,parentKey,Site_ID,property,...
```

This models:

- `Site_ID` is the primary key
- `Parent_site_ID` is a semantically different field that references `Site_ID`
- The hierarchical relationship is explicit via `Ancestor_part_ID`

### Regenerating from SQL Schema

If you update the SQL schema file, you can regenerate the dictionary:

```bash
uv run python generate_dictionary.py
```

This will create `dictionary_new.csv`. Review it and replace `dictionary.csv` if correct.

## Naming Conventions

The following naming rules apply:

### Part_IDs

- **Tables**: Singular nouns, lowercase, words separated by underscores
  - Examples: `watershed`, `sampling_points`, `equipment_model`, `weather_condition`

- **Primary Keys**: `[Table_name]_ID` with capitalized first letters
  - Examples: `Watershed_ID`, `Sampling_point_ID`, `Equipment_model_ID`
  - Rule: These appear in multiple tables with the same Part_ID

- **Foreign Keys**: Use the exact same Part_ID as the referenced primary key
  - Example: `site` table references `watershed` via `Watershed_ID`
  - The dictionary shows this with `site_present = property` and `watershed_present = key`

- **Regular Fields**: Descriptive names, mixed case with underscores
  - Examples: `Site_name`, `Street_number`, `Latitude_GPS`, `Purchase_date`

- **Table-Prefixed Fields**: When non-ID names collide across tables
  - Format: `tablename_FieldName`
  - Examples: `site_City`, `contact_City`, `purpose_Description`

### Junction Tables (Many-to-Many)

- Format: `[table1]_has_[table2]` where both tables are singular
- Examples: `project_has_equipment`, `project_has_contact`, `equipment_model_has_procedures`
- Primary keys are composite (two `compositeKey*` fields)

### Value Sets and Members

- **Value Sets**: descriptive name + `_set` suffix
  - Part_type: `valueSet`
  - Examples: `Part_type_set`, `Site_type_set`

- **Members**: short, descriptive identifiers
  - Part_type: `valueSetMember`
  - Member_of_set_part_ID: points to the set
  - Examples: `table`, `key`, `property`, `valueSet`, `valueSetMember`

## Practical Examples

### Example 1: Understanding Equipment_ID

The `Equipment_ID` field has ONE row in the dictionary:

| Column | Value |
|--------|-------|
| Part_ID | Equipment_ID |
| Label | Equipment ID |
| Description | Identifier for equipment, also used in 2 other table(s) |
| Part_type | key |
| SQL_data_type | int |
| equipment_present | key |
| metadata_present | property |
| project_has_equipment_present | compositeKeySecond |
| *(all other _present columns)* | *(empty)* |

This tells us:

- Equipment_ID is a primary key (`Part_type = key`)
- It's the primary key in the `equipment` table
- It appears as a foreign key in `metadata`
- It's part of a composite key in `project_has_equipment`

### Example 2: Understanding Description Fields

Because `Description` appears in multiple tables with different meanings, there are MULTIPLE rows:

| Part_ID | Label | purpose_present | project_present | site_present |
|---------|-------|-----------------|-----------------|--------------|
| Description | Description | | | |
| purpose_Description | Purpose Description | property | | |
| project_Description | Project Description | | property | |
| site_Description | Site Description | | | property |

Note: The plain `Description` is the Parts table's own Description field (with `Parts_present = property`).

### Example 3: Adding a New Field

To add a `Latitude` field to the `site` table:

1. Check if `Latitude` already exists (it doesn't, but `Latitude_GPS` does in `sampling_points`)
2. Since the names are different, add a new row:

   ```csv
   Part_ID,Label,Description,Part_type,SQL_data_type,Is_required,Sort_order,site_present
   Latitude,Latitude,Latitude coordinate of site,property,real,False,15,property
   ```

3. Save and validate the dictionary

### Example 4: Adding an Existing Field to a New Table

To add `Contact_ID` to a new `project_contact_history` table:

1. Find the existing `Contact_ID` row
2. Add a new column `project_contact_history_present`
3. Set the value to `property` (or `compositeKeyFirst`/`compositeKeySecond` if it's part of the primary key)
4. No need to create a new row—just update the existing one!

## Tips for Working with the Dictionary

1. **Always search before adding**: Use your editor's find function to check if a Part_ID exists
2. **ID fields are shared**: If you see `_ID` at the end, it's likely used across multiple tables
3. **Use table prefixes for collisions**: When the same field name means different things in different tables
4. **Validate after changes**: Run `validate_dictionary.py` to check for duplicates and issues
5. **Keep it synchronized**: If you edit the SQL schema, regenerate the dictionary and merge changes carefully
6. **Document value sets**: When adding enumerations, create both the valueSet and all valueSetMembers

## Self-Reference: The Parts Table Describes Itself

The dictionary includes rows that describe its own structure. For example:

- `Part_ID` (the field) has `Parts_present = key`
- `Label` has `Parts_present = property`
- `equipment_present` (one of the many `_present` columns) has `Parts_present = property`

This self-referential structure means the dictionary is "bootstrapped"—it fully describes itself using its own format.
