# Entity Relationship Diagram (ERD)

This interactive diagram shows all tables, views, and their relationships in datEAUbase schema.

## Interactive ERD

The interactive version allows you to:
- 🖱️ **Drag tables/views** to rearrange layout
- 🔍 **Zoom in/out** for better visibility
- 📐 **Auto-layout** to reorganize tables automatically
- 💾 **Export** diagram as PNG

<iframe src="../../assets/erd_interactive.html" width="100%" height="800px" frameborder="0" style="border: 2px solid #e2e8f0; border-radius: 8px;"></iframe>

[Open in new window](../assets/erd_interactive.html){: target="_blank" .md-button .md-button--primary}

## Legend

### Entity Types

| Marker | Description |
|--------|-------------|
| **Table** | Physical database table with primary keys, foreign keys, and properties |
| **View** | Virtual table defined by a SQL query (shown with distinct styling) |

### Field Markers
- **PK** badge: Primary Key - Unique identifier for each record
- **FK** badge: Foreign Key - Reference to another table's primary key
- **\*** Required field (NOT NULL)

### Relationship Notation
Relationships use standard crow's foot notation:
- **Single line (|)**: "One" side of relationship
- **Crow's foot (⟨)**: "Many" side of relationship

**Relationship Types:**
- **One-to-One**: Single line on both ends (e.g., watershed ↔ hydrological_characteristics)
- **One-to-Many**: Crow's foot on child side, single line on parent (e.g., site ↔ sampling_points)
- **Many-to-Many**: Crow's foot on both ends (via junction tables like project_has_contact)

## Statistics

The current schema contains:
- **23** tables
- **0** views
- **27** relationships
