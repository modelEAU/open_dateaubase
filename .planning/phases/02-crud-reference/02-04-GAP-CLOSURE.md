---
phase: 02-crud-reference
plan: 04-gap-closure
type: gap-closure
parent_plan: 02-04-PLAN.md
depends_on:
  - plan: 02-04
    status: checkpoint-reached
    tasks_complete: [1, 2]
    task_3: human-feedback-received
---

<objective>
Redesign Sites, Equipment, and Campaigns pages to use form-based CRUD instead of inline editing.

**Context**: Human verification of 02-04 Task 3 revealed that while st.data_editor works for READ and DELETE, CREATE and UPDATE need form-based interfaces for better UX with graduate student users.

**Approach**: Keep table for display + selection, add dialog forms for create/edit operations. Add API lookup endpoints for FK dropdowns.

**Scope**: All three reference data pages (Sites, Equipment, Campaigns).
</objective>

<context>
@.planning/phases/02-crud-reference/02-04-PLAN.md
@app/pages/1_Sites.py
@app/pages/2_Equipment.py
@app/pages/3_Campaigns.py
@app/components/crud_table.py
@app/api_client.py

**Current Implementation**:
- `crud_data_editor()` component wraps `st.data_editor`
- Inline editing: users edit cells directly in the table
- Write operations: diff original vs edited dataframe
- FK fields show raw IDs (not user-friendly)

**Target Implementation**:
- Table displays data with row selection (st.dataframe or st.data_editor with disabled editing)
- "New" button opens create form dialog
- "Edit" button opens edit form dialog (requires row selection)
- Forms use `st.form` with proper field types
- FK fields show dropdowns populated from API lookups
- Validation shows inline errors
- POST for create, PATCH for update

**API Gaps Identified**:
1. No PATCH endpoints for partial updates (only PUT)
2. No lookup endpoints for FK dropdowns:
   - `/sites/lookup` - id+name list
   - `/campaign-types` - all campaign types
   - `/equipment-models/lookup` - model_id + model_name + manufacturer
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add PATCH endpoints for partial updates</name>
  <files>
    api/v1/endpoints/sites.py
    api/v1/endpoints/equipment.py
    api/v1/endpoints/campaigns.py
  </files>
  <action>
    Add PATCH endpoints to support partial updates for form-based editing:

    **Sites** (`api/v1/endpoints/sites.py`):
    ```python
    @router.patch("/{site_id}", response_model=SiteOut)
    def patch_site(site_id: int, body: SitePatch, conn=Depends(get_db)):
        """Partial update of a site."""
        updated = site_repository.patch_site(conn, site_id, body.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")
        return updated
    ```

    Create `SitePatch` schema in `api/v1/schemas/metadata.py` with all optional fields.

    **Equipment** (`api/v1/endpoints/equipment.py`):
    ```python
    @router.patch("/{equipment_id}", response_model=EquipmentOut)
    def patch_equipment(equipment_id: int, body: EquipmentPatch, conn=Depends(get_db)):
        """Partial update of equipment."""
        updated = equipment_repository.patch_equipment(conn, equipment_id, body.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Equipment {equipment_id} not found.")
        return updated
    ```

    **Campaigns** (`api/v1/endpoints/campaigns.py`):
    ```python
    @router.patch("/{campaign_id}", response_model=CampaignOut)
    def patch_campaign(campaign_id: int, body: CampaignPatch, conn=Depends(get_db)):
        """Partial update of a campaign."""
        updated = campaign_repository.patch_campaign(conn, campaign_id, body.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found.")
        return updated
    ```

    Create corresponding Patch schemas and repository methods for each entity.
  </action>
  <verify>
    curl -X PATCH http://localhost:8000/api/v1/sites/1 \
      -H "Content-Type: application/json" \
      -d '{"name": "Updated Site Name"}'
    # Should return 200 with updated site
  </verify>
  <done>PATCH endpoints exist for /sites/{id}, /equipment/{id}, /campaigns/{id} with partial update support</done>
</task>

<task type="auto">
  <name>Task 2: Add lookup endpoints for FK dropdowns</name>
  <files>
    api/v1/endpoints/sites.py
    api/v1/endpoints/campaigns.py
    api/v1/endpoints/metadata.py (or new endpoints)
    api/v1/schemas/common.py
  </files>
  <action>
    Add lightweight lookup endpoints for UI dropdowns:

    **Sites Lookup** (`api/v1/endpoints/sites.py`):
    ```python
    @router.get("/lookup/list", response_model=list[SiteLookupOut])
    def list_sites_lookup(conn=Depends(get_db)):
        """Return lightweight site list for dropdowns (id, name only)."""
        return site_repository.get_sites_lookup(conn)
    ```

    Create `SiteLookupOut` schema: `{site_id: int, name: str}`

    **Campaign Types** (`api/v1/endpoints/campaigns.py`):
    ```python
    @router.get("/types", response_model=list[CampaignTypeOut])
    def list_campaign_types(conn=Depends(get_db)):
        """Return all campaign types for dropdowns."""
        return campaign_repository.get_campaign_types(conn)
    ```

    Create `CampaignTypeOut` schema: `{campaign_type_id: int, name: str, description: str | None}`
    Add `get_campaign_types()` to campaign_repository.py

    **Equipment Models** (add to `api/v1/endpoints/equipment.py`):
    ```python
    @router.get("/models/lookup", response_model=list[EquipmentModelLookupOut])
    def list_equipment_models_lookup(conn=Depends(get_db)):
        """Return equipment models for dropdowns."""
        return equipment_repository.get_models_lookup(conn)
    ```

    Create `EquipmentModelLookupOut`: `{model_id: int, model_name: str, manufacturer: str | None}`
  </action>
  <verify>
    curl http://localhost:8000/api/v1/sites/lookup/list | jq '.[0] | {id, name}'
    curl http://localhost:8000/api/v1/campaigns/types | jq '.[0] | {campaign_type_id, name}'
  </verify>
  <done>Lookup endpoints return id+name pairs for all FK relationships; response time < 100ms</done>
</task>

<task type="auto">
  <name>Task 3: Create crud_form component</name>
  <files>
    app/components/crud_form.py
  </files>
  <action>
    Create `app/components/crud_form.py` with reusable form rendering utilities:

    ```python
    """Reusable form components for CRUD operations."""
    from __future__ import annotations

    import streamlit as st
    from typing import Callable, Any

    def render_form_field(
        field_name: str,
        field_type: str,
        value: Any = None,
        required: bool = False,
        options: list[dict] | None = None,  # For dropdowns: [{"id": 1, "label": "Name"}]
        help_text: str | None = None,
    ) -> Any:
        """Render a single form field based on type.
        
        field_type: "text" | "number" | "select" | "date" | "textarea"
        """
        label = f"{field_name}{' *' if required else ''}"
        
        if field_type == "select" and options:
            # Map options to display labels, return ID
            option_map = {opt["label"]: opt["id"] for opt in options}
            labels = list(option_map.keys())
            current_label = next(
                (opt["label"] for opt in options if opt["id"] == value),
                labels[0] if labels else None
            )
            selected = st.selectbox(label, options=labels, index=labels.index(current_label) if current_label in labels else 0, help=help_text)
            return option_map[selected]
        elif field_type == "number":
            return st.number_input(label, value=value or 0, help=help_text)
        elif field_type == "date":
            return st.date_input(label, value=value, help=help_text)
        elif field_type == "textarea":
            return st.text_area(label, value=value or "", help=help_text)
        else:  # text
            return st.text_input(label, value=value or "", help=help_text)

    def validate_required_fields(data: dict, required_fields: list[str]) -> list[str]:
        """Return list of validation errors for missing required fields."""
        errors = []
        for field in required_fields:
            if not data.get(field):
                errors.append(f"{field} is required")
        return errors
    ```
  </action>
  <verify>uv run python -c "from app.components.crud_form import render_form_field; print('OK')"</verify>
  <done>crud_form.py exists with render_form_field() and validate_required_fields() functions</done>
</task>

<task type="auto">
  <name>Task 4: Create form_dialog component</name>
  <files>
    app/components/form_dialog.py
  </files>
  <action>
    Create `app/components/form_dialog.py` for modal form dialogs using Streamlit's st.dialog:

    ```python
    """Form dialog components for CRUD operations."""
    from __future__ import annotations

    import streamlit as st
    from typing import Callable, Any

    @st.dialog("Create New Item", width="large")
    def create_form_dialog(
        fields: list[dict],  # [{"name": "...", "type": "...", "required": bool, "options": [...]}]
        on_submit: Callable[[dict], bool],  # Returns True if successful
        title: str = "Create",
    ) -> None:
        """Display a create form dialog.
        
        Example fields:
        [
            {"name": "name", "type": "text", "required": True},
            {"name": "site_id", "type": "select", "required": True, "options": [{"id": 1, "label": "Site A"}]},
        ]
        """
        from app.components.crud_form import render_form_field, validate_required_fields
        
        st.write(f"### {title}")
        
        form_data = {}
        required_fields = []
        
        for field in fields:
            if field.get("required"):
                required_fields.append(field["name"])
            form_data[field["name"]] = render_form_field(
                field_name=field["name"],
                field_type=field["type"],
                required=field.get("required", False),
                options=field.get("options"),
                help_text=field.get("help"),
            )
        
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("Validate", type="secondary"):
                errors = validate_required_fields(form_data, required_fields)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    st.success("All required fields filled!")
        with col2:
            if st.button("Send", type="primary"):
                errors = validate_required_fields(form_data, required_fields)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    success = on_submit(form_data)
                    if success:
                        st.rerun()
        with col3:
            if st.button("Cancel", type="secondary"):
                st.rerun()

    @st.dialog("Edit Item", width="large")
    def edit_form_dialog(
        item_data: dict,
        fields: list[dict],
        on_submit: Callable[[dict], bool],
        title: str = "Edit",
    ) -> None:
        """Display an edit form dialog pre-populated with item_data."""
        from app.components.crud_form import render_form_field, validate_required_fields
        
        st.write(f"### {title}")
        
        form_data = {}
        required_fields = []
        
        for field in fields:
            field_name = field["name"]
            if field.get("required"):
                required_fields.append(field_name)
            
            # Get current value from item_data
            current_value = item_data.get(field_name)
            
            form_data[field_name] = render_form_field(
                field_name=field_name,
                field_type=field["type"],
                value=current_value,
                required=field.get("required", False),
                options=field.get("options"),
                help_text=field.get("help"),
            )
        
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("Validate", type="secondary"):
                errors = validate_required_fields(form_data, required_fields)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    st.success("All required fields filled!")
        with col2:
            if st.button("Send", type="primary"):
                errors = validate_required_fields(form_data, required_fields)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    # Include ID from original item
                    form_data["id"] = item_data.get("id")
                    success = on_submit(form_data)
                    if success:
                        st.rerun()
        with col3:
            if st.button("Cancel", type="secondary"):
                st.rerun()
    ```
  </action>
  <verify>uv run python -c "from app.components.form_dialog import create_form_dialog; print('OK')"</verify>
  <done>form_dialog.py exists with create_form_dialog() and edit_form_dialog() functions using st.dialog</done>
</task>

<task type="auto">
  <name>Task 5: Update api_client with PATCH and lookup methods</name>
  <files>
    app/api_client.py
  </files>
  <action>
    Add to `app/api_client.py`:

    **PATCH methods**:
    ```python
    def patch_site(site_id: int, data: dict) -> dict:
        try:
            with _get_client() as client:
                r = client.patch(f"/sites/{site_id}", json=data)
        except httpx.ConnectError:
            raise APIError(503, "Cannot reach API")
        _raise_for_status(r)
        return r.json()

    def patch_equipment(equipment_id: int, data: dict) -> dict:
        try:
            with _get_client() as client:
                r = client.patch(f"/equipment/{equipment_id}", json=data)
        except httpx.ConnectError:
            raise APIError(503, "Cannot reach API")
        _raise_for_status(r)
        return r.json()

    def patch_campaign(campaign_id: int, data: dict) -> dict:
        try:
            with _get_client() as client:
                r = client.patch(f"/campaigns/{campaign_id}", json=data)
        except httpx.ConnectError:
            raise APIError(503, "Cannot reach API")
        _raise_for_status(r)
        return r.json()
    ```

    **Lookup methods**:
    ```python
    def list_sites_lookup() -> list[dict]:
        """Return lightweight site list for dropdowns."""
        try:
            with _get_client() as client:
                r = client.get("/sites/lookup/list")
        except httpx.ConnectError:
            raise APIError(503, "Cannot reach API")
        _raise_for_status(r)
        return r.json()

    def list_campaign_types() -> list[dict]:
        """Return all campaign types for dropdowns."""
        try:
            with _get_client() as client:
                r = client.get("/campaigns/types")
        except httpx.ConnectError:
            raise APIError(503, "Cannot reach API")
        _raise_for_status(r)
        return r.json()

    def list_equipment_models_lookup() -> list[dict]:
        """Return equipment models for dropdowns."""
        try:
            with _get_client() as client:
                r = client.get("/equipment/models/lookup")
        except httpx.ConnectError:
            raise APIError(503, "Cannot reach API")
        _raise_for_status(r)
        return r.json()
    ```
  </action>
  <verify>uv run python -c "from app.api_client import patch_site, list_sites_lookup; print('OK')"</verify>
  <done>api_client has patch_* and lookup methods for all entities</done>
</task>

<task type="auto">
  <name>Task 6: Rewrite Sites page with form-based CRUD</name>
  <files>
    app/pages/1_Sites.py
  </files>
  <action>
    Rewrite `app/pages/1_Sites.py` with form-based pattern:

    ```python
    """Sites CRUD page with form-based editing."""
    from __future__ import annotations

    import sys
    from pathlib import Path

    _project_root = str(Path(__file__).resolve().parent.parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    import streamlit as st
    import pandas as pd

    from app.api_client import (
        APIError,
        create_site,
        delete_site,
        list_sites,
        patch_site,
    )
    from app.auth import get_current_user, logout, require_auth
    from app.components.form_dialog import create_form_dialog, edit_form_dialog

    require_auth()

    with st.sidebar:
        user = get_current_user()
        if user:
            st.write(f"Logged in as: **{user['name']}**")
        if st.button("Sign out"):
            logout()

    st.title("Sites")

    # Load sites
    try:
        with st.spinner("Loading sites..."):
            sites_data = list_sites()
            sites = sites_data.get("items", []) if isinstance(sites_data, dict) else sites_data
    except APIError as e:
        st.error(f"Cannot load sites: {e.message}")
        st.stop()

    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 8])
    with col1:
        if st.button("➕ New", type="primary"):
            create_form_dialog(
                fields=[
                    {"name": "name", "type": "text", "required": True},
                    {"name": "type", "type": "text", "required": False},
                    {"name": "description", "type": "textarea", "required": False},
                    {"name": "lat_wgs84", "type": "number", "required": False},
                    {"name": "long_wgs84", "type": "number", "required": False},
                    {"name": "city", "type": "text", "required": False},
                    {"name": "province", "type": "text", "required": False},
                    {"name": "country", "type": "text", "required": False},
                ],
                on_submit=lambda data: handle_create_site(data),
                title="Create New Site",
            )

    # Store selected row in session state
    if "selected_site_id" not in st.session_state:
        st.session_state.selected_site_id = None

    # Display table with selection
    if sites:
        df = pd.DataFrame(sites)
        
        # Create a selection column
        selected_indices = st.dataframe(
            df,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
        )
        
        if selected_indices and selected_indices.get("selection", {}).get("rows"):
            row_idx = selected_indices["selection"]["rows"][0]
            st.session_state.selected_site_id = df.iloc[row_idx]["id"]
            selected_site = sites[row_idx]
        else:
            selected_site = None
            st.session_state.selected_site_id = None
    else:
        st.info("No sites found. Click 'New' to create one.")
        selected_site = None

    with col2:
        if st.button("✏️ Edit", disabled=selected_site is None):
            if selected_site:
                edit_form_dialog(
                    item_data=selected_site,
                    fields=[
                        {"name": "name", "type": "text", "required": True},
                        {"name": "type", "type": "text", "required": False},
                        {"name": "description", "type": "textarea", "required": False},
                        {"name": "lat_wgs84", "type": "number", "required": False},
                        {"name": "long_wgs84", "type": "number", "required": False},
                        {"name": "city", "type": "text", "required": False},
                        {"name": "province", "type": "text", "required": False},
                        {"name": "country", "type": "text", "required": False},
                    ],
                    on_submit=lambda data: handle_patch_site(selected_site["id"], data),
                    title=f"Edit Site: {selected_site.get('name', '')}",
                )

    with col3:
        if st.button("🗑️ Delete", disabled=selected_site is None, type="secondary"):
            if selected_site and st.confirm(f"Delete site '{selected_site.get('name')}'?"):
                handle_delete_site(selected_site["id"])

    # Handler functions
    def handle_create_site(data: dict) -> bool:
        try:
            create_site(data)
            st.success("Site created successfully!")
            return True
        except APIError as e:
            st.error(f"Failed to create site: {e.message}")
            return False

    def handle_patch_site(site_id: int, data: dict) -> bool:
        try:
            patch_site(site_id, data)
            st.success("Site updated successfully!")
            return True
        except APIError as e:
            st.error(f"Failed to update site: {e.message}")
            return False

    def handle_delete_site(site_id: int) -> None:
        try:
            delete_site(site_id)
            st.success("Site deleted successfully!")
            st.rerun()
        except APIError as e:
            st.error(f"Failed to delete site: {e.message}")
    ```
  </action>
  <verify>uv run python -c "import ast; ast.parse(open('app/pages/1_Sites.py').read()); print('syntax OK')"</verify>
  <done>Sites page uses form-based CRUD with New/Edit/Delete buttons and dialog forms</done>
</task>

<task type="auto">
  <name>Task 7: Rewrite Equipment page with form-based CRUD</name>
  <files>
    app/pages/2_Equipment.py
  </files>
  <action>
    Rewrite `app/pages/2_Equipment.py` with form-based pattern, including model_id dropdown:

    ```python
    """Equipment CRUD page with form-based editing."""
    from __future__ import annotations

    import sys
    from pathlib import Path

    _project_root = str(Path(__file__).resolve().parent.parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    import streamlit as st
    import pandas as pd

    from app.api_client import (
        APIError,
        create_equipment,
        delete_equipment,
        list_equipment,
        list_equipment_models_lookup,
        patch_equipment,
    )
    from app.auth import get_current_user, logout, require_auth
    from app.components.form_dialog import create_form_dialog, edit_form_dialog

    require_auth()

    with st.sidebar:
        user = get_current_user()
        if user:
            st.write(f"Logged in as: **{user['name']}**")
        if st.button("Sign out"):
            logout()

    st.title("Equipment")

    # Load equipment and models for dropdown
    try:
        with st.spinner("Loading..."):
            equipment_data = list_equipment()
            equipment = equipment_data.get("items", []) if isinstance(equipment_data, dict) else equipment_data
            models = list_equipment_models_lookup()
    except APIError as e:
        st.error(f"Cannot load data: {e.message}")
        st.stop()

    # Prepare model options for dropdown
    model_options = [{"id": m["model_id"], "label": f"{m['manufacturer']} - {m['model_name']}"} for m in models]

    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 8])
    with col1:
        if st.button("➕ New", type="primary"):
            create_form_dialog(
                fields=[
                    {"name": "identifier", "type": "text", "required": True},
                    {"name": "serial_number", "type": "text", "required": False},
                    {"name": "model_id", "type": "select", "required": False, "options": model_options},
                    {"name": "owner", "type": "text", "required": False},
                    {"name": "purchase_date", "type": "date", "required": False},
                ],
                on_submit=lambda data: handle_create_equipment(data),
                title="Create New Equipment",
            )

    # Store selected row
    if "selected_equipment_id" not in st.session_state:
        st.session_state.selected_equipment_id = None

    # Display table
    if equipment:
        df = pd.DataFrame(equipment)
        selected_indices = st.dataframe(
            df,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
        )
        if selected_indices and selected_indices.get("selection", {}).get("rows"):
            row_idx = selected_indices["selection"]["rows"][0]
            st.session_state.selected_equipment_id = df.iloc[row_idx]["equipment_id"]
            selected_item = equipment[row_idx]
        else:
            selected_item = None
            st.session_state.selected_equipment_id = None
    else:
        st.info("No equipment found. Click 'New' to create one.")
        selected_item = None

    with col2:
        if st.button("✏️ Edit", disabled=selected_item is None):
            if selected_item:
                edit_form_dialog(
                    item_data=selected_item,
                    fields=[
                        {"name": "identifier", "type": "text", "required": True},
                        {"name": "serial_number", "type": "text", "required": False},
                        {"name": "model_id", "type": "select", "required": False, "options": model_options},
                        {"name": "owner", "type": "text", "required": False},
                        {"name": "purchase_date", "type": "date", "required": False},
                    ],
                    on_submit=lambda data: handle_patch_equipment(selected_item["equipment_id"], data),
                    title=f"Edit Equipment: {selected_item.get('identifier', '')}",
                )

    with col3:
        if st.button("🗑️ Delete", disabled=selected_item is None, type="secondary"):
            if selected_item:
                handle_delete_equipment(selected_item["equipment_id"])

    def handle_create_equipment(data: dict) -> bool:
        try:
            create_equipment(data)
            st.success("Equipment created successfully!")
            return True
        except APIError as e:
            st.error(f"Failed to create equipment: {e.message}")
            return False

    def handle_patch_equipment(equipment_id: int, data: dict) -> bool:
        try:
            patch_equipment(equipment_id, data)
            st.success("Equipment updated successfully!")
            return True
        except APIError as e:
            st.error(f"Failed to update equipment: {e.message}")
            return False

    def handle_delete_equipment(equipment_id: int) -> None:
        try:
            delete_equipment(equipment_id)
            st.success("Equipment deleted successfully!")
            st.rerun()
        except APIError as e:
            st.error(f"Failed to delete equipment: {e.message}")
    ```
  </action>
  <verify>uv run python -c "import ast; ast.parse(open('app/pages/2_Equipment.py').read()); print('syntax OK')"</verify>
  <done>Equipment page uses form-based CRUD with model dropdown populated from API lookup</done>
</task>

<task type="auto">
  <name>Task 8: Rewrite Campaigns page with form-based CRUD</name>
  <files>
    app/pages/3_Campaigns.py
  </files>
  <action>
    Rewrite `app/pages/3_Campaigns.py` with form-based pattern, including site and campaign type dropdowns:

    ```python
    """Campaigns CRUD page with form-based editing."""
    from __future__ import annotations

    import sys
    from pathlib import Path

    _project_root = str(Path(__file__).resolve().parent.parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    import streamlit as st
    import pandas as pd

    from app.api_client import (
        APIError,
        create_campaign,
        delete_campaign,
        list_campaigns,
        list_campaign_types,
        list_sites_lookup,
        patch_campaign,
    )
    from app.auth import get_current_user, logout, require_auth
    from app.components.form_dialog import create_form_dialog, edit_form_dialog

    require_auth()

    with st.sidebar:
        user = get_current_user()
        if user:
            st.write(f"Logged in as: **{user['name']}**")
        if st.button("Sign out"):
            logout()

    st.title("Campaigns")

    # Load campaigns, sites, and campaign types
    try:
        with st.spinner("Loading..."):
            campaigns_data = list_campaigns()
            campaigns = campaigns_data.get("items", []) if isinstance(campaigns_data, dict) else campaigns_data
            sites = list_sites_lookup()
            campaign_types = list_campaign_types()
    except APIError as e:
        st.error(f"Cannot load data: {e.message}")
        st.stop()

    # Prepare dropdown options
    site_options = [{"id": s["site_id"], "label": s["name"]} for s in sites]
    type_options = [{"id": t["campaign_type_id"], "label": t["name"]} for t in campaign_types]

    # Site filter for list view
    site_filter_col, _ = st.columns([2, 8])
    with site_filter_col:
        filter_options = [{"id": None, "label": "All Sites"}] + site_options
        selected_site_filter = st.selectbox(
            "Filter by site",
            options=[opt["label"] for opt in filter_options],
            index=0,
        )
        site_id_filter = next(
            (opt["id"] for opt in filter_options if opt["label"] == selected_site_filter),
            None
        )

    # Filter campaigns
    if site_id_filter is not None:
        filtered_campaigns = [c for c in campaigns if c.get("site_id") == site_id_filter]
    else:
        filtered_campaigns = campaigns

    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 8])
    with col1:
        if st.button("➕ New", type="primary"):
            create_form_dialog(
                fields=[
                    {"name": "name", "type": "text", "required": True},
                    {"name": "campaign_type_id", "type": "select", "required": True, "options": type_options},
                    {"name": "site_id", "type": "select", "required": True, "options": site_options},
                    {"name": "description", "type": "textarea", "required": False},
                    {"name": "start_date", "type": "date", "required": False},
                    {"name": "end_date", "type": "date", "required": False},
                ],
                on_submit=lambda data: handle_create_campaign(data),
                title="Create New Campaign",
            )

    # Store selected row
    if "selected_campaign_id" not in st.session_state:
        st.session_state.selected_campaign_id = None

    # Display table
    if filtered_campaigns:
        df = pd.DataFrame(filtered_campaigns)
        selected_indices = st.dataframe(
            df,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
        )
        if selected_indices and selected_indices.get("selection", {}).get("rows"):
            row_idx = selected_indices["selection"]["rows"][0]
            st.session_state.selected_campaign_id = df.iloc[row_idx]["campaign_id"]
            selected_campaign = filtered_campaigns[row_idx]
        else:
            selected_campaign = None
            st.session_state.selected_campaign_id = None
    else:
        st.info("No campaigns found. Click 'New' to create one.")
        selected_campaign = None

    with col2:
        if st.button("✏️ Edit", disabled=selected_campaign is None):
            if selected_campaign:
                edit_form_dialog(
                    item_data=selected_campaign,
                    fields=[
                        {"name": "name", "type": "text", "required": True},
                        {"name": "campaign_type_id", "type": "select", "required": True, "options": type_options},
                        {"name": "site_id", "type": "select", "required": True, "options": site_options},
                        {"name": "description", "type": "textarea", "required": False},
                        {"name": "start_date", "type": "date", "required": False},
                        {"name": "end_date", "type": "date", "required": False},
                    ],
                    on_submit=lambda data: handle_patch_campaign(selected_campaign["campaign_id"], data),
                    title=f"Edit Campaign: {selected_campaign.get('name', '')}",
                )

    with col3:
        if st.button("🗑️ Delete", disabled=selected_campaign is None, type="secondary"):
            if selected_campaign:
                handle_delete_campaign(selected_campaign["campaign_id"])

    def handle_create_campaign(data: dict) -> bool:
        try:
            create_campaign(data)
            st.success("Campaign created successfully!")
            return True
        except APIError as e:
            st.error(f"Failed to create campaign: {e.message}")
            return False

    def handle_patch_campaign(campaign_id: int, data: dict) -> bool:
        try:
            patch_campaign(campaign_id, data)
            st.success("Campaign updated successfully!")
            return True
        except APIError as e:
            st.error(f"Failed to update campaign: {e.message}")
            return False

    def handle_delete_campaign(campaign_id: int) -> None:
        try:
            delete_campaign(campaign_id)
            st.success("Campaign deleted successfully!")
            st.rerun()
        except APIError as e:
            st.error(f"Failed to delete campaign: {e.message}")
    ```
  </action>
  <verify>uv run python -c "import ast; ast.parse(open('app/pages/3_Campaigns.py').read()); print('syntax OK')"</verify>
  <done>Campaigns page uses form-based CRUD with site and campaign type dropdowns populated from API lookups</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    Form-based CRUD redesign complete for all three reference data pages:
    
    **API Changes**:
    - PATCH endpoints for Sites, Equipment, Campaigns (/api/v1/{entity}/{id})
    - Lookup endpoints: /sites/lookup/list, /campaigns/types, /equipment/models/lookup
    
    **App Components**:
    - `app/components/crud_form.py` - Form field rendering utilities
    - `app/components/form_dialog.py` - Modal form dialogs with Validate/Send buttons
    
    **Pages**:
    - `app/pages/1_Sites.py` - Table display with New/Edit/Delete buttons, form dialogs
    - `app/pages/2_Equipment.py` - Same pattern with equipment model dropdown
    - `app/pages/3_Campaigns.py` - Same pattern with site and campaign type dropdowns, site filter
    
    **Pattern**: Select row → Edit (or New) → Form dialog → Validate/Send → Refresh
  </what-built>
  <how-to-verify>
    1. Start the API: `uv run uvicorn api.main:app --reload`
    2. Start the app: `uv run streamlit run app/Home.py`
    3. Log in with any username/password
    4. Navigate to **Sites** page:
       - Table displays with row selection
       - Click "New" → Create form dialog opens
       - Fill required Name field, click "Send" → Site created
       - Select a row, click "Edit" → Edit form pre-populated
       - Change name, click "Send" → Site updated
       - Verify "Validate" button shows validation errors for missing required fields
    5. Navigate to **Equipment** page:
       - Click "New" → Equipment model dropdown shows "Manufacturer - Model Name"
       - Select model, fill identifier, click "Send" → Equipment created
       - Verify model_id stored correctly (raw ID), displayed as friendly name
    6. Navigate to **Campaigns** page:
       - Site filter dropdown at top
       - Click "New" → Both Site and Campaign Type show friendly names in dropdowns
       - Create campaign with site and type → Verify FKs stored correctly
    7. Confirm all pages: required fields marked with (*), FKs show names not IDs
  </how-to-verify>
  <resume-signal>Type "approved" to complete Phase 02, or describe issues to fix</resume-signal>
</task>

</tasks>

<verification>
Before declaring plan complete:
- [ ] All PATCH endpoints return 200 with partial updates
- [ ] All lookup endpoints return id+name pairs < 100ms
- [ ] `uv run python -c "import app.components.crud_form; import app.components.form_dialog"` passes
- [ ] All three pages pass syntax check
- [ ] `uv run pytest tests/unit/ -q` still passes
- [ ] Human verification checkpoint approved
</verification>

<success_criteria>
- Form-based CRUD pattern replaces inline editing on all three pages
- PATCH endpoints support partial updates for all entities
- Lookup endpoints provide FK dropdown data with friendly names
- Required fields marked with (*) in forms
- Validation button shows errors clearly
- Send button submits via POST (create) or PATCH (update)
- Phase 02 complete with user-approved UX
</success_criteria>

<output>
After completion, create `.planning/phases/02-crud-reference/02-04-SUMMARY.md`:

# Phase 02 Plan 04: Form-Based CRUD + Equipment + Campaigns Summary

**Form-based CRUD pattern with dialog forms, FK dropdowns, and PATCH partial updates for all reference data pages**

## Accomplishments

## Files Created/Modified

## Decisions Made

## Issues Encountered

## Next Step

Phase 02 complete. Ready for Phase 03: CRUD Pages — Core Entities.
</output>
