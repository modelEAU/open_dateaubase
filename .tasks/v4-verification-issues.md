[ x] Campaign wizard: Page 1: ailed to load lookup data: [{'type': 'int_parsing', 'loc': ['path', 'signal_interface_id'], 'msg': 'Input should be a valid integer, unable to parse string as an integer', 'input': 'lookup'}]
[x] Projects: Cannot load data: Internal Server Error
[x] Watersheds: Cannot load data: Internal Server Error
[x] Process Units -> Create: Create Process Units
TypeError: string indices must be integers, not 'str'
Traceback:

File "/app/app/components/form_dialog.py", line 50, in create_form_dialog
    form_data[field["name"]] = render_form_field(
                               ~~~~~~~~~~~~~~~~~^
        field_name=field["name"],
        ^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
        help_text=field.get("help"),
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
File "/app/app/components/crud_form.py", line 27, in render_form_field
    option_map = {opt["label"]: opt["id"] for opt in options}
                  ~~~^^^^^^^^^

[ ] Data Acquisition Systems: Cannot load data: Not Found
[ ] Channels: Cannot load lookup data: [{'type': 'int_parsing', 'loc': ['path', 'signal_interface_id'], 'msg': 'Input should be a valid integer, unable to parse string as an integer', 'input': 'lookup'}]
[ ] Procedures: Cannot load data: Internal Server Error
[ ] Signal Interfaces:  Cannot load data: Not Found
[ ] Signal Interface Port Kinds: Cannot load data: Not Found
[ ] Process Unit Types: KeyError: 'process_unit_type_id' Traceback:

File "/app/app/Home.py", line 142, in <module>
    pg.run()
    ~~~~~~^^
File "/app/.venv/lib/python3.13/site-packages/streamlit/navigation/page.py", line 380, in run
    exec(code, module.__dict__)  # noqa: S102
    ~~~~^^^^^^^^^^^^^^^^^^^^^^^
File "/app/app/pages/process_unit_types.py", line 23, in <module>
    render_crud_page(
    ~~~~~~~~~~~~~~~~^
        title="Process Unit Types",
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<9 lines>...
        label_field="name",
        ^^^^^^^^^^^^^^^^^^^
    )
    ^
File "/app/app/components/generic_crud.py", line 83, in render_crud_page
    df = pd.DataFrame(items).sort_values(pk_field).reset_index(drop=True)
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^
File "/app/.venv/lib/python3.13/site-packages/pandas/core/frame.py", line 7211, in sort_values
    k = self._get_label_or_level_values(by[0], axis=axis)
File "/app/.venv/lib/python3.13/site-packages/pandas/core/generic.py", line 1914, in _get_label_or_level_values
    raise KeyError(key)
[ ] Purposes:  Cannot load data: Internal Server Error

Equipment Move -> Change Wiring: Cannot load signal interfaces: [{'type': 'int_parsing', 'loc': ['path', 'signal_interface_id'], 'msg': 'Input should be a valid integer, unable to parse string as an integer', 'input': 'lookup'}]

[ ] Port Kinds: I;m not sure what this is for.
[ ] Interface types is not required. Can be removed along with the type field in signal interfaces.
[ ] The EquipmentModels page should show what parameters an equipment model is able to measure, and the editor view should let you make those associations.