USE proposed_2025_11;
GO

-- 1. Unit
INSERT INTO unit (Unit_ID, Unit)
VALUES (1, N'mg/L');

-- 2. Parameter (lié à Unit_ID = 1)
INSERT INTO parameter (Parameter_ID, Parameter, Unit_ID, Description)
VALUES (1, N'NH4', 1, N'Ammonium');

-- 3. Purpose
INSERT INTO purpose (Purpose_ID, Purpose, Description)
VALUES (1, N'measurement', N'Measurement for testing');

-- 4. Project
INSERT INTO project (Project_ID, Project_name, Description)
VALUES (1, N'Test project', N'API dev test project');

-- 5. Equipment_model
INSERT INTO equipment_model (
    Equipment_model_ID, Equipment_model, Method, Functions, Manufacturer, Manual_location
)
VALUES (
    1, N'Test_model', N'test', N'test', N'test', N'test'
);

-- 6. Equipment (référence Equipment_model_ID = 1)
INSERT INTO equipment (
    Equipment_ID, Equipment_identifier, Serial_number, Owner,
    Storage_location, Purchase_date, Equipment_model_ID
)
VALUES (
    1, N'Test_eq', N'SN-001', N'Owner',
    N'Lab', '2025-01-01', 1
);

-- 7. Watershed
INSERT INTO watershed (
    Watershed_ID, Watershed_name, Description, Surface_area, Concentration_time, Impervious_surface
)
VALUES (
    1, N'Test_ws', N'test', 1.0, 1, 1.0
);

-- 8. Site (référence Watershed_ID = 1)
INSERT INTO site (
    Site_ID, Site_name, Site_type, Watershed_ID, Description,
    Picture, Street_number, Street_name, City, Zip_code, Province, Country
)
VALUES (
    1, N'Test_site', N'test', 1, N'test',
    NULL, N'1', N'Test St', N'Quebec', N'G1K1A1', N'QC', N'Canada'
);

-- 9. Sampling_point (référence Site_ID = 1)
INSERT INTO sampling_points (
    Sampling_point_ID, Sampling_point, Sampling_location,
    Site_ID, Latitude_GPS, Longitude_GPS, Description, Pictures
)
VALUES (
    1, N'SP1', N'Inlet',
    1, N'0', N'0', N'test', NULL
);

-- 10. Metadata_ID = 1
INSERT INTO metadata (
    Metadata_ID, Parameter_ID, Unit_ID, Purpose_ID,
    Equipment_ID, Procedure_ID, Condition_ID,
    Sampling_point_ID, Contact_ID, Project_ID,
    StartDate, EndDate
)
VALUES (
    1, 1, 1, 1,
    1, NULL, NULL,
    1, NULL, 1,
    0, 2147483647
);

-- Vérification
SELECT * FROM metadata WHERE Metadata_ID = 1;
GO
