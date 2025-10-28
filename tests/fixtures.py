import pytest

@pytest.fixture
def sample_csv_data():
    """Create sample CSV data for testing - NEW FORMAT with parentKey support."""
    # This fixture demonstrates the new dictionary structure:
    # - TestTable_ID is the primary key
    # - Name, Status are regular non-prefixed fields
    # - Parent_ID is a parentKey that references TestTable_ID
    # - StatusSet is a value set with two members
    csv_content = """Part_ID,Label,Description,Part_type,Value_set_part_ID,Member_of_set_part_ID,Ancestor_part_ID,SQL_data_type,Is_required,Default_value,Sort_order,TestTable_present,TestTable_required,TestTable_order
TestTable,Test Table,A test table,table,,,,,,,,,,
TestTable_ID,Test Table ID,Identifier for TestTable,key,,,,int,True,,1,key,True,1
Name,Name,Name field,property,,,,nvarchar(255),True,,2,property,True,2
Status,Status,Status field,property,StatusSet,,,nvarchar(50),False,,3,property,False,3
Parent_ID,Parent ID,Hierarchical reference to parent TestTable,parentKey,,,TestTable_ID,int,False,,4,property,False,4
StatusSet,Status Set,Valid status values,valueSet,,,,,,,,
active,Active,Active status,valueSetMember,,StatusSet,,nvarchar(50),,,1,,
inactive,Inactive,Inactive status,valueSetMember,,StatusSet,,nvarchar(50),,,2,,
"""
    return csv_content
