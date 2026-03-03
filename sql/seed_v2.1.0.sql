-- ============================================================
-- Seed data for schema v2.1.0
-- Scenario: Wastewater and stormwater monitoring in Quebec City
--
-- Timestamps are UTC throughout.
-- Preserves the same Equipment_ID, Parameter_ID, Unit_ID, and
-- SamplingPoint IDs as the archived v1.0.0 seed so that test
-- expectations remain stable.
-- ============================================================

SET NOCOUNT ON;

-- ============================================================
-- TIER 0: Tables with no foreign keys
-- ============================================================

-- Units of measurement (IDs 1-8 match v1.0.0/v1.1.0 seeds; ID 9 is new)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'mg/L');       -- ID 1
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'NTU');        -- ID 2
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'pH units');   -- ID 3
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'°C');         -- ID 4
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'mS/cm');      -- ID 5
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'nm');         -- ID 6: nanometres (UV-Vis wavelength axis)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'µm');         -- ID 7: micrometres (particle size axis)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'm/s');        -- ID 8: metres per second (velocity axis)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'Status Code'); -- ID 9: integer status codes

-- Watersheds (IDs match v1.0.0 seed)
INSERT INTO [dbo].[Watershed] ([Name], [Description], [SurfaceArea], [ConcentrationTime], [ImperviousSurface])
VALUES (N'Riviere Saint-Charles', N'Urban catchment in Quebec City', 550.0, 180, 35.5);  -- ID 1

INSERT INTO [dbo].[Watershed] ([Name], [Description], [SurfaceArea], [ConcentrationTime], [ImperviousSurface])
VALUES (N'Riviere Montmorency', N'Rural reference watershed north of Quebec City', 1150.0, 420, 8.2);  -- ID 2

-- Weather conditions
INSERT INTO [dbo].[WeatherCondition] ([WeatherCondition], [Description]) VALUES (N'Dry', N'No precipitation in the last 48 hours');    -- ID 1
INSERT INTO [dbo].[WeatherCondition] ([WeatherCondition], [Description]) VALUES (N'Rain', N'Active rainfall event');                   -- ID 2
INSERT INTO [dbo].[WeatherCondition] ([WeatherCondition], [Description]) VALUES (N'Snowmelt', N'Spring snowmelt conditions');           -- ID 3

-- Equipment models (IDs match v1.0.0 seed)
INSERT INTO [dbo].[EquipmentModel] ([EquipmentModel], [Method], [Functions], [Manufacturer], [ManualLocation])
VALUES (N'ISCO 6712', N'Automatic sampling', N'Portable autosampler for wastewater and stormwater', N'Teledyne ISCO', N'/manuals/isco_6712.pdf');  -- ID 1

INSERT INTO [dbo].[EquipmentModel] ([EquipmentModel], [Method], [Functions], [Manufacturer], [ManualLocation])
VALUES (N'YSI ProDSS', N'Multi-parameter probe', N'pH, temperature, conductivity, dissolved oxygen', N'YSI/Xylem', N'/manuals/ysi_prodss.pdf');  -- ID 2

INSERT INTO [dbo].[EquipmentModel] ([EquipmentModel], [Method], [Functions], [Manufacturer], [ManualLocation])
VALUES (N'Hach 2100Q', N'Nephelometric', N'Portable turbidity meter', N'Hach', N'/manuals/hach_2100q.pdf');  -- ID 3

-- Procedures (IDs match v1.0.0 seed)
INSERT INTO [dbo].[Procedures] ([ProcedureName], [ProcedureType], [Description], [ProcedureLocation])
VALUES (N'Grab sampling', N'Sampling', N'Manual grab sample collected at water surface', N'/procedures/grab_sampling.pdf');  -- ID 1

INSERT INTO [dbo].[Procedures] ([ProcedureName], [ProcedureType], [Description], [ProcedureLocation])
VALUES (N'24h composite', N'Sampling', N'Time-weighted 24-hour composite sample via autosampler', N'/procedures/composite_24h.pdf');  -- ID 2

INSERT INTO [dbo].[Procedures] ([ProcedureName], [ProcedureType], [Description], [ProcedureLocation])
VALUES (N'Online continuous', N'Measurement', N'Continuous in-situ measurement with data logging', N'/procedures/online_continuous.pdf');  -- ID 3

-- Hydrological characteristics (one row per watershed; IDs match Watershed IDs)
INSERT INTO [dbo].[HydrologicalCharacteristics] ([UrbanArea], [Forest], [Wetlands], [Cropland], [Meadow], [Grassland])
VALUES (35.5, 25.0, 5.0, 10.0, 12.5, 12.0);  -- Watershed 1 (urban)

INSERT INTO [dbo].[HydrologicalCharacteristics] ([UrbanArea], [Forest], [Wetlands], [Cropland], [Meadow], [Grassland])
VALUES (8.2, 55.0, 12.0, 15.0, 5.0, 4.8);    -- Watershed 2 (rural)

-- Urban characteristics
INSERT INTO [dbo].[UrbanCharacteristics] ([Commercial], [GreenSpaces], [Industrial], [Institutional], [Residential], [Agricultural], [Recreational])
VALUES (15.0, 8.0, 12.0, 5.0, 45.0, 5.0, 10.0);   -- Watershed 1

INSERT INTO [dbo].[UrbanCharacteristics] ([Commercial], [GreenSpaces], [Industrial], [Institutional], [Residential], [Agricultural], [Recreational])
VALUES (2.0, 3.0, 1.0, 1.0, 60.0, 28.0, 5.0);      -- Watershed 2

-- ============================================================
-- TIER 1: ValueBinningAxis / ValueBin (from v1.1.0 seed)
-- ============================================================

INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID])
VALUES (N'S::CAN spectro::lyser UV-Vis', N'UV-Vis absorption spectrometer 200-750 nm, 7 representative bins', 7, 6);   -- ID 1
INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID])
VALUES (N'LISST-200X particle size', N'Volume-equivalent spherical diameter fractionation, 4 size classes', 4, 7);      -- ID 2
INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID])
VALUES (N'FlowCam particle velocity', N'Settling velocity fractionation for joint size-velocity distribution', 2, 8);   -- ID 3

-- UV-Vis bins (AxisID=1)
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (1, 0,   197.5, 202.5);    -- ID 1
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (1, 10,  219.1, 224.1);    -- ID 2
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (1, 50,  305.3, 310.3);    -- ID 3
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (1, 100, 413.2, 418.2);    -- ID 4
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (1, 150, 521.0, 526.0);    -- ID 5
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (1, 200, 628.9, 633.9);    -- ID 6
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (1, 255, 747.5, 752.5);    -- ID 7
-- Particle size bins (AxisID=2)
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (2, 0, 0.0,    63.0);      -- ID 8
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (2, 1, 63.0,   125.0);     -- ID 9
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (2, 2, 125.0,  250.0);     -- ID 10
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (2, 3, 250.0,  10000.0);   -- ID 11
-- Velocity bins (AxisID=3)
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (3, 0, 0.0, 0.5);          -- ID 12
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound]) VALUES (3, 1, 0.5, 2.0);          -- ID 13

-- ============================================================
-- TIER 2: Site, Person, Equipment, Parameter, Laboratory
-- ============================================================

-- Sites (IDs match v1.0.0 seed)
INSERT INTO [dbo].[Site] ([Watershed_ID], [Name], [Type], [Description], [LatitudeWGS84], [LongitudeWGS84], [StreetNumber], [StreetName], [City], [Province], [Country])
VALUES (1, N'WWTP Est Inlet', N'Wastewater treatment plant', N'Main inlet of the eastern WWTP', 46.8312, -71.2077, N'500', N'Boulevard des Capucins', N'Quebec', N'Quebec', N'Canada');  -- ID 1

INSERT INTO [dbo].[Site] ([Watershed_ID], [Name], [Type], [Description], [LatitudeWGS84], [LongitudeWGS84], [StreetNumber], [StreetName], [City], [Province], [Country])
VALUES (1, N'CSO Outfall 12', N'Combined sewer overflow', N'CSO outfall discharging to Riviere Saint-Charles', 46.8200, -71.2250, N'120', N'Rue du Pont', N'Quebec', N'Quebec', N'Canada');  -- ID 2

-- Person (adapted from Contact in v1.0.0 seed; IDs preserved)
INSERT INTO [dbo].[Person] ([LastName], [FirstName], [Company], [Role], [Function], [Email], [Phone], [Linkedin], [Website])
VALUES (N'Tremblay', N'Marie', N'Universite Laval - modelEAU', N'Active', N'Research Associate', N'marie.tremblay@ulaval.ca', N'418-555-0101', NULL, NULL);  -- ID 1

INSERT INTO [dbo].[Person] ([LastName], [FirstName], [Company], [Role], [Function], [Email], [Phone], [Linkedin], [Website])
VALUES (N'Gagnon', N'Pierre', N'Universite Laval - modelEAU', N'Active', N'PhD Student', N'pierre.gagnon@ulaval.ca', N'418-555-0102', NULL, NULL);  -- ID 2

-- Equipment (IDs match v1.0.0 seed)
INSERT INTO [dbo].[Equipment] ([EquipmentModel_ID], [Identifier], [SerialNumber], [Owner], [StorageLocation], [PurchaseDate])
VALUES (1, N'ISCO-001', N'SN-6712-2021-001', N'modelEAU Lab', N'PLT-2900 Storage', '2021-03-15');  -- ID 1

INSERT INTO [dbo].[Equipment] ([EquipmentModel_ID], [Identifier], [SerialNumber], [Owner], [StorageLocation], [PurchaseDate])
VALUES (2, N'YSI-001', N'SN-PRODSS-2022-045', N'modelEAU Lab', N'PLT-2900 Storage', '2022-06-01');  -- ID 2

INSERT INTO [dbo].[Equipment] ([EquipmentModel_ID], [Identifier], [SerialNumber], [Owner], [StorageLocation], [PurchaseDate])
VALUES (3, N'HACH-001', N'SN-2100Q-2020-112', N'modelEAU Lab', N'PLT-2900 Storage', '2020-09-20');  -- ID 3

-- Parameters (IDs 1-5 match v1.0.0 seed; 6-7 are new status parameters)
INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description]) VALUES (1, N'TSS',         N'Total suspended solids');        -- ID 1
INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description]) VALUES (1, N'COD',         N'Chemical oxygen demand');        -- ID 2
INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description]) VALUES (3, N'pH',          N'Hydrogen ion concentration');    -- ID 3
INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description]) VALUES (4, N'Temperature', N'Water temperature');            -- ID 4
INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description]) VALUES (5, N'Conductivity',N'Electrical conductivity');      -- ID 5
INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description])
VALUES (9, N'Sensor Status', N'Per-channel operational status code. Values reference dbo.SensorStatusCode.');   -- ID 6
INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description])
VALUES (9, N'Device Status', N'Overall equipment health status. Values reference dbo.SensorStatusCode.');       -- ID 7

-- Laboratory
INSERT INTO [dbo].[Laboratory] ([Name], [Site_ID], [Description])
VALUES (N'modelEAU Water Quality Lab', 1, N'In-house water quality analysis laboratory at Universite Laval');  -- ID 1

-- ============================================================
-- TIER 3: SamplingPoint, junctions, Campaign
-- ============================================================

-- Sampling points (IDs match v1.0.0 seed)
INSERT INTO [dbo].[SamplingPoint] ([Site_ID], [SamplingPoint], [SamplingLocation], [LatitudeGPS], [LongitudeGPS], [Description])
VALUES (1, N'WWTP-IN-01', N'Inlet channel after screening', N'46.8310', N'-71.2080', N'Primary sampling point at plant inlet');  -- ID 1

INSERT INTO [dbo].[SamplingPoint] ([Site_ID], [SamplingPoint], [SamplingLocation], [LatitudeGPS], [LongitudeGPS], [Description])
VALUES (1, N'WWTP-OUT-01', N'Final effluent discharge', N'46.8315', N'-71.2075', N'Effluent sampling point after disinfection');  -- ID 2

INSERT INTO [dbo].[SamplingPoint] ([Site_ID], [SamplingPoint], [SamplingLocation], [LatitudeGPS], [LongitudeGPS], [Description])
VALUES (2, N'CSO-12-OUT', N'Overflow pipe outlet', N'46.8200', N'-71.2250', N'CSO overflow discharge point');  -- ID 3

-- Equipment model capabilities
INSERT INTO [dbo].[EquipmentModelHasParameter] ([EquipmentModel_ID], [Parameter_ID]) VALUES (1, 1);  -- ISCO → TSS
INSERT INTO [dbo].[EquipmentModelHasParameter] ([EquipmentModel_ID], [Parameter_ID]) VALUES (1, 2);  -- ISCO → COD
INSERT INTO [dbo].[EquipmentModelHasParameter] ([EquipmentModel_ID], [Parameter_ID]) VALUES (2, 3);  -- YSI → pH
INSERT INTO [dbo].[EquipmentModelHasParameter] ([EquipmentModel_ID], [Parameter_ID]) VALUES (2, 4);  -- YSI → Temperature
INSERT INTO [dbo].[EquipmentModelHasParameter] ([EquipmentModel_ID], [Parameter_ID]) VALUES (2, 5);  -- YSI → Conductivity

INSERT INTO [dbo].[EquipmentModelHasProcedures] ([EquipmentModel_ID], [Procedure_ID]) VALUES (1, 2);  -- ISCO → 24h composite
INSERT INTO [dbo].[EquipmentModelHasProcedures] ([EquipmentModel_ID], [Procedure_ID]) VALUES (2, 3);  -- YSI → Online continuous
INSERT INTO [dbo].[EquipmentModelHasProcedures] ([EquipmentModel_ID], [Procedure_ID]) VALUES (3, 1);  -- Hach → Grab sampling

-- Campaigns (replace Project from v1.0.0 seed)
INSERT INTO [dbo].[Campaign] ([CampaignType_ID], [Site_ID], [Name], [Description], [CampaignStartDateTime])
VALUES (2, 1, N'WWTP Inlet Monitoring 2024', N'Routine monitoring of wastewater treatment plant influent quality', '2024-01-01T00:00:00');  -- ID 1

INSERT INTO [dbo].[Campaign] ([CampaignType_ID], [Site_ID], [Name], [Description], [CampaignStartDateTime], [CampaignEndDateTime])
VALUES (1, 2, N'CSO Event Study 2024', N'Combined sewer overflow characterization during rain events', '2024-01-01T00:00:00', '2024-12-31T23:59:59');  -- ID 2

-- ============================================================
-- TIER 4: Sample, CampaignEquipment, EquipmentEvent, etc.
-- ============================================================

-- Sample (morning grab from WWTP inlet)
INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart], [SampleDateTimeEnd], [SampleType_ID], [SampleMethod_ID], [Description])
VALUES (1, 1, 1, '2025-09-10T13:00:00', '2025-09-10T13:15:00', 1, 1, N'Morning grab sample at WWTP inlet');  -- ID 1

-- Campaign membership
INSERT INTO [dbo].[CampaignEquipment] ([Campaign_ID], [Equipment_ID], [Role]) VALUES (1, 1, N'Primary autosampler');
INSERT INTO [dbo].[CampaignEquipment] ([Campaign_ID], [Equipment_ID], [Role]) VALUES (1, 2, N'Online probe');
INSERT INTO [dbo].[CampaignEquipment] ([Campaign_ID], [Equipment_ID], [Role]) VALUES (2, 1, N'Event-triggered sampler');
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [SamplingPoint_ID], [Role]) VALUES (1, 1, N'Primary inlet');
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [SamplingPoint_ID], [Role]) VALUES (1, 2, N'Effluent control');
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [SamplingPoint_ID], [Role]) VALUES (2, 3, N'CSO discharge');

-- Equipment event: calibration of ISCO-001
INSERT INTO [dbo].[EquipmentEvent] ([Equipment_ID], [EquipmentEventType_ID], [EventDateTimeStart], [EventDateTimeEnd], [PerformedByPerson_ID], [Campaign_ID], [Notes])
VALUES (1, 1, '2024-01-10T09:00:00', '2024-01-10T11:00:00', 1, 1, N'Pre-deployment calibration using TSS standard solutions');  -- ID 1

-- Equipment installation: ISCO-001 at WWTP inlet
INSERT INTO [dbo].[EquipmentInstallation] ([Equipment_ID], [SamplingPoint_ID], [InstalledDate], [Campaign_ID], [Notes])
VALUES (1, 1, '2024-01-11T08:00:00', 1, N'Installed for routine inlet monitoring campaign');  -- ID 1

-- ============================================================
-- TIER 5: Channel
--
-- In v2.1.0, Channel represents a unique measurement stream
-- identified by (Equipment_ID, Parameter_ID, DataProvenance_ID, ProcessingDegree).
-- Location context is tracked via EquipmentInstallation, not Channel.
--
-- NOTE: Channels 1 and 10 from the v1.0.0 seed (MetaData rows 1 and 4)
-- both used Equipment_ID=1, Parameter_ID=1 — they merge into Channel 1.
-- DataProvenance IDs: 1=Sensor, 2=Laboratory, 3=Manual Entry
-- ValueType IDs: 1=Scalar, 2=Vector, 3=Matrix, 4=Image
-- ============================================================

-- Channel 1:  ISCO-001 TSS (sensor, raw, scalar) — covers MetaData rows 1 and 4
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (1, 1, 1, 1, 1);  -- ID 1

-- Channel 2: ISCO-001 COD (sensor, raw, scalar)
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (1, 2, 1, 1, 1);  -- ID 2

-- Channel 3: YSI-001 pH (sensor, raw, scalar)
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (2, 3, 1, 1, 1);  -- ID 3

-- Channel 4: YSI-001 Temperature (sensor, raw, scalar)
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (2, 4, 1, 1, 1);  -- ID 4

-- Channel 5: effluent TSS — no equipment, manual entry (covers MetaData row 5)
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (NULL, 1, 3, 1, 1);  -- ID 5

-- Channel 6: UV-Vis absorbance vector (no equipment-parameter pair in this demo)
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (NULL, NULL, 1, 1, 2);  -- ID 6

-- Channel 7: camera image at CSO outfall
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (NULL, NULL, 1, 1, 4);  -- ID 7

-- Channel 8: particle size distribution (vector, mg/L)
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (NULL, NULL, 1, 1, 2);  -- ID 8

-- Channel 9: particle size-velocity joint distribution (matrix)
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (NULL, NULL, 1, 1, 3);  -- ID 9

-- Channel 10: device-level status stream for ISCO-001
-- StatusChannel_ID is NULL — this channel is referenced by EquipmentStatusChannel, not by another Channel
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID])
VALUES (NULL, 7, 1, 1, 1);  -- ID 10

-- Channel 11: per-channel status stream monitoring Channel 1 (ISCO TSS)
-- StatusChannel_ID=1 means "this channel stores status values for Channel 1"
INSERT INTO [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID], [ValueType_ID], [StatusChannel_ID])
VALUES (NULL, 6, 1, 1, 1, 1);  -- ID 11

-- ChannelAxis: link vector/matrix channels to their binning axes
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID], [AxisRole], [ValueBinningAxis_ID]) VALUES (6, 0, 1);  -- UV-Vis: wavelength axis
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID], [AxisRole], [ValueBinningAxis_ID]) VALUES (8, 0, 2);  -- PSD: particle size axis
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID], [AxisRole], [ValueBinningAxis_ID]) VALUES (9, 0, 2);  -- Size-velocity: row=size
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID], [AxisRole], [ValueBinningAxis_ID]) VALUES (9, 1, 3);  -- Size-velocity: col=velocity

-- EquipmentStatusChannel: ISCO-001 device status → Channel 10
INSERT INTO [dbo].[EquipmentStatusChannel] ([Equipment_ID], [StatusChannel_ID]) VALUES (1, 10);

-- ============================================================
-- TIER 6: Value, ValueVector, ValueMatrix, ValueImage
--
-- Timestamps are UTC. Formerly INT (Unix epoch) in v1.0.0 seed;
-- converted here to DATETIME2 literals.
-- Metadata_ID → Channel_ID mapping:
--   MetaData 1 → Channel 1 (ISCO TSS)
--   MetaData 2 → Channel 2 (ISCO COD)
--   MetaData 3 → Channel 3 (YSI pH)
--   MetaData 4 → Channel 1 (ISCO TSS — same channel, different deployment)
--   MetaData 5 → Channel 5 (manual TSS)
--   MetaData 6 → Channel 4 (YSI Temperature)
-- ============================================================

-- ISCO TSS at WWTP inlet (Channel_ID=1)
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (1, 185.0, '2024-01-15T13:00:00');  -- ID 1
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (1, 210.5, '2024-01-15T19:00:00');  -- ID 2
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (1, 192.3, '2024-01-16T13:00:00');  -- ID 3

-- ISCO COD 24h composite (Channel_ID=2)
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (2, 450.0, '2024-01-15T05:00:00');  -- ID 4
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (2, 520.8, '2024-01-16T05:00:00');  -- ID 5

-- YSI pH online continuous (Channel_ID=3)
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (3, 7.2, '2024-01-15T05:00:00');    -- ID 6
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (3, 7.1, '2024-01-15T09:00:00');    -- ID 7
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (3, 6.9, '2024-01-15T13:00:00');    -- ID 8
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (3, 7.8, '2024-01-15T17:00:00');    -- ID 9

-- ISCO TSS at CSO outfall (Channel_ID=1 — same channel as WWTP inlet; location tracked via EquipmentInstallation)
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (1, 350.0, '2024-03-20T12:00:00');  -- ID 10
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (1, 580.2, '2024-03-20T14:00:00');  -- ID 11
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (1, 345.0, '2024-03-20T14:00:00');  -- ID 12

-- Effluent TSS manual entry (Channel_ID=5)
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (5, 12.5, '2024-01-15T13:00:00');  -- ID 13
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (5, 15.0, '2024-01-16T13:00:00');  -- ID 14

-- YSI Temperature online (Channel_ID=4)
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (4, 12.3, '2024-01-15T05:00:00');  -- ID 15
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (4, 12.1, '2024-01-15T09:00:00');  -- ID 16
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (4, 11.8, '2024-01-15T13:00:00');  -- ID 17

-- NULL timestamp edge case (Channel_ID=1)
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (1, 200.0, NULL);  -- ID 18

-- Device status values: ISCO-001 operational (Channel_ID=10, code 1=Operational)
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (10, 1.0, '2024-01-11T08:00:00');  -- ID 19 (deployed, operational)
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (10, 4.0, '2024-01-10T09:00:00');  -- ID 20 (in calibration = code 4=Maintenance)

-- Per-channel status for Channel 1 (Channel_ID=11, code 1=Operational)
INSERT INTO [dbo].[Value] ([Channel_ID], [Value], [Timestamp]) VALUES (11, 1.0, '2024-01-11T08:00:00');  -- ID 21

-- ValueVector: UV-Vis spectrum (Channel_ID=6)
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (6, '2025-09-10T14:00:00', 1, 2.85, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (6, '2025-09-10T14:00:00', 2, 2.42, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (6, '2025-09-10T14:00:00', 3, 1.15, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (6, '2025-09-10T14:00:00', 4, 0.45, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (6, '2025-09-10T14:00:00', 5, 0.12, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (6, '2025-09-10T14:00:00', 6, 0.05, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (6, '2025-09-10T14:00:00', 7, 0.02, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (6, '2025-09-10T18:00:00', 1, 3.10, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (6, '2025-09-10T18:00:00', 2, 2.68, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (6, '2025-09-10T18:00:00', 3, 1.35, 1);

-- ValueVector: particle size distribution (Channel_ID=8)
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (8, '2025-09-10T13:00:00', 8,  45.2, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (8, '2025-09-10T13:00:00', 9,  28.1, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (8, '2025-09-10T13:00:00', 10, 12.5, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (8, '2025-09-10T13:00:00', 11,  5.8, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (8, '2025-09-10T17:00:00', 8,  52.0, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (8, '2025-09-10T17:00:00', 9,  33.4, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (8, '2025-09-10T17:00:00', 10, 15.1, NULL);
INSERT INTO [dbo].[ValueVector] ([Channel_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode]) VALUES (8, '2025-09-10T17:00:00', 11,  7.2, NULL);

-- ValueImage: camera at CSO outfall (Channel_ID=7)
INSERT INTO [dbo].[ValueImage] ([Channel_ID], [Timestamp], [ImageWidth], [ImageHeight], [NumberOfChannels], [ImageFormat], [FileSizeBytes], [StorageBackend], [StoragePath])
VALUES (7, '2025-09-10T16:00:00', 1920, 1080, 3, N'JPEG', 245760, N'FileSystem', N'/images/cso12/2025-09-10_160000.jpg');
INSERT INTO [dbo].[ValueImage] ([Channel_ID], [Timestamp], [ImageWidth], [ImageHeight], [NumberOfChannels], [ImageFormat], [FileSizeBytes], [StorageBackend], [StoragePath])
VALUES (7, '2025-09-10T16:15:00', 1920, 1080, 3, N'JPEG', 251904, N'FileSystem', N'/images/cso12/2025-09-10_161500.jpg');

-- ValueMatrix: particle size-velocity joint distribution (Channel_ID=9)
INSERT INTO [dbo].[ValueMatrix] ([Channel_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value]) VALUES (9, '2025-09-10T13:00:00', 8,  12, 22.1);
INSERT INTO [dbo].[ValueMatrix] ([Channel_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value]) VALUES (9, '2025-09-10T13:00:00', 8,  13, 23.1);
INSERT INTO [dbo].[ValueMatrix] ([Channel_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value]) VALUES (9, '2025-09-10T13:00:00', 9,  12, 15.0);
INSERT INTO [dbo].[ValueMatrix] ([Channel_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value]) VALUES (9, '2025-09-10T13:00:00', 9,  13, 13.1);
INSERT INTO [dbo].[ValueMatrix] ([Channel_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value]) VALUES (9, '2025-09-10T13:00:00', 10, 12,  6.3);
INSERT INTO [dbo].[ValueMatrix] ([Channel_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value]) VALUES (9, '2025-09-10T13:00:00', 10, 13,  6.2);

-- ============================================================
-- TIER 7: New v2.1.0 tables
-- ============================================================

-- LabAnalysis (analysis of Sample 1 in the modelEAU lab)
INSERT INTO [dbo].[LabAnalysis] ([Sample_ID], [Laboratory_ID], [AnalystPerson_ID], [Procedure_ID], [AnalysisDateTime], [Campaign_ID], [Notes])
VALUES (1, 1, 1, 1, '2025-09-10T20:00:00', 1, N'Duplicate TSS analysis on morning grab');  -- ID 1

-- LabValue (TSS replicates from LabAnalysis 1)
INSERT INTO [dbo].[LabValue] ([LabAnalysis_ID], [Parameter_ID], [LabResult], [Replicate])
VALUES (1, 1, 178.4, 1);  -- Replicate 1: 178.4 mg/L TSS
INSERT INTO [dbo].[LabValue] ([LabAnalysis_ID], [Parameter_ID], [LabResult], [Replicate])
VALUES (1, 1, 181.2, 2);  -- Replicate 2: 181.2 mg/L TSS

-- Annotation: calibration period on ISCO TSS channel
INSERT INTO [dbo].[Annotation] ([Channel_ID], [AnnotationType_ID], [StartTime], [EndTime], [AuthorPerson_ID], [Campaign_ID], [EquipmentEvent_ID], [Title], [Comment])
VALUES (1, 3, '2024-01-10T09:00:00', '2024-01-10T11:00:00', 1, 1, 1,
        N'Pre-deployment calibration window',
        N'Data during this interval is from calibration, not field measurements.');

PRINT 'Seed data for v2.1.0 loaded successfully.';
