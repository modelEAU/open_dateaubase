"""
ERD (Entity-Relationship Diagram) generator for datEAUbase.

This module reads the dictionary.json and generates an interactive
browser-based ERD diagram using JointJS.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json
from dataclasses import dataclass, asdict


@dataclass
class ERDField:
    """Represents a field in a table for ERD visualization."""
    name: str
    sql_type: str
    is_pk: bool = False
    is_fk: bool = False
    is_required: bool = False
    fk_target: Optional[str] = None  # Format: "table_name.field_name"
    description: Optional[str] = None


@dataclass
class ERDTable:
    """Represents a table for ERD visualization."""
    id: str
    label: str
    description: str
    fields: List[ERDField]


@dataclass
class ERDRelationship:
    """Represents a foreign key relationship from child (FK) to parent (PK)."""
    from_table: str
    to_table: str
    from_field: str
    to_field: str
    # TODO: Add cardinality information in the future (one-to-one, one-to-many, many-to-many)
    # This could be inferred from field.is_required and composite key patterns
    relationship_type: str = "many-to-one"  # Placeholder for future cardinality implementation


def generate_erd_data(parts_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform parsed dictionary data into ERD-friendly format.
    
    Args:
        parts_data: Parsed data from parse_parts_json() in generate_docs.py
        
    Returns:
        Dict with 'tables' and 'relationships' for ERD rendering
    """
    tables = []
    relationships = []
    
    # Process each table
    for table_id, table_info in parts_data['tables'].items():
        fields = []
        
        for field in table_info['fields']:
            is_pk = field['part_type'] in ['key', 'compositeKeyFirst', 'compositeKeySecond']
            is_fk = bool(field.get('fk_to'))
            
            fk_target = None
            if is_fk and field['fk_to']:
                # Extract target table from FK field (e.g., "Contact_ID" -> "contact")
                fk_field = field['fk_to']
                if fk_field.endswith('_ID'):
                    # Convert to lowercase to match table_id format
                    target_table = fk_field[:-3].lower()
                    fk_target = f"{target_table}.{fk_field}"
            
            erd_field = ERDField(
                name=field['label'],
                sql_type=field['sql_data_type'] or 'unknown',
                is_pk=is_pk,
                is_fk=is_fk,
                is_required=field['is_required'],
                fk_target=fk_target,
                description=field['description']
            )
            fields.append(erd_field)
        
        erd_table = ERDTable(
            id=table_id,
            label=table_info['label'],
            description=table_info['description'],
            fields=fields
        )
        tables.append(erd_table)
    
    # Build a mapping of PK field IDs to their primary tables
    # A field is a PRIMARY KEY in a table if part_type is 'key' (not compositeKeyFirst/Second)
    # Composite keys in junction tables should NOT be treated as the primary definition
    pk_id_to_table = {}
    for tid, tinfo in parts_data['tables'].items():
        for f in tinfo['fields']:
            # Only consider 'key' as the primary definition of where this field is a PK
            # compositeKeyFirst/Second means it's part of a composite key in a junction table
            if f['part_type'] == 'key':
                pk_field_id = f['part_id']
                # Store the table where this field is the primary key
                pk_id_to_table[pk_field_id] = (tid, f['label'])

    # Extract relationships from foreign keys
    # A relationship exists when a field is:
    #  - A property (FK) in the source table (indicated by fk_to being set)
    #  - A primary key in the target table (part_type='key')
    for table_id, table_info in parts_data['tables'].items():
        for field in table_info['fields']:
            if field.get('fk_to'):
                # fk_to contains the target field part_id (e.g., "Equipment_model_ID")
                target_field_id = field['fk_to']

                # Look up which table has this field as its primary key
                target_info = pk_id_to_table.get(target_field_id)

                # Only create a relationship if we found a table with this as a primary key
                if target_info:
                    target_table, target_pk_label = target_info
                    if target_table in parts_data['tables']:
                        # Use explicit relationship_type from field metadata
                        rel_type = field.get('relationship_type', 'one-to-many')

                        relationship = ERDRelationship(
                            from_table=table_id,
                            to_table=target_table,
                            from_field=field['label'],
                            to_field=target_pk_label,
                            relationship_type=rel_type
                        )
                        relationships.append(relationship)
    
    return {
        'tables': [asdict(t) for t in tables],
        'relationships': [asdict(r) for r in relationships]
    }


def generate_erd_html(erd_data: Dict[str, Any], output_path: Path, library: str = "jointjs") -> None:
    """
    Generate standalone HTML file with interactive ERD using JointJS.

    Args:
        erd_data: ERD data from generate_erd_data()
        output_path: Path to write HTML file
        library: Deprecated parameter, kept for backward compatibility. Only 'jointjs' is supported.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if library != "jointjs":
        raise ValueError(f"Unsupported library. Only 'jointjs' library is supported. Got: {library}")

    html_content = _generate_jointjs_html(erd_data)
    output_path.write_text(html_content, encoding='utf-8')


def _generate_jointjs_html(erd_data: Dict[str, Any]) -> str:
    """Generate HTML using JointJS library with custom HTML elements (Lucid-like)."""
    
    # Serialize ERD data as JSON for embedding
    erd_json = json.dumps(erd_data, indent=2)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>datEAUbase ERD</title>
    
    <!-- JointJS and dependencies -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/lodash.js/4.17.21/lodash.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/backbone.js/1.4.1/backbone-min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jointjs/3.7.1/joint.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/dagre/0.8.5/dagre.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/graphlib/2.1.8/graphlib.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    
    <!-- Styling -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jointjs/3.7.1/joint.min.css" />

    <style>
        :root {{
            --bg-color: #f0f2f5;
            --table-bg: #ffffff;
            --table-border: #e2e8f0;
            --header-bg: #f8fafc;
            --header-text: #1e293b;
            --text-primary: #334155;
            --text-secondary: #64748b;
            --accent-color: #3b82f6;
            --pk-color: #eab308;
            --fk-color: #8b5cf6;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            margin: 0;
            overflow: hidden;
            display: flex;
            height: 100vh;
        }}

        #paper {{
            flex-grow: 1;
            overflow: hidden;
            background-image: radial-gradient(#cbd5e1 1px, transparent 1px);
            background-size: 20px 20px;
        }}

        /* --- Custom HTML Element Styles --- */
        .html-element {{
            position: absolute;
            background: var(--table-bg);
            border-radius: 8px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border: 1px solid var(--table-border);
            pointer-events: auto; 
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: box-shadow 0.2s ease; /* transition removed for transform to avoid lag during drag */
            transform-origin: 0 0;
            z-index: 100 !important; /* Ensure it floats above SVG */
        }}

        /* Add cursor styles */
        .table-header {{
            cursor: move; /* Indicate draggable */
        }}
        .info-btn {{
            cursor: pointer;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .info-btn:hover {{
            background-color: #e2e8f0;
        }}
        .html-element.selected {{
            box-shadow: 0 0 0 2px var(--accent-color), 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            z-index: 100 !important;
        }}

        .table-header {{
            background: var(--header-bg);
            padding: 8px 12px;
            border-bottom: 1px solid var(--table-border);
            font-weight: 600;
            font-size: 14px;
            color: var(--header-text);
            display: flex;
            align-items: center;
            justify-content: space-between;
            pointer-events: auto; /* Allow dragging from header */
        }}

        .table-body {{
            pointer-events: auto;
        }}

        .table-row {{
            display: flex;
            padding: 6px 12px;
            font-size: 12px;
            border-bottom: 1px solid #f1f5f9;
            align-items: center;
            cursor: pointer;
            transition: background 0.1s;
        }}

        .table-row:last-child {{
            border-bottom: none;
        }}

        .table-row:hover {{
            background: #f8fafc;
        }}

        .col-key {{
            width: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: bold;
            margin-right: 8px;
        }}

        .col-name {{
            flex-grow: 1;
            font-weight: 500;
            color: var(--text-primary);
            margin-right: 12px;
        }}

        .col-type {{
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-secondary);
            font-size: 11px;
        }}

        .pk-badge {{ color: var(--pk-color); }}
        .fk-badge {{ color: var(--fk-color); }}

        /* --- Sidebar Styles --- */
        #sidebar {{
            width: 300px;
            background: white;
            border-left: 1px solid var(--table-border);
            display: flex;
            flex-direction: column;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            position: absolute;
            right: 0;
            top: 0;
            bottom: 0;
            box-shadow: -4px 0 15px rgba(0,0,0,0.05);
            z-index: 1000;
        }}

        #sidebar.open {{
            transform: translateX(0);
        }}

        .sidebar-header {{
            padding: 16px;
            border-bottom: 1px solid var(--table-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .sidebar-title {{
            font-size: 16px;
            font-weight: 600;
        }}

        .close-btn {{
            background: none;
            border: none;
            cursor: pointer;
            font-size: 20px;
            color: var(--text-secondary);
        }}

        .sidebar-content {{
            padding: 16px;
            overflow-y: auto;
        }}

        .field-detail {{
            margin-bottom: 16px;
        }}

        .detail-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }}

        .detail-value {{
            font-size: 14px;
            color: var(--text-primary);
            line-height: 1.5;
        }}
        
        .type-tag {{
            display: inline-block;
            background: #e2e8f0;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
        }}

        /* --- Toolbar --- */
        .toolbar {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: white;
            padding: 8px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex;
            gap: 8px;
            z-index: 999;
        }}

        .tool-btn {{
            padding: 8px 12px;
            background: var(--header-bg);
            border: 1px solid var(--table-border);
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
        }}

        .tool-btn:hover {{
            background: #e2e8f0;
        }}

        .tool-btn.primary {{
            background: var(--accent-color);
            color: white;
            border: none;
        }}
        
        .tool-btn.primary:hover {{
            background: #2563eb;
        }}

    </style>
</head>
<body>

    <div class="toolbar">
        <button class="tool-btn primary" onclick="autoLayout()">Running Auto Layout...</button>
        <button class="tool-btn" onclick="zoomIn()">+</button>
        <button class="tool-btn" onclick="zoomOut()">-</button>
        <button class="tool-btn" onclick="exportPNG()">Save as PNG</button>
        <button class="tool-btn" onclick="exportSVG()">Save as SVG</button>
    </div>

    <div id="paper"></div>

    <div id="sidebar">
        <div class="sidebar-header">
            <span class="sidebar-title">Field Details</span>
            <button class="close-btn" onclick="closeSidebar()">×</button>
        </div>
        <div class="sidebar-content" id="sidebar-details">
            <div class="detail-value" style="color: var(--text-secondary); font-style: italic;">
                Select a field to view details.
            </div>
        </div>
    </div>

    <script>
        const erdData = {erd_json};

        // --- Custom HTML Element Definition ---
        joint.shapes.html = {{}};
        joint.shapes.html.Element = joint.shapes.standard.Rectangle.extend({{
            defaults: joint.util.deepSupplement({{
                type: 'html.Element',
                attrs: {{
                    rect: {{ stroke: 'none', 'fill-opacity': 0 }} // Invisible SVG rect
                }}
            }}, joint.shapes.standard.Rectangle.prototype.defaults)
        }});

        joint.shapes.html.ElementView = joint.dia.ElementView.extend({{
            htmlTemplate: null,

            initialize: function() {{
                joint.dia.ElementView.prototype.initialize.apply(this, arguments);
                
                // Create the DIV that will mock the element
                this.div = document.createElement('div');
                this.div.className = 'html-element';
                this.div.id = this.model.id; 
                
                // Prevent paper panning when clicking on the element
                this.div.addEventListener('mousedown', (e) => {{
                    // We handle our own interactions
                    e.stopPropagation(); 
                    
                    // Visual Selection
                    document.querySelectorAll('.html-element').forEach(el => el.classList.remove('selected'));
                    this.div.classList.add('selected');
                }});
                
                this.renderContent();
                this.model.on('change', this.updateBox, this);
            }},
            renderContent: function() {{
                const data = this.model.get('tableData');
                
                // Escape string for usage in onclick
                const tableJson = JSON.stringify({{
                    name: data.label,
                    description: data.description,
                    type: 'table'
                }}).replace(/"/g, '&quot;');
                
                let rowsHtml = '';
                data.fields.forEach(field => {{
                    let keyBadge = '';
                    if (field.is_pk) keyBadge = '<span class="pk-badge" title="Primary Key">PK</span>';
                    else if (field.is_fk) keyBadge = '<span class="fk-badge" title="Foreign Key">FK</span>';

                    // Add asterisk for required fields
                    const requiredMarker = field.is_required ? '<span style="color: #ef4444;">*</span>' : '';

                    // Escape data for attribute usage
                    const fieldJson = JSON.stringify(field).replace(/"/g, '&quot;');

                    rowsHtml += `
                        <div class="table-row" onclick="showFieldDetails('${{fieldJson}}', '${{data.label}}', event)">
                            <div class="col-key">${{keyBadge}}</div>
                            <div class="col-name" title="${{field.name}}">${{field.name}}${{requiredMarker}}</div>
                            <div class="col-type" title="${{field.sql_type}}">${{field.sql_type}}</div>
                        </div>
                    `;
                }});

                this.div.innerHTML = `
                    <div class="table-header" onmousedown="startDrag(event, '${{this.model.id}}')">
                        <span>${{data.label}}</span>
                        <span class="info-btn" onclick="showTableDetails('${{tableJson}}', event)">ℹ️</span>
                    </div>
                    <div class="table-body">
                        ${{rowsHtml}}
                    </div>
                `;
            }},
            render: function() {{
                joint.dia.ElementView.prototype.render.apply(this, arguments);
                
                // Add the DIV to the paper container
                // We use paper.el to ensure it's in the same container
                // Append ensures it is visually on top of the SVG if z-index is equal (but we forced z-index 100)
                this.paper.$el.append(this.div);
                
                this.updateBox();
                return this;
            }},

            updateBox: function() {{
                const bbox = this.model.getBBox();
                const scale = this.paper.scale();
                const tr = this.paper.translate();

                this.div.style.transform = `translate(${{bbox.x * scale.sx + tr.tx}}px, ${{bbox.y * scale.sy + tr.ty}}px) scale(${{scale.sx}})`;
                this.div.style.transformOrigin = '0 0';
                this.div.style.width = bbox.width + 'px';
                this.div.style.height = bbox.height + 'px';
                this.div.style.left = '0';
                this.div.style.top = '0';
            }},

            remove: function() {{
                // Clean up
                if (this.div) this.div.remove();
                joint.dia.ElementView.prototype.remove.apply(this, arguments);
            }}
        }});

        // --- Init Graph ---
        const graph = new joint.dia.Graph();
        const paper = new joint.dia.Paper({{
            el: document.getElementById('paper'),
            model: graph,
            width: '100%',
            height: '100%',
            gridSize: 10,
            drawGrid: true,
            background: {{ color: '#f0f2f5' }},
            interactive: {{ linkMove: false }}, // Allow element move, deny link move
            defaultRouter: {{ name: 'manhattan' }},
            defaultConnector: {{ name: 'rounded' }}
        }});

        // --- Build Graph ---
        const tableElements = {{}};

        // 1. Create Nodes
        erdData.tables.forEach(table => {{
            // Dynamic Width Calculation
            // Estimate text width: Label vs (Fields Name + Type)
            let maxChars = table.label.length;
            table.fields.forEach(f => {{
                // Name + Type + Spacing
                const lineLength = f.name.length + f.sql_type.length + 5;
                if (lineLength > maxChars) maxChars = lineLength;
            }});
            
            // Approx 10px per char + liberal padding
            let calculatedWidth = (maxChars * 10) + 80;
            // Clamping - Minimum width based on style preference
            if (calculatedWidth < 280) calculatedWidth = 280;
            if (calculatedWidth > 700) calculatedWidth = 700;

            // Calculate approximate height
            const headerHeight = 40;
            const rowHeight = 30; 
            // Add extra buffer + border
            const height = headerHeight + (table.fields.length * rowHeight) + 10; 

            const element = new joint.shapes.html.Element({{
                position: {{ x: 0, y: 0 }}, // Will be set by Layout
                size: {{ width: calculatedWidth, height: height }},
                tableData: table // Pass full data to view
            }});

            element.addTo(graph);
            tableElements[table.id] = element;
        }});

        // Helper function to determine cardinality markers
        function getCardinalityMarkers(relType) {{
            // Returns {{ sourceMarker, targetMarker }} based on relationship type
            // Convention: arrow points from child (FK holder) to parent (PK holder)

            // Crow's foot marker (many side) - three lines spreading out
            const crowsFoot = {{
                type: 'path',
                d: 'M 0 -5 L 10 0 L 0 5 M 10 0 L 10 -5 M 10 0 L 10 5',
                fill: 'none'
            }};

            // Single line marker (one side)
            const oneLine = {{
                type: 'path',
                d: 'M 10 -5 L 10 5',
                fill: 'none'
            }};

            if (relType === 'one-to-one') {{
                // One-to-one: single line on both ends
                return {{
                    sourceMarker: oneLine,  // Child end (one)
                    targetMarker: oneLine   // Parent end (one)
                }};
            }} else if (relType === 'one-to-many') {{
                // One-to-many: crow's foot on child (source), single line on parent (target)
                return {{
                    sourceMarker: crowsFoot,  // Child end (many)
                    targetMarker: oneLine     // Parent end (one)
                }};
            }} else if (relType === 'many-to-many') {{
                // Many-to-many: crow's foot on both ends
                return {{
                    sourceMarker: crowsFoot,  // Many end
                    targetMarker: crowsFoot   // Many end
                }};
            }}

            // Default to one-to-many
            return {{
                sourceMarker: crowsFoot,
                targetMarker: oneLine
            }};
        }}

        // 2. Create Links
        erdData.relationships.forEach(rel => {{
            const source = tableElements[rel.from_table];
            const target = tableElements[rel.to_table];

            if (source && target) {{
                const markers = getCardinalityMarkers(rel.relationship_type);

                const link = new joint.shapes.standard.Link({{
                    source: {{ id: source.id }},
                    target: {{ id: target.id }},
                    relationshipData: rel, // Store data for click handler
                    attrs: {{
                        line: {{
                            stroke: '#94a3b8',
                            strokeWidth: 2,
                            sourceMarker: markers.sourceMarker,
                            targetMarker: markers.targetMarker
                        }}
                    }},
                    connector: {{ name: 'rounded' }},
                    router: {{
                        name: 'manhattan',
                        args: {{
                            padding: 20,
                            step: 20,
                            startDirections: ['right'],
                            endDirections: ['left']
                        }}
                    }}
                }});
                link.addTo(graph);
            }}
        }});

        // --- Auto Layout ---
        function autoLayout() {{
            joint.layout.DirectedGraph.layout(graph, {{
                dagre: dagre,
                graphlib: dagre.graphlib,
                rankDir: 'LR', // Left to Right flow is often better for wide tables
                nodeSep: 60,
                rankSep: 120,
                marginX: 50,
                marginY: 50
            }});
            
            // Force update of HTML elements after layout moves SVG nodes
            graph.getElements().forEach(el => {{
                // Trigger change event to update div position
                el.trigger('change:position'); 
            }});
            
            paper.scaleContentToFit({{ padding: 50, maxScale: 1 }});
            // Update zoom level tracker
            currentScale = paper.scale().sx;
        }}

        // Initial Layout
        setTimeout(autoLayout, 100);

        // --- Interaction ---
        
        // Zoom-Pan
        let currentScale = 1;
        const paperEl = document.getElementById('paper');
        
        // Pan logic
        let isPanning = false;
        let startPan = {{ x: 0, y: 0 }};
        let initialPan = {{ x: 0, y: 0 }};

        paper.on('blank:pointerdown', (evt, x, y) => {{
            isPanning = true;
            startPan = {{ x: evt.clientX, y: evt.clientY }};
            initialPan = paper.translate();
            paperEl.style.cursor = 'grabbing';
            closeSidebar(); // Also close sidebar on blank click
        }});

        // Native Wheel Zoom (better for trackpads)
        paperEl.addEventListener('wheel', (evt) => {{
            evt.preventDefault();
            
            // Normalize delta
            const delta = -Math.sign(evt.deltaY) * 0.1;
            const oldScale = currentScale;
            let newScale = oldScale + delta;
            
            // Clamp
            if (newScale < 0.2) newScale = 0.2;
            if (newScale > 3) newScale = 3;
            
            if (newScale !== oldScale) {{
                currentScale = newScale;
                
                // Zoom towards mouse cursor
                // We need to calculate the new offset to keep the point under cursor stable
                // Current mouse position in DOM
                const rect = paperEl.getBoundingClientRect();
                const mouseX = evt.clientX - rect.left;
                const mouseY = evt.clientY - rect.top;
                
                // Convert mouse to graph coordinates (using OLD scale)
                const tr = paper.translate();
                const graphX = (mouseX - tr.tx) / oldScale;
                const graphY = (mouseY - tr.ty) / oldScale;
                
                // New Translate = Mouse - (Graph * NewScale)
                const newTx = mouseX - (graphX * newScale);
                const newTy = mouseY - (graphY * newScale);
                
                paper.scale(newScale, newScale);
                paper.translate(newTx, newTy);
                
                // Update HTML elements (scale event also handles this, but explicit check good)
            }}
        }}, {{ passive: false }});
        
        // Custom Drag Logic for HTML Elements
        let isDraggingBox = false;
        let dragElementId = null;
        let dragStartOffset = {{ x: 0, y: 0 }};
        
        function startDrag(evt, modelId) {{
            // evt.preventDefault(); // allow text selection? No, header.
            isDraggingBox = true;
            dragElementId = modelId;
            
            const tr = paper.translate();
            const sc = paper.scale().sx;
            const model = graph.getCell(modelId);
            const pos = model.position();
            
            // Calculate where we clicked relative to model pos
            // Mouse (client) -> Graph Coords
            // But easier: just track delta from mouse down.
            // Wait, we need to update MODEL position.
            
            // Mouse Client X/Y
            // We'll track MovementX/Y in mousemove? No, that's unreliable.
            // Let's track absolute start.
            
            // Store original model position
            dragStartOffset = {{
                clickX: evt.clientX,
                clickY: evt.clientY,
                modelX: pos.x,
                modelY: pos.y
            }};
            
            paperEl.style.cursor = 'move';
        }}


        // Global Mouse Move (handles both pan and box drag)
        document.addEventListener('mousemove', (evt) => {{
            if (isPanning) {{
                const dx = evt.clientX - startPan.x;
                const dy = evt.clientY - startPan.y;
                paper.translate(initialPan.tx + dx, initialPan.ty + dy);
            }}
            
            if (isDraggingBox && dragElementId) {{
                const dx = evt.clientX - dragStartOffset.clickX;
                const dy = evt.clientY - dragStartOffset.clickY;
                
                // Convert screen delta to graph delta
                // deltaGraph = deltaScreen / scale
                const sc = paper.scale().sx;
                const dGraphX = dx / sc;
                const dGraphY = dy / sc;
                
                const model = graph.getCell(dragElementId);
                model.position(dragStartOffset.modelX + dGraphX, dragStartOffset.modelY + dGraphY);
                
                // Links update automatically because model updates
            }}
        }});
        
        document.addEventListener('mouseup', () => {{
            isPanning = false;
            isDraggingBox = false;
            dragElementId = null;
            paperEl.style.cursor = 'default';
        }});
        
        // Link Click Handler
        paper.on('link:pointerdown', (linkView) => {{
            const rel = linkView.model.get('relationshipData');
            if (!rel) return; // Guard against regular links if any
            
            const sidebar = document.getElementById('sidebar');
            const content = document.getElementById('sidebar-details');
            
            content.innerHTML = `
                <div class="field-detail">
                    <div class="detail-label">Relationship</div>
                    <div class="type-tag">Foreign Key</div>
                </div>
                <div class="field-detail">
                    <div class="detail-label">From (Child)</div>
                    <div class="detail-value">
                        <strong>${{rel.from_table}}</strong>.${{rel.from_field}}
                    </div>
                </div>
                <div class="field-detail">
                    <div class="detail-label">To (Parent)</div>
                    <div class="detail-value">
                        <strong>${{rel.to_table}}</strong>.${{rel.to_field}}
                    </div>
                </div>
                <div class="field-detail">
                    <div class="detail-label">Type</div>
                    <div class="detail-value">${{rel.relationship_type}}</div>
                </div>
            `;
            sidebar.classList.add('open');
            
            // Highlight Link
            graph.getLinks().forEach(l => {{
                l.attr('line/stroke', '#94a3b8');
                l.attr('line/strokeWidth', 2);
            }});
            
            linkView.model.attr('line/stroke', '#3b82f6');
            linkView.model.attr('line/strokeWidth', 4);
        }});
        
        // Paper Transform Listener to sync HTML elements
        // This is crucial. When paper zooms or pans, we must update the CSS transform of a container 
        // OR update every single element. Updating every element is easier for this scale.
        paper.on('render:done translate resize scale', () => {{
            // This global update is heavy but ensures sync
            const transform = paper.translate();
            const scale = paper.scale();

            // Iterate all views
            for (const key in paper._views) {{
                const view = paper._views[key];
                if (view.updateBox) {{
                    const modelBox = view.model.getBBox();
                    // Transform model coordinates to paper coordinates
                    // (x * scale) + tx
                    const tx = transform.tx;
                    const ty = transform.ty;
                    const sx = scale.sx;
                    const sy = scale.sy;
                    
                    // Apply transform directly to the div for scaling and positioning
                    view.div.style.transform = `translate(${{modelBox.x * sx + tx}}px, ${{modelBox.y * sy + ty}}px) scale(${{sx}})`;
                    view.div.style.transformOrigin = '0 0'; // Scale from top-left
                    
                    // Set width/height based on original model size, let scale handle visual size
                    view.div.style.width = modelBox.width + 'px';
                    view.div.style.height = modelBox.height + 'px';
                }}
            }}
        }});

        // --- Toolbar Functions ---
        function zoomIn() {{ currentScale += 0.1; paper.scale(currentScale); }}
        function zoomOut() {{ currentScale -= 0.1; paper.scale(currentScale); }}

        function exportPNG() {{
            closeSidebar();

            // Get the paper element
            const paperElement = document.getElementById('paper');

            // Calculate the bounding box of all elements
            const bbox = graph.getBBox();

            // Add some padding
            const padding = 50;
            const width = bbox.width + (padding * 2);
            const height = bbox.height + (padding * 2);

            // Temporarily adjust view to fit content
            const originalTransform = paper.translate();
            const originalScale = paper.scale();

            // Reset to show all content
            paper.translate(padding - bbox.x, padding - bbox.y);
            paper.scale(1, 1);

            // Use html2canvas to render
            html2canvas(paperElement, {{
                backgroundColor: '#f0f2f5',
                width: width,
                height: height,
                scrollX: 0,
                scrollY: 0,
                windowWidth: width,
                windowHeight: height,
                useCORS: true
            }}).then(canvas => {{
                // Convert canvas to blob and download
                canvas.toBlob(blob => {{
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.download = 'dateaubase_erd.png';
                    link.href = url;
                    link.click();
                    URL.revokeObjectURL(url);
                }});

                // Restore original view
                paper.translate(originalTransform.tx, originalTransform.ty);
                paper.scale(originalScale.sx, originalScale.sy);
            }}).catch(err => {{
                console.error('Error generating PNG:', err);
                alert('Error generating PNG. See console for details.');

                // Restore original view even on error
                paper.translate(originalTransform.tx, originalTransform.ty);
                paper.scale(originalScale.sx, originalScale.sy);
            }});
        }}

        function exportSVG() {{
            closeSidebar();

            // Get the SVG element from the paper
            const svgElement = paper.svg;

            // Clone the SVG to avoid modifying the original
            const svgClone = svgElement.cloneNode(true);

            // Get bounding box for proper dimensions
            const bbox = graph.getBBox();
            const padding = 50;

            // Set viewBox and dimensions
            svgClone.setAttribute('viewBox', `${{bbox.x - padding}} ${{bbox.y - padding}} ${{bbox.width + padding * 2}} ${{bbox.height + padding * 2}}`);
            svgClone.setAttribute('width', bbox.width + padding * 2);
            svgClone.setAttribute('height', bbox.height + padding * 2);

            // Add background rectangle
            const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            bgRect.setAttribute('x', bbox.x - padding);
            bgRect.setAttribute('y', bbox.y - padding);
            bgRect.setAttribute('width', bbox.width + padding * 2);
            bgRect.setAttribute('height', bbox.height + padding * 2);
            bgRect.setAttribute('fill', '#f0f2f5');
            svgClone.insertBefore(bgRect, svgClone.firstChild);

            // Embed HTML elements as foreignObject
            const htmlElements = document.querySelectorAll('.html-element');
            htmlElements.forEach(htmlEl => {{
                const modelId = htmlEl.id;
                const model = graph.getCell(modelId);
                if (!model) return;

                const bbox = model.getBBox();

                // Create foreignObject to embed HTML
                const foreignObject = document.createElementNS('http://www.w3.org/2000/svg', 'foreignObject');
                foreignObject.setAttribute('x', bbox.x);
                foreignObject.setAttribute('y', bbox.y);
                foreignObject.setAttribute('width', bbox.width);
                foreignObject.setAttribute('height', bbox.height);

                // Clone the HTML element and its styles
                const htmlClone = htmlEl.cloneNode(true);
                htmlClone.style.transform = 'none';
                htmlClone.style.position = 'relative';
                htmlClone.style.width = bbox.width + 'px';
                htmlClone.style.height = bbox.height + 'px';

                foreignObject.appendChild(htmlClone);
                svgClone.appendChild(foreignObject);
            }});

            // Serialize SVG to string
            const serializer = new XMLSerializer();
            let svgString = serializer.serializeToString(svgClone);

            // Add XML declaration and namespaces
            svgString = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>' + svgString;

            // Create blob and download
            const blob = new Blob([svgString], {{ type: 'image/svg+xml;charset=utf-8' }});
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.download = 'dateaubase_erd.svg';
            link.href = url;
            link.click();
            URL.revokeObjectURL(url);
        }}
        
        // --- Sidebar Logic ---
        function showFieldDetails(fieldJson, tableName, event) {{
            event.stopPropagation(); // Prevent paper blank click from closing sidebar
            const field = JSON.parse(fieldJson);
            const sidebar = document.getElementById('sidebar');
            const content = document.getElementById('sidebar-details');
            
            const desc = field.description || "No description available.";
            
            content.innerHTML = `
                <div class="field-detail">
                    <div class="detail-label">Table</div>
                    <div class="detail-value" style="font-weight: 600">${{tableName}}</div>
                </div>
                <div class="field-detail">
                    <div class="detail-label">Field</div>
                    <div class="detail-value">${{field.name}}</div>
                </div>
                <div class="field-detail">
                    <div class="detail-label">Type</div>
                    <div class="type-tag">${{field.sql_type}}</div>
                </div>
                <div class="field-detail">
                    <div class="detail-label">Description</div>
                    <div class="detail-value">${{desc}}</div>
                </div>
            `;
            
            if (field.is_fk && field.fk_target) {{
                content.innerHTML += `
                     <div class="field-detail">
                        <div class="detail-label">Foreign Key Target</div>
                        <div class="detail-value">🔗 ${{field.fk_target}}</div>
                    </div>
                `;
            }}
            
            sidebar.classList.add('open');
            
            // Highlight row visually (already handled by onclick row class? No, need logic)
            // Remove previous highlights
            document.querySelectorAll('.table-row').forEach(r => r.style.background = '');
            // Highlight current
            event.currentTarget.style.background = '#e0e7ff';
        }}
        
        function showTableDetails(tableJson, event) {{
            event.stopPropagation();
            const table = JSON.parse(tableJson);
            const sidebar = document.getElementById('sidebar');
            const content = document.getElementById('sidebar-details');
            
            content.innerHTML = `
                <div class="field-detail">
                    <div class="detail-label">Type</div>
                    <div class="type-tag">Table</div>
                </div>
                <div class="field-detail">
                    <div class="detail-label">Name</div>
                    <div class="detail-value" style="font-weight: 600">${{table.name}}</div>
                </div>
                <div class="field-detail">
                    <div class="detail-label">Description</div>
                    <div class="detail-value">${{table.description || "No description available."}}</div>
                </div>
            `;
            
            sidebar.classList.add('open');
            // Remove row highlights
            document.querySelectorAll('.table-row').forEach(r => r.style.background = '');
        }}

        function closeSidebar() {{
             document.getElementById('sidebar').classList.remove('open');
             document.querySelectorAll('.table-row').forEach(r => r.style.background = '');
        }}
        
        // Close sidebar when clicking on paper blank area
        paper.on('blank:pointerdown', () => {{
            closeSidebar();
        }});

    </script>
</body>
</html>"""

    return html
