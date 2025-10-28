import csv
import os
from pathlib import Path
from datetime import datetime
from importlib.metadata import version

package_version = version("open-dateaubase")
TARGET_DBS = ["mssql"]

def on_pre_build(config):
    """
    MkDocs hook that runs before the build process.
    Reads Parts_table.csv and generates reference.md
    """
    # Define paths
    project_root = Path(config['config_file_path']).parent
    csv_path = project_root / 'src/dictionary.csv'
    docs_dir = Path(config['docs_dir'])
    output_path = docs_dir / 'reference'
    sql_path = project_root / 'sql_generation_scripts'
    
    # Read and parse CSV
    parts_data = parse_parts_table(csv_path)
    
    # Generate markdown
    image = generate_schema_image(parts_data)
    tables = generate_tables_markdown(parts_data)
    value_sets = generate_value_sets_markdown(parts_data)
    
    # Generate SQL schema(s)
    generate_sql_schemas(parts_data, sql_path, TARGET_DBS)

    # Write to file
    # TODO: Write the schema image to a file in the docs/assets directory
    (output_path / "tables.md").write_text(tables, encoding='utf-8')
    (output_path / "valuesets.md").write_text(value_sets, encoding='utf-8')
    print(f"Generated {output_path}")

    

def generate_sql_schemas(parts_data, path, db_list):
    for target_db in db_list:
        sql_schema = generate_sql_schema(parts_data, target_db=target_db)
        version_str = package_version
        filename = f"v{version_str}_as-designed_{target_db}.sql"
        (path / filename).write_text(sql_schema, encoding='utf-8')
        print(f"Generated SQL schema for {target_db} at {path / filename}")


def generate_schema_image(data):
    return "Schema image generation not yet implemented!"

def parse_parts_table(csv_path):
    """
    Parse the Parts_table.csv into a structured format.
    Returns a dict organized by tables and value sets.

    NEW FORMAT: Uses TableName_present columns instead of Table_part_ID
    """
    data = {
        'tables': {},
        'value_sets': {},
        'metadata': {},
        'id_field_locations': {}  # Track where ID fields appear for FK detection
    }

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        # Read all rows to ensure fieldnames is populated
        rows = list(reader)
        fieldnames = reader.fieldnames or []

        # Find all *_present columns (excluding Parts_present which is self-reference)
        present_columns = [col for col in fieldnames
                          if col.endswith('_present') and col != 'Parts_present']

        # Find all *_order columns for sorting
        order_columns = {col.replace('_order', ''): col
                        for col in fieldnames if col.endswith('_order')}

        for row in rows:
            part_id = row['Part_ID']
            part_type = row['Part_type']

            if part_type == 'table':
                # Skip Parts table self-reference
                if part_id != 'Parts':
                    data['tables'][part_id] = {
                        'label': row['Label'],
                        'description': row['Description'],
                        'fields': []
                    }

            elif part_type in ['key', 'property', 'compositeKeyFirst', 'compositeKeySecond', 'parentKey']:
                # Check all *_present columns to see which tables this field appears in
                for present_col in present_columns:
                    table_id = present_col.replace('_present', '')
                    role = row.get(present_col, '').strip()

                    if role:  # Field appears in this table
                        # Ensure table exists
                        if table_id not in data['tables']:
                            continue

                        # Get sort order for this table
                        order_col = order_columns.get(table_id, '')
                        sort_order = int(row.get(order_col, '999')) if row.get(order_col) else 999

                        # Track ID field locations for FK detection
                        if part_id.endswith('_ID'):
                            if part_id not in data['id_field_locations']:
                                data['id_field_locations'][part_id] = {}
                            data['id_field_locations'][part_id][table_id] = role

                        # For parentKey type, fk_to comes from Ancestor_part_ID
                        fk_to = ''
                        if part_type == 'parentKey':
                            fk_to = row.get('Ancestor_part_ID', '')

                        field_info = {
                            'part_id': part_id,
                            'label': row['Label'],
                            'description': row['Description'],
                            'part_type': role,  # Use role from _present column (key, property, etc.)
                            'sql_data_type': row['SQL_data_type'],
                            'is_required': row['Is_required'] == 'True',
                            'default_value': row['Default_value'],
                            'fk_to': fk_to,  # Set for parentKey, otherwise determined later from ID patterns
                            'value_set': row['Value_set_part_ID'],
                            'sort_order': sort_order
                        }
                        data['tables'][table_id]['fields'].append(field_info)

            elif part_type == 'valueSet':
                data['value_sets'][part_id] = {
                    'label': row['Label'],
                    'description': row['Description'],
                    'members': []
                }

            elif part_type == 'valueSetMember':
                value_set_id = row['Member_of_set_part_ID']
                if value_set_id and value_set_id in data['value_sets']:
                    member_info = {
                        'part_id': part_id,
                        'label': row['Label'],
                        'description': row['Description'],
                        'sort_order': int(row['Sort_order']) if row['Sort_order'] else 999
                    }
                    data['value_sets'][value_set_id]['members'].append(member_info)

    # Derive foreign key relationships from ID field patterns
    # Two cases:
    # 1. An ID field that appears as 'key' in one table and 'property' in others is a FK
    # 2. A field ending in _ID that references another table's primary key (e.g., TestTable_Parent_ID -> TestTable_ID)

    for id_field, locations in data['id_field_locations'].items():
        # Find the table where this is the primary key
        pk_table = None
        for table_id, role in locations.items():
            if role == 'key':
                pk_table = table_id
                break

        if pk_table:
            # Mark all other occurrences as foreign keys
            for table_id, role in locations.items():
                if table_id != pk_table and role == 'property':
                    # Find the field in this table and set fk_to
                    for field in data['tables'][table_id]['fields']:
                        if field['part_id'] == id_field:
                            field['fk_to'] = id_field

    # Also detect FK fields that reference other tables by name pattern
    # E.g., TestTable_Parent_ID should reference TestTable_ID
    for table_id, table_info in data['tables'].items():
        for field in table_info['fields']:
            if field['part_id'].endswith('_ID') and not field['fk_to']:
                # Try to find a matching primary key
                # Extract potential table name from field name
                # E.g., "TestTable_Parent_ID" -> look for "TestTable_ID"
                parts = field['part_id'].rsplit('_', 1)  # Split from right to get [..., 'ID']
                if len(parts) == 2:
                    prefix = parts[0]  # E.g., "TestTable_Parent"
                    # Look for any table whose PK this might reference
                    # Check if prefix ends with a table name
                    for potential_table in data['tables'].keys():
                        if prefix.startswith(potential_table + '_'):
                            # This might be a FK to potential_table
                            target_pk = potential_table + '_ID'
                            if target_pk in data['id_field_locations']:
                                field['fk_to'] = target_pk
                                break

    # Sort fields and members by sort_order
    for table in data['tables'].values():
        table['fields'].sort(key=lambda x: x['sort_order'])

    for value_set in data['value_sets'].values():
        value_set['members'].sort(key=lambda x: x['sort_order'])

    return data


def generate_tables_markdown(data):
    """
    Generate markdown documentation from parsed data.
    """
    md = ["# Database Tables\n"]
    md.append("This documentation is auto-generated from the Parts metadata table.\n")
    
    # Generate table documentation
    md.append("\n## Tables\n")
    
    for table_id, table_info in sorted(data['tables'].items()):
        # Anchor as invisible span, table name as regular heading
        md.append(f'\n<span id="{table_id}"></span>\n')
        md.append(f"### {table_info['label']}\n")
        md.append(f"{table_info['description']}\n")
        
        if table_info['fields']:
            md.append("\n#### Fields\n")
            md.append("| Field | SQL Type | Value Set | Required | Description | Constraints |")
            md.append("|-------|----------|-----------|----------|-------------|-------------|")
            
            for field in table_info['fields']:
                field_name = field['label']
                field_id = field['part_id']
                
                # SQL Type column
                sql_type = field['sql_data_type'] if field['sql_data_type'] else '-'
                if field['part_type'] in ['key', 'compositeKeyFirst', 'compositeKeySecond']:
                    if field['part_type'] == 'key':
                        sql_type += ' **(PK)**' 
                    elif field['part_type'] == "compositeKeyFirst":
                        sql_type += ' **(CK-1)**'
                    elif field['part_type'] == "compositeKeySecond":
                        sql_type += ' **(CK-2)**'
                    else:
                        raise ValueError(f"Found unknown part type: {field['part_type']}. Correct the parts table OR update the documentation generation code.")
                
                # Value Set column - link to the value set definition
                value_set = f"[{field['value_set']}](valuesets.md#{field['value_set']})" if field['value_set'] else '-'
                
                required = '✓' if field['is_required'] else ''
                
                # Anchor the description with the Part_ID
                description = f'<span id="{field_id}"></span>{field["description"]}'
                
                # Build constraints column
                constraints = []
                if field['fk_to']:
                    # Link to the FK target field
                    constraints.append(f"FK → [{field['fk_to']}](#{field['fk_to']})")
                if field['default_value']:
                    constraints.append(f"Default: `{field['default_value']}`")
                
                constraints_str = '<br>'.join(constraints) if constraints else '-'
                
                md.append(f"| {field_name} | {sql_type} | {value_set} | {required} | {description} | {constraints_str} |")
    
    return '\n'.join(md)
    

def generate_value_sets_markdown(data):
    """
    Generate value set documentation with proper anchoring.
    """
    md = ["# Value Sets\n"]
    md.append("Controlled vocabularies used throughout the database.\n")
    
    if data['value_sets']:    
        for value_set_id, value_set_info in sorted(data['value_sets'].items()):
            # Anchor as invisible span, value set name as regular heading
            md.append(f'\n<span id="{value_set_id}"></span>\n')
            md.append(f"## {value_set_info['label']}\n")
            md.append(f"{value_set_info['description']}\n")
            
            if value_set_info['members']:
                md.append("\n| Value | Description |")
                md.append("|-------|-------------|")
                
                for member in value_set_info['members']:
                    member_id = member['part_id']
                    # Anchor each member with its Part_ID
                    md.append(f"| <span id=\"{member_id}\"></span>`{member_id}` | {member['description']} |")
    else:
        md.append("No value sets currently appear in the dictionary.")
    
    return '\n'.join(md)

def generate_sql_schema(data, target_db='mssql', include_timestamp=True):
    """
    Generate SQL CREATE statements from parsed metadata.

    Args:
        data: Parsed parts table data
        target_db: Target database flavor ('mssql', 'postgres', 'mysql' - future)
        include_timestamp: Whether to include generation timestamp (default: True)

    Returns:
        SQL DDL as a string

    Raises:
        ValueError: If circular foreign key dependencies detected
    """
    # Validate no circular FK dependencies
    validate_no_circular_fks(data)

    sql = ["-- Auto-generated SQL schema from Parts metadata table"]
    sql.append(f"-- Target database: {target_db.upper()}")
    if include_timestamp:
        sql.append(f"-- Generated: {datetime.now().isoformat()}")
    sql.append("\n")
    
    # Get DB-specific config
    db_config = get_db_config(target_db)
    
    # First pass: Create all tables without foreign keys
    for table_id, table_info in sorted(data['tables'].items()):
        sql.append(f"\n-- {table_info['description']}")
        sql.append(f"CREATE TABLE {db_config['quote'](table_id)} (")
        
        field_definitions = []
        pk_fields = []
        
        for field in table_info['fields']:
            field_def = generate_field_definition(field, data, db_config)
            field_definitions.append(field_def)
            
            # Track primary key fields
            if field['part_type'] in ['key', 'compositeKeyFirst', 'compositeKeySecond']:
                field_name = extract_field_name(field['part_id'])
                pk_fields.append(f"{db_config['quote'](field_name)}")
        
        # Add primary key constraint
        if pk_fields:
            pk_name = "PK_" + table_id
            pk_constraint = f"    CONSTRAINT {db_config['quote'](pk_name)} PRIMARY KEY ({', '.join(pk_fields)})"
            field_definitions.append(pk_constraint)
        
        sql.append(",\n".join(field_definitions))
        sql.append(");\n")
    
    # Second pass: Add foreign key constraints
    sql.append("\n-- Foreign Key Constraints\n")
    for table_id, table_info in sorted(data['tables'].items()):
        for field in table_info['fields']:
            if field['fk_to']:
                fk_sql = generate_foreign_key_constraint(table_id, field, db_config)
                if fk_sql:
                    sql.append(fk_sql)
    
    return '\n'.join(sql)


def get_db_config(target_db):
    """
    Get database-specific configuration.
    
    Args:
        target_db: Database flavor string
        
    Returns:
        Dict with DB-specific settings
    """
    configs = {
        'mssql': {
            'quote_char': '[',
            'quote_char_end': ']',
            'type_mappings': {
                'nvarchar': 'nvarchar',
                'ntext': 'nvarchar(max)',  # ntext deprecated in modern MSSQL
                'int': 'int',
                'float': 'float',
                'real': 'real',
                'numeric': 'numeric',
                'bit': 'bit'
            },
            'supports_check_constraints': True,
            'supports_deferred_constraints': False
        },
        # Future: postgres, mysql, sqlite configs
    }
    
    if target_db not in configs:
        raise ValueError(f"Unsupported database: {target_db}. Supported: {list(configs.keys())}")
    
    config = configs[target_db]
    
    # Add convenience method for quoting identifiers
    if config['quote_char_end']:
        config['quote'] = lambda name: f"{config['quote_char']}{name}{config['quote_char_end']}"
    else:
        config['quote'] = lambda name: f"{config['quote_char']}{name}{config['quote_char']}"
    
    return config


def extract_field_name(part_id):
    """
    Extract field name from Part_ID.

    NEW FORMAT handling:
    - ID fields (e.g., 'Equipment_ID', 'Project_ID'): Use as-is (these are the actual SQL field names)
    - Table-prefixed fields (e.g., 'site_City', 'purpose_Description'): Remove table prefix
    - Non-prefixed fields: Use as-is

    Args:
        part_id: Part_ID from dictionary

    Returns:
        Field name to use in SQL
    """
    # ID fields are used as-is in SQL
    if part_id.endswith('_ID'):
        return part_id

    # Table-prefixed non-ID fields: remove prefix
    # Format is lowercase_table_MixedCaseField (e.g., 'site_City', 'contact_City')
    if '_' in part_id:
        # Check if first part looks like a table name (lowercase)
        parts = part_id.split('_', 1)
        if len(parts) == 2 and parts[0].islower():
            # This is likely a table-prefixed field, remove prefix
            return parts[1]

    # Otherwise use as-is
    return part_id


def validate_no_circular_fks(data):
    """
    Check for circular foreign key dependencies between tables.
    
    Args:
        data: Parsed parts table data
        
    Raises:
        ValueError: If circular FK dependencies found
    """
    # Build adjacency list of FK relationships
    fk_graph = {table_id: set() for table_id in data['tables']}
    
    for table_id, table_info in data['tables'].items():
        for field in table_info['fields']:
            if field['fk_to'] and '_' in field['fk_to']:
                target_table = field['fk_to'].split('_', 1)[0]
                if target_table in fk_graph:
                    fk_graph[table_id].add(target_table)
    
    # Check for bidirectional relationships (A->B and B->A)
    circular_deps = []
    for table_a, targets in fk_graph.items():
        for table_b in targets:
            if table_b == table_a:
                # self-referential FKs are allowed
                continue
            if table_a in fk_graph.get(table_b, set()):
                # Found circular dependency
                pair = tuple(sorted([table_a, table_b]))
                if pair not in circular_deps:
                    circular_deps.append(pair)
    
    if circular_deps:
        error_msg = "Circular foreign key dependencies detected:\n"
        for table_a, table_b in circular_deps:
            error_msg += f"  - {table_a} ↔ {table_b}\n"
        error_msg += "\nEach pair of tables has FKs pointing to each other, which creates ambiguity in table creation order."
        raise ValueError(error_msg)


def generate_field_definition(field, data, db_config):
    """
    Generate SQL field definition with constraints.
    
    Args:
        field: Field metadata dict
        data: Full parsed data (for value set lookups)
        db_config: Database-specific configuration
        
    Returns:
        SQL field definition string
    """
    field_name = extract_field_name(field['part_id'])
    
    quote = db_config['quote']
    
    parts = [f"    {quote(field_name)}"]
    
    # Data type with mapping
    sql_type = field['sql_data_type'] if field['sql_data_type'] else 'nvarchar(255)'
    # Apply type mapping for target DB
    base_type = sql_type.split('(')[0]  # Extract base type (e.g., 'nvarchar' from 'nvarchar(255)')
    if base_type in db_config['type_mappings']:
        # Preserve parameters if they exist
        if '(' in sql_type:
            params = sql_type[sql_type.index('('):]
            sql_type = db_config['type_mappings'][base_type].split('(')[0] + params
        else:
            sql_type = db_config['type_mappings'][base_type]
    
    parts.append(sql_type)
    
    # NULL constraint
    if field['is_required']:
        parts.append("NOT NULL")
    else:
        parts.append("NULL")
    
    # Default value
    if field['default_value']:
        default_val = field['default_value']
        # Handle boolean defaults
        if default_val in ['True', 'False']:
            default_val = '1' if default_val == 'True' else '0'
        # Handle numeric vs string defaults
        if field['sql_data_type'] and field['sql_data_type'].split('(')[0] in ['int', 'float', 'real', 'numeric', 'bit']:
            parts.append(f"DEFAULT {default_val}")
        else:
            parts.append(f"DEFAULT '{default_val}'")
    
    # Note: Value set CHECK constraints removed per requirement #3
    # Future: could add back conditionally based on target_db config
    
    return ' '.join(parts)


def generate_foreign_key_constraint(table_id, field, db_config):
    """
    Generate ALTER TABLE statement for foreign key.

    NEW FORMAT: fk_to is the Part_ID of the target field (e.g., 'TestTable_ID')
    We need to find which table has this field as a primary key.

    Args:
        table_id: Source table ID
        field: Field metadata with FK reference
        db_config: Database-specific configuration

    Returns:
        SQL ALTER TABLE statement or None
    """
    if not field['fk_to']:
        return None

    # fk_to is the Part_ID of the target (e.g., 'TestTable_ID')
    # For ID fields, this is the actual field name
    # We need to determine the target table from the naming
    fk_target = field['fk_to']
    source_field = extract_field_name(field['part_id'])

    # For ID fields like 'TestTable_ID', the target table is the part before '_ID'
    if fk_target.endswith('_ID'):
        target_field = fk_target  # e.g., 'TestTable_ID'
        # Extract table name (everything before '_ID')
        target_table = fk_target[:-3]  # Remove '_ID' to get 'TestTable'
    else:
        # Non-ID FK (shouldn't happen in new format, but fallback)
        return None

    quote = db_config['quote']
    constraint_name = f"FK_{table_id}_{source_field}"

    sql = f"""ALTER TABLE {quote(table_id)}
    ADD CONSTRAINT {quote(constraint_name)}
    FOREIGN KEY ({quote(source_field)})
    REFERENCES {quote(target_table)} ({quote(target_field)});
"""

    return sql