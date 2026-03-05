---
status: resolved
trigger: "TypeError: combine() argument 1 must be datetime.date, not None when opening new annotation form"
created: 2026-03-05T00:00:00Z
updated: 2026-03-05T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - render_form_field doesn't handle None values for datetime fields, causing datetime.combine to fail
test: Read crud_form.py lines 44-55 and verify the issue
expecting: st.date_input returns None when value is None, then datetime.combine fails
next_action: Apply fix to handle None date_val before calling datetime.combine

## Symptoms

expected: New annotation form should open without errors, datetime fields should handle empty/null values gracefully
actual: TypeError is raised when form tries to render a datetime field with None value
errors: TypeError: combine() argument 1 must be datetime.date, not None at File "/Users/jeandavidt/Developer/modelEAU/open_dateaubase/app/components/crud_form.py", line 55: return datetime.datetime.combine(date_val, time_val)
reproduction: Open the new annotation form in Annotations page - error occurs in render_form_field when handling datetime field with None value
started: Issue occurs when opening form with empty datetime fields

## Eliminated

## Evidence

- timestamp: 2026-03-05T00:00:00Z
  checked: crud_form.py lines 44-55
  found: datetime field handling code - st.date_input called with value=None returns None, then datetime.combine(date_val, time_val) fails because date_val is None
  implication: Need to check if date_val is None before calling datetime.combine

- timestamp: 2026-03-05T00:00:00Z
  checked: form_dialog.py line 50
  found: form_data[field["name"]] = render_form_field(...) is called without passing a value for new forms
  implication: value parameter defaults to None, which triggers the bug in datetime fields

## Resolution

root_cause: In crud_form.py render_form_field(), when field_type is "datetime" and value is None, st.date_input returns None, but datetime.datetime.combine() is called with date_val=None causing TypeError
fix: Add None check for date_val before calling datetime.combine; return None if date_val is None
verification: All app tests pass (13/13), custom verification script confirms fix handles None correctly and maintains correct behavior with valid dates
files_changed:
  - app/components/crud_form.py: Added None check on line 58-59 to handle empty datetime fields
