# Checkpoint Feedback Summary: 02-04 Form-Based CRUD Redesign

**Date**: 2026-03-05  
**Plan**: 02-04 (Equipment + Campaigns Pages + Verify)  
**Checkpoint**: Task 3 - Human Verification  
**Status**: Feedback received, gap closure plan created

---

## User Feedback Summary

### Original Approach
Inline data editor (`st.data_editor`) was implemented for all CRUD operations:
- ✅ **READ**: Works well - table displays data effectively
- ✅ **DELETE**: Works well - row deletion is intuitive
- ❌ **CREATE**: Needs form-based interface - inline row addition is confusing for FK fields
- ❌ **UPDATE**: Needs form-based interface - inline editing shows raw IDs instead of friendly names

### Key Issues Identified

1. **Foreign Key Fields**: Showing raw IDs (e.g., `site_id: 5`) instead of friendly names (e.g., "Main Campus River") is not user-friendly for graduate students
2. **No Dropdown Support**: `st.data_editor` cannot render dropdowns populated from related tables
3. **Validation**: Inline editing makes it hard to show validation errors clearly
4. **Complex Forms**: Sites, Equipment, and Campaigns have multiple fields - inline editing is cramped

### Required Changes

| Requirement | Current | Target |
|-------------|---------|--------|
| New Item | Add row in table | "New" button → form dialog |
| Edit Item | Edit cell inline | Select row → "Edit" → form dialog |
| FK Display | Raw IDs | Dropdown with friendly names |
| Required Fields | No visual indicator | Red star (*) marker |
| Validation | Error on save | "Validate" button shows errors |
| Submit | Auto-save on edit | "Send" button submits form |
| HTTP Method | POST/PUT | POST (create), PATCH (update) |

---

## Gap Closure Plan Created

**File**: `.planning/phases/02-crud-reference/02-04-GAP-CLOSURE.md`

### Scope
Comprehensive redesign of all three reference data pages (Sites, Equipment, Campaigns) to use form-based CRUD pattern.

### Tasks (8 Total)

#### API Layer (Tasks 1-2)
1. **Add PATCH endpoints** for partial updates on Sites, Equipment, Campaigns
2. **Add lookup endpoints** for FK dropdowns:
   - `GET /sites/lookup/list` - id + name for site dropdowns
   - `GET /campaigns/types` - all campaign types
   - `GET /equipment/models/lookup` - model_id + name + manufacturer

#### Component Layer (Tasks 3-4)
3. **Create `crud_form.py`** - Reusable form field rendering with support for:
   - Text, number, date, textarea field types
   - Select dropdowns with id → label mapping
   - Required field validation
   
4. **Create `form_dialog.py`** - Modal form dialogs using `st.dialog`:
   - `create_form_dialog()` - Empty form for new items
   - `edit_form_dialog()` - Pre-populated form for editing
   - "Validate" and "Send" buttons
   - Error display inline

#### API Client (Task 5)
5. **Update `api_client.py`**:
   - Add `patch_site()`, `patch_equipment()`, `patch_campaign()`
   - Add `list_sites_lookup()`, `list_campaign_types()`, `list_equipment_models_lookup()`

#### Page Layer (Tasks 6-8)
6. **Rewrite Sites page** - Table with row selection + New/Edit/Delete buttons
7. **Rewrite Equipment page** - Same pattern with equipment model dropdown
8. **Rewrite Campaigns page** - Same pattern with site and campaign type dropdowns, site filter

### New UX Pattern

```
┌─────────────────────────────────────────┐
│  Sites                        [Sign out]│
├─────────────────────────────────────────┤
│ [➕ New] [✏️ Edit] [🗑️ Delete]          │
│                                         │
│ ┌───────────────────────────────────┐   │
│ │ ID │ Name      │ Type  │ City     │   │
│ ├───────────────────────────────────┤   │
│ │ 1  │ Site A ░░ │ River │ Montreal │ ← │ Selected row
│ │ 2  │ Site B    │ Lake  │ Quebec   │   │
│ └───────────────────────────────────┘   │
└─────────────────────────────────────────┘

User clicks "Edit":
┌─────────────────────────────────────────┐
│ ┌───────────────────────────────────┐   │
│ │         Edit Site: Site A         │   │
│ ├───────────────────────────────────┤   │
│ │ Name * [Site A              ]     │   │
│ │ Type   [River ▼             ]     │   │
│ │ Desc   [Main monitoring...  ]     │   │
│ │ City   [Montreal            ]     │   │
│ ├───────────────────────────────────┤   │
│ │ [Validate] [Send] [Cancel]        │   │
│ └───────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Foreign Key Handling

| Field | Current | Target |
|-------|---------|--------|
| `site_id` | User enters "5" | Dropdown shows "Main Campus River" |
| `campaign_type_id` | User enters "3" | Dropdown shows "Long-term Monitoring" |
| `model_id` | User enters "12" | Dropdown shows "Hach - HQ40d Multiparameter" |

**Mapping**: Form shows friendly labels, converts to IDs for API submission.

---

## State Updates

**STATE.md Updated**:
- Position: At checkpoint, awaiting form-based CRUD redesign
- Decision added: "UI Pattern - REFERENCE DATA: Form-based CRUD (not inline editing)"
- Blocker documented: Checkpoint decision required for gap closure plan
- Next action: Review and approve gap closure plan

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `.planning/STATE.md` | Updated | Checkpoint feedback, position, decisions |
| `.planning/phases/02-crud-reference/02-04-GAP-CLOSURE.md` | Created | Comprehensive redesign plan |

---

## Commit

```
docs(02-04): checkpoint feedback - form-based CRUD gap closure plan

- Document human verification feedback on inline editing pattern
- Create comprehensive gap closure plan for form-based CRUD
- Add PATCH endpoints, lookup endpoints, and form components
- Update STATE.md with checkpoint position and feedback summary
```

**Hash**: `16b2a8e`

---

## Next Steps

1. **Review Gap Closure Plan**: User reviews `.planning/phases/02-crud-reference/02-04-GAP-CLOSURE.md`
2. **Decision**: Approve plan or request modifications
3. **Execution**: Execute tasks 1-8 from gap closure plan
4. **Verification**: Human verification checkpoint after all tasks complete
5. **Complete Phase 02**: Proceed to Phase 03 (Core Entities)

---

## Impact Assessment

| Aspect | Impact | Notes |
|--------|--------|-------|
| **Timeline** | +1-2 days | Additional API endpoints + component development |
| **User Experience** | Significant improvement | Graduate students can use dropdowns, see friendly names |
| **Code Reusability** | High | `crud_form.py` and `form_dialog.py` reusable for Phase 03 |
| **API Changes** | Moderate | New PATCH and lookup endpoints needed |
| **Breaking Changes** | None | New endpoints, existing ones unchanged |

---

## Design Rationale

**Why form-based instead of inline?**

1. **User Profile**: Graduate students are domain experts but not database experts - they think in "Site Name" not "site_id"
2. **FK Complexity**: Reference data has many foreign keys - inline editing requires users to know IDs by heart
3. **Validation**: Forms allow pre-submission validation with clear error messages
4. **Future-Proofing**: Form components will be reused for Core Entities (Channels, Annotations) which have even more FK relationships

**Why PATCH instead of PUT?**
- Partial updates are more appropriate for form submissions where users may change only one field
- Consistent with REST best practices for partial resource modification

**Why lookup endpoints?**
- Decouples UI from database structure
- Allows caching of reference data
- Supports future autocomplete/search features
