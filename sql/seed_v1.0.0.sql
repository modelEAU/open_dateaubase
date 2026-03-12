-- Seed data for schema v1.0.0
-- Scenario: Wastewater and stormwater monitoring in Quebec City
-- All timestamps are Unix epoch INTs (v1.0.0 format)

-- =============================================================================
-- Tier 1: Tables with no foreign keys
-- =============================================================================

-- Units of measurement
INSERT INTO [dbo].[Unit] ([Unit]) VALUES ('mg/L');        -- ID 1
INSERT INTO [dbo].[Unit] ([Unit]) VALUES ('NTU');          -- ID 2
INSERT INTO [dbo].[Unit] ([Unit]) VALUES ('pH units');     -- ID 3
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'°C');          -- ID 4
INSERT INTO [dbo].[Unit] ([Unit]) VALUES ('mS/cm');        -- ID 5

-- Watersheds
INSERT INTO [dbo].[Watershed] ([name], [Description], [Surface_area], [Concentration_time], [Impervious_surface])
VALUES ('Riviere Saint-Charles', 'Urban catchment in Quebec City', 550.0, 180, 35.5);  -- ID 1

INSERT INTO [dbo].[Watershed] ([name], [Description], [Surface_area], [Concentration_time], [Impervious_surface])
VALUES ('Riviere Montmorency', 'Rural reference watershed north of Quebec City', 1150.0, 420, 8.2);  -- ID 2

-- Weather conditions
INSERT INTO [dbo].[WeatherCondition] ([Weather_condition], [Description])
VALUES ('Dry', 'No precipitation in the last 48 hours');  -- ID 1

INSERT INTO [dbo].[WeatherCondition] ([Weather_condition], [Description])
VALUES ('Rain', 'Active rainfall event');  -- ID 2

INSERT INTO [dbo].[WeatherCondition] ([Weather_condition], [Description])
VALUES ('Snowmelt', 'Spring snowmelt conditions');  -- ID 3

-- Equipment models
INSERT INTO [dbo].[EquipmentModel] ([Equipment_model], [Method], [Functions], [Manufacturer], [Manual_location])
VALUES ('ISCO 6712', 'Automatic sampling', 'Portable autosampler for wastewater and stormwater', 'Teledyne ISCO', '/manuals/isco_6712.pdf');  -- ID 1

INSERT INTO [dbo].[EquipmentModel] ([Equipment_model], [Method], [Functions], [Manufacturer], [Manual_location])
VALUES ('YSI ProDSS', 'Multi-parameter probe', 'pH, temperature, conductivity, dissolved oxygen', 'YSI/Xylem', '/manuals/ysi_prodss.pdf');  -- ID 2

INSERT INTO [dbo].[EquipmentModel] ([Equipment_model], [Method], [Functions], [Manufacturer], [Manual_location])
VALUES ('Hach 2100Q', 'Nephelometric', 'Portable turbidity meter', 'Hach', '/manuals/hach_2100q.pdf');  -- ID 3

-- Procedures
INSERT INTO [dbo].[Procedures] ([Procedure_name], [Procedure_type], [Description], [Procedure_location])
VALUES ('Grab sampling', 'Sampling', 'Manual grab sample collected at water surface', '/procedures/grab_sampling.pdf');  -- ID 1

INSERT INTO [dbo].[Procedures] ([Procedure_name], [Procedure_type], [Description], [Procedure_location])
VALUES ('24h composite', 'Sampling', 'Time-weighted 24-hour composite sample via autosampler', '/procedures/composite_24h.pdf');  -- ID 2

INSERT INTO [dbo].[Procedures] ([Procedure_name], [Procedure_type], [Description], [Procedure_location])
VALUES ('Online continuous', 'Measurement', 'Continuous in-situ measurement with data logging', '/procedures/online_continuous.pdf');  -- ID 3

-- Projects
INSERT INTO [dbo].[Project] ([name], [Description])
VALUES ('WWTP Inlet Monitoring 2024', 'Routine monitoring of wastewater treatment plant influent quality');  -- ID 1

INSERT INTO [dbo].[Project] ([name], [Description])
VALUES ('CSO Event Study 2024', 'Combined sewer overflow characterization during rain events');  -- ID 2

-- Purposes
INSERT INTO [dbo].[Purpose] ([Purpose], [Description])
VALUES ('Routine monitoring', 'Regular scheduled sampling for compliance and process control');  -- ID 1

INSERT INTO [dbo].[Purpose] ([Purpose], [Description])
VALUES ('Event-based sampling', 'Triggered sampling during wet weather or snowmelt events');  -- ID 2

-- Comments (QA/QC notes)
INSERT INTO [dbo].[Comments] ([Comment]) VALUES ('Sample collected under normal conditions');          -- ID 1
INSERT INTO [dbo].[Comments] ([Comment]) VALUES ('High turbidity observed - possible equipment drift');  -- ID 2
INSERT INTO [dbo].[Comments] ([Comment]) VALUES ('Duplicate sample collected for QA/QC');               -- ID 3
INSERT INTO [dbo].[Comments] ([Comment]) VALUES (NULL);                                                 -- ID 4 (no comment)

-- Hydrological characteristics (one per watershed)
INSERT INTO [dbo].[HydrologicalCharacteristics] ([Urban_area], [Forest], [Wetlands], [Cropland], [Meadow], [Grassland])
VALUES (35.5, 25.0, 5.0, 10.0, 12.5, 12.0);  -- Watershed 1 (urban)

INSERT INTO [dbo].[HydrologicalCharacteristics] ([Urban_area], [Forest], [Wetlands], [Cropland], [Meadow], [Grassland])
VALUES (8.2, 55.0, 12.0, 15.0, 5.0, 4.8);    -- Watershed 2 (rural)

-- Urban characteristics (one per watershed)
INSERT INTO [dbo].[UrbanCharacteristics] ([Commercial], [Green_spaces], [Industrial], [Institutional], [Residential], [Agricultural], [Recreational])
VALUES (15.0, 8.0, 12.0, 5.0, 45.0, 5.0, 10.0);   -- Watershed 1 (urban)

INSERT INTO [dbo].[UrbanCharacteristics] ([Commercial], [Green_spaces], [Industrial], [Institutional], [Residential], [Agricultural], [Recreational])
VALUES (2.0, 3.0, 1.0, 1.0, 60.0, 28.0, 5.0);      -- Watershed 2 (rural)

-- =============================================================================
-- Tier 2: Tables with FKs to Tier 1
-- =============================================================================

-- Contacts
INSERT INTO [dbo].[Contact] ([Last_name], [First_name], [Company], [Status], [Function], [Office_number], [Email], [Phone], [City], [Zip_code], [Country])
VALUES ('Tremblay', 'Marie', N'Universite Laval - modelEAU', 'Active', 'Research Associate', 'PLT-2910', 'marie.tremblay@ulaval.ca', '418-555-0101', N'Quebec', 'G1V 0A6', 'Canada');  -- ID 1

INSERT INTO [dbo].[Contact] ([Last_name], [First_name], [Company], [Status], [Function], [Office_number], [Email], [Phone], [City], [Zip_code], [Country])
VALUES ('Gagnon', 'Pierre', N'Universite Laval - modelEAU', 'Active', 'PhD Student', 'PLT-2912', 'pierre.gagnon@ulaval.ca', '418-555-0102', N'Quebec', 'G1V 0A6', 'Canada');  -- ID 2

-- Equipment instances
INSERT INTO [dbo].[Equipment] ([model_ID], [identifier], [Serial_number], [Owner], [Storage_location], [Purchase_date])
VALUES (1, 'ISCO-001', 'SN-6712-2021-001', N'modelEAU Lab', 'PLT-2900 Storage', '2021-03-15');  -- ID 1

INSERT INTO [dbo].[Equipment] ([model_ID], [identifier], [Serial_number], [Owner], [Storage_location], [Purchase_date])
VALUES (2, 'YSI-001', 'SN-PRODSS-2022-045', N'modelEAU Lab', 'PLT-2900 Storage', '2022-06-01');  -- ID 2

INSERT INTO [dbo].[Equipment] ([model_ID], [identifier], [Serial_number], [Owner], [Storage_location], [Purchase_date])
VALUES (3, 'HACH-001', 'SN-2100Q-2020-112', N'modelEAU Lab', 'PLT-2900 Storage', '2020-09-20');  -- ID 3

-- Parameters (water quality)
INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description])
VALUES (1, 'TSS', 'Total suspended solids');  -- ID 1

INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description])
VALUES (1, 'COD', 'Chemical oxygen demand');  -- ID 2

INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description])
VALUES (3, 'pH', 'Hydrogen ion concentration');  -- ID 3

INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description])
VALUES (4, 'Temperature', 'Water temperature');  -- ID 4

INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description])
VALUES (5, 'Conductivity', 'Electrical conductivity');  -- ID 5

-- Sites
INSERT INTO [dbo].[Site] ([Watershed_ID], [name], [type], [Description], [Street_number], [Street_name], [City], [Province], [Country])
VALUES (1, 'WWTP Est Inlet', 'Wastewater treatment plant', 'Main inlet of the eastern WWTP', '500', 'Boulevard des Capucins', N'Quebec', N'Quebec', 'Canada');  -- ID 1

INSERT INTO [dbo].[Site] ([Watershed_ID], [name], [type], [Description], [Street_number], [Street_name], [City], [Province], [Country])
VALUES (1, 'CSO Outfall 12', 'Combined sewer overflow', 'CSO outfall discharging to Riviere Saint-Charles', '120', 'Rue du Pont', N'Quebec', N'Quebec', 'Canada');  -- ID 2

-- =============================================================================
-- Tier 3: Tables with FKs to Tier 2
-- =============================================================================

-- Sampling points
INSERT INTO [dbo].[SamplingPoints] ([Site_ID], [Sampling_point], [Sampling_location], [Latitude_GPS], [Longitude_GPS], [Description])
VALUES (1, 'WWTP-IN-01', 'Inlet channel after screening', '46.8310', '-71.2080', 'Primary sampling point at plant inlet');  -- ID 1

INSERT INTO [dbo].[SamplingPoints] ([Site_ID], [Sampling_point], [Sampling_location], [Latitude_GPS], [Longitude_GPS], [Description])
VALUES (1, 'WWTP-OUT-01', 'Final effluent discharge', '46.8315', '-71.2075', 'Effluent sampling point after disinfection');  -- ID 2

INSERT INTO [dbo].[SamplingPoints] ([Site_ID], [Sampling_point], [Sampling_location], [Latitude_GPS], [Longitude_GPS], [Description])
VALUES (2, 'CSO-12-OUT', 'Overflow pipe outlet', '46.8200', '-71.2250', 'CSO overflow discharge point');  -- ID 3

-- Junction tables: Equipment model capabilities
INSERT INTO [dbo].[EquipmentModelHasParameter] ([Equipment_model_ID], [Parameter_ID]) VALUES (1, 1);  -- ISCO -> TSS (collects samples for TSS)
INSERT INTO [dbo].[EquipmentModelHasParameter] ([Equipment_model_ID], [Parameter_ID]) VALUES (1, 2);  -- ISCO -> COD
INSERT INTO [dbo].[EquipmentModelHasParameter] ([Equipment_model_ID], [Parameter_ID]) VALUES (2, 3);  -- YSI -> pH
INSERT INTO [dbo].[EquipmentModelHasParameter] ([Equipment_model_ID], [Parameter_ID]) VALUES (2, 4);  -- YSI -> Temperature
INSERT INTO [dbo].[EquipmentModelHasParameter] ([Equipment_model_ID], [Parameter_ID]) VALUES (2, 5);  -- YSI -> Conductivity

-- Junction tables: Equipment model procedures
INSERT INTO [dbo].[EquipmentModelHasProcedures] ([Equipment_model_ID], [Procedure_ID]) VALUES (1, 2);  -- ISCO -> 24h composite
INSERT INTO [dbo].[EquipmentModelHasProcedures] ([Equipment_model_ID], [Procedure_ID]) VALUES (2, 3);  -- YSI -> Online continuous
INSERT INTO [dbo].[EquipmentModelHasProcedures] ([Equipment_model_ID], [Procedure_ID]) VALUES (3, 1);  -- Hach -> Grab sampling

-- Junction tables: Parameter procedures
INSERT INTO [dbo].[ParameterHasProcedures] ([Procedure_ID], [Parameter_ID]) VALUES (1, 1);  -- Grab -> TSS
INSERT INTO [dbo].[ParameterHasProcedures] ([Procedure_ID], [Parameter_ID]) VALUES (2, 2);  -- 24h composite -> COD
INSERT INTO [dbo].[ParameterHasProcedures] ([Procedure_ID], [Parameter_ID]) VALUES (3, 3);  -- Online -> pH
INSERT INTO [dbo].[ParameterHasProcedures] ([Procedure_ID], [Parameter_ID]) VALUES (3, 4);  -- Online -> Temperature

-- =============================================================================
-- Tier 4: MetaData (central hub)
-- =============================================================================

-- MetaData row 1: WWTP inlet TSS, routine monitoring, grab sample
INSERT INTO [dbo].[MetaData] ([Project_ID], [Contact_ID], [Equipment_ID], [Parameter_ID], [Procedure_ID], [Unit_ID], [Purpose_ID], [Sampling_point_ID], [Condition_ID])
VALUES (1, 1, 1, 1, 1, 1, 1, 1, 1);  -- ID 1

-- MetaData row 2: WWTP inlet COD, routine monitoring, 24h composite
INSERT INTO [dbo].[MetaData] ([Project_ID], [Contact_ID], [Equipment_ID], [Parameter_ID], [Procedure_ID], [Unit_ID], [Purpose_ID], [Sampling_point_ID], [Condition_ID])
VALUES (1, 1, 1, 2, 2, 1, 1, 1, 1);  -- ID 2

-- MetaData row 3: WWTP inlet pH, online continuous (some FKs NULL)
INSERT INTO [dbo].[MetaData] ([Project_ID], [Contact_ID], [Equipment_ID], [Parameter_ID], [Procedure_ID], [Unit_ID], [Purpose_ID], [Sampling_point_ID], [Condition_ID])
VALUES (1, 2, 2, 3, 3, 3, 1, 1, NULL);  -- ID 3 (no weather condition)

-- MetaData row 4: CSO overflow TSS, event-based sampling
INSERT INTO [dbo].[MetaData] ([Project_ID], [Contact_ID], [Equipment_ID], [Parameter_ID], [Procedure_ID], [Unit_ID], [Purpose_ID], [Sampling_point_ID], [Condition_ID])
VALUES (2, 2, 1, 1, 1, 1, 2, 3, 2);  -- ID 4

-- MetaData row 5: WWTP effluent TSS (minimal FKs to test NULLs)
INSERT INTO [dbo].[MetaData] ([Project_ID], [Contact_ID], [Equipment_ID], [Parameter_ID], [Procedure_ID], [Unit_ID], [Purpose_ID], [Sampling_point_ID], [Condition_ID])
VALUES (1, NULL, NULL, 1, 1, 1, 1, 2, NULL);  -- ID 5 (no contact, no equipment)

-- MetaData row 6: Temperature, online continuous
INSERT INTO [dbo].[MetaData] ([Project_ID], [Contact_ID], [Equipment_ID], [Parameter_ID], [Procedure_ID], [Unit_ID], [Purpose_ID], [Sampling_point_ID], [Condition_ID])
VALUES (1, 2, 2, 4, 3, 4, 1, 1, 1);  -- ID 6

-- Junction tables: Project relationships
INSERT INTO [dbo].[ProjectHasContact] ([Contact_ID], [Project_ID]) VALUES (1, 1);
INSERT INTO [dbo].[ProjectHasContact] ([Contact_ID], [Project_ID]) VALUES (2, 1);
INSERT INTO [dbo].[ProjectHasContact] ([Contact_ID], [Project_ID]) VALUES (2, 2);

INSERT INTO [dbo].[ProjectHasEquipment] ([Equipment_ID], [Project_ID]) VALUES (1, 1);
INSERT INTO [dbo].[ProjectHasEquipment] ([Equipment_ID], [Project_ID]) VALUES (2, 1);
INSERT INTO [dbo].[ProjectHasEquipment] ([Equipment_ID], [Project_ID]) VALUES (3, 1);
INSERT INTO [dbo].[ProjectHasEquipment] ([Equipment_ID], [Project_ID]) VALUES (1, 2);

INSERT INTO [dbo].[ProjectHasSamplingPoints] ([Project_ID], [Sampling_point_ID]) VALUES (1, 1);
INSERT INTO [dbo].[ProjectHasSamplingPoints] ([Project_ID], [Sampling_point_ID]) VALUES (1, 2);
INSERT INTO [dbo].[ProjectHasSamplingPoints] ([Project_ID], [Sampling_point_ID]) VALUES (2, 3);

-- =============================================================================
-- Tier 5: Value (measurements)
-- Timestamps are Unix epoch seconds (INT) for v1.0.0
-- =============================================================================

-- TSS at WWTP inlet (Metadata_ID=1), dry weather
-- 2024-01-15 08:00 EST = 1705320000
-- 2024-01-15 14:00 EST = 1705341600
-- 2024-01-16 08:00 EST = 1705406400
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (1, 1, 185.0, 1, 1705320000);   -- ID 1
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 1, 210.5, 2, 1705341600);  -- ID 2
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (1, 1, 192.3, 3, 1705406400);   -- ID 3

-- COD at WWTP inlet (Metadata_ID=2), 24h composite
-- 2024-01-15 00:00 to 2024-01-16 00:00
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 2, 450.0, 1, 1705291200);  -- ID 4  (2024-01-15 00:00 EST)
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 2, 520.8, 2, 1705377600);  -- ID 5  (2024-01-16 00:00 EST)

-- pH online continuous (Metadata_ID=3)
-- 2024-01-15 every 4 hours
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 3, 7.2, 1, 1705291200);   -- ID 6
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 3, 7.1, 2, 1705305600);   -- ID 7
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 3, 6.9, 3, 1705320000);   -- ID 8
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (2, 3, 7.8, 4, 1705334400);      -- ID 9  (flagged: equipment drift)

-- CSO overflow TSS during rain (Metadata_ID=4)
-- 2024-03-20 rain event
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 4, 350.0, 1, 1710936000);  -- ID 10 (2024-03-20 12:00 EST)
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 4, 580.2, 2, 1710943200);  -- ID 11 (2024-03-20 14:00 EST)
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (3, 4, 345.0, 3, 1710943200);     -- ID 12 (duplicate for QA/QC)

-- WWTP effluent TSS (Metadata_ID=5)
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 5, 12.5, 1, 1705320000);   -- ID 13
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 5, 15.0, 2, 1705406400);   -- ID 14

-- Temperature online (Metadata_ID=6)
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 6, 12.3, 1, 1705291200);   -- ID 15
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 6, 12.1, 2, 1705305600);   -- ID 16
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 6, 11.8, 3, 1705320000);   -- ID 17

-- Value with NULL timestamp (edge case for migration testing)
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (4, 1, 200.0, NULL, NULL);         -- ID 18 (no timestamp, no experiment number)
