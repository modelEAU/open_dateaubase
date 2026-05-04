-- ============================================================
-- Vocabulary seed (seed_vocabulary.sql)
-- Replaces seed_v2.2.0.sql + seed_importer_fixtures.sql
--
-- Contains ONLY lookup/vocabulary rows that the importer cannot
-- auto-create: units, parameters, procedures, one TEST_ watershed,
-- and one TEST_ lab.
--
-- No Equipment, EquipmentModel, Site, SamplingPoint, Campaign,
-- Channel, Observation, or Value rows — those are created by the
-- importer on first run, proving the auto-creation logic works.
-- ============================================================

SET NOCOUNT ON;

-- ============================================================
-- Units (13 total)
-- ============================================================
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'mg/L');         -- ID 1
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'NTU');          -- ID 2
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'pH units');     -- ID 3
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'°C');           -- ID 4
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'mS/cm');        -- ID 5
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'nm');           -- ID 6: nanometres (UV-Vis wavelength axis)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'µm');           -- ID 7: micrometres (particle size axis)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'm/s');          -- ID 8: metres per second
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'Status Code');  -- ID 9: integer status codes
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'AU');           -- ID 10: absorbance units (UV-Vis)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'-');            -- ID 11: dimensionless (images)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'm³/h');         -- ID 12: volumetric flow rate
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'm');            -- ID 13: metres (level/depth)

-- ============================================================
-- Parameters (17 total)
-- ============================================================
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'TSS',           N'Total suspended solids');                                            -- ID 1
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'COD',           N'Chemical oxygen demand');                                            -- ID 2
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'pH',            N'Hydrogen ion concentration');                                        -- ID 3
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Temperature',   N'Water temperature');                                                 -- ID 4
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Conductivity',  N'Electrical conductivity');                                           -- ID 5
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Sensor Status', N'Per-channel operational status code');                               -- ID 6
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Device Status', N'Overall equipment health status code');                              -- ID 7
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Dissolved oxygen', N'Dissolved oxygen concentration in water');                        -- ID 8
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Turbidity',     N'Water turbidity measured by nephelometry');                          -- ID 9
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'absorbance',    N'UV-Vis spectral absorbance (per-wavelength vector, unit AU)');       -- ID 10
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Ammonium-N',    N'Ammonium nitrogen concentration (NH4-N)');                           -- ID 11
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Nitrate-N',     N'Nitrate nitrogen concentration as NO3-N equivalent');                -- ID 12
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'COD filtered',  N'Filtered COD (CODf) — soluble fraction of chemical oxygen demand'); -- ID 13
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Flow',          N'Volumetric flow rate');                                              -- ID 14
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Level',         N'Water level / depth');                                               -- ID 15
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'floc_morphology', N'Activated sludge floc morphology image from inline microscope');  -- ID 16
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Potassium',     N'Potassium concentration (K)');                                       -- ID 17

-- ============================================================
-- Unit ontology (QUDT IRIs + SI dimension vectors)
-- Format: [m, kg, s, A, K, mol, cd]
-- ============================================================
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/MilliGM-PER-L',   [UnitVector]=N'0,1,-3,0,0,0,0' WHERE [Unit]=N'mg/L';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/NTU',              [UnitVector]=N'0,0,0,0,0,0,0'  WHERE [Unit]=N'NTU';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/PH',               [UnitVector]=N'0,0,0,0,0,0,0'  WHERE [Unit]=N'pH units';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/DEG_C',            [UnitVector]=N'0,0,0,0,1,0,0'  WHERE [Unit]=N'°C';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/MilliS-PER-CentiM',[UnitVector]=N'-3,-1,3,2,0,0,0' WHERE [Unit]=N'mS/cm';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/NanoM',            [UnitVector]=N'1,0,0,0,0,0,0'  WHERE [Unit]=N'nm';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/MicroM',           [UnitVector]=N'1,0,0,0,0,0,0'  WHERE [Unit]=N'µm';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/M-PER-SEC',        [UnitVector]=N'1,0,-1,0,0,0,0' WHERE [Unit]=N'm/s';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/ABSORBANCE_UNIT',  [UnitVector]=N'0,0,0,0,0,0,0'  WHERE [Unit]=N'AU';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/UNITLESS',         [UnitVector]=N'0,0,0,0,0,0,0'  WHERE [Unit]=N'-';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/M3-PER-HR',        [UnitVector]=N'3,0,-1,0,0,0,0' WHERE [Unit]=N'm³/h';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/M',                [UnitVector]=N'1,0,0,0,0,0,0'  WHERE [Unit]=N'm';

-- ============================================================
-- Parameter ontology (ENVO IRIs)
-- Note: status/image/spectral parameters have no ENVO mapping.
-- ============================================================
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01001502' WHERE [Parameter]=N'TSS';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01000632' WHERE [Parameter]=N'COD';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_09200019' WHERE [Parameter]=N'pH';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01001501' WHERE [Parameter]=N'Temperature';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_09200010' WHERE [Parameter]=N'Conductivity';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01001111' WHERE [Parameter]=N'Dissolved oxygen';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01001573' WHERE [Parameter]=N'Turbidity';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/CHEBI_49786'   WHERE [Parameter]=N'Ammonium-N';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/CHEBI_17632'   WHERE [Parameter]=N'Nitrate-N';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01001020' WHERE [Parameter]=N'Flow';

-- ============================================================
-- Fixed vocabulary tables (seed_data from schema_dictionary YAMLs)
-- These are required by the importer and API — do NOT remove.
-- ============================================================

-- ValueKind (scalar=1, vector=2, matrix=3, image=4 — hard-coded in API)
SET IDENTITY_INSERT [dbo].[ValueKind] ON;
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (1, N'Scalar', N'A single numeric measurement value (e.g. temperature, concentration)');
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (2, N'Vector', N'An ordered sequence of numeric values (e.g. particle size distribution)');
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (3, N'Matrix', N'A two-dimensional array of values (e.g. excitation-emission matrix)');
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (4, N'Image',  N'A raster image stored as a binary file');
SET IDENTITY_INSERT [dbo].[ValueKind] OFF;

-- ChannelKind (looked up by name: "value" is the default for every ingest call)
INSERT INTO [dbo].[ChannelKind] ([ChannelKind_ID], [Name], [Description]) VALUES (1, N'Value',       N'Primary measurement or output value');
INSERT INTO [dbo].[ChannelKind] ([ChannelKind_ID], [Name], [Description]) VALUES (2, N'Status',      N'Device or measurement status flag');
INSERT INTO [dbo].[ChannelKind] ([ChannelKind_ID], [Name], [Description]) VALUES (3, N'Alarm',       N'Alarm or alert indicator');
INSERT INTO [dbo].[ChannelKind] ([ChannelKind_ID], [Name], [Description]) VALUES (4, N'Uncertainty', N'Measurement uncertainty estimate');

-- DataProvenanceKind (importer configs reference ID=1 "Sensor")
INSERT INTO [dbo].[DataProvenanceKind] ([Name], [Description]) VALUES (N'Sensor',          N'Value acquired directly from an instrument or sensor in the field');
INSERT INTO [dbo].[DataProvenanceKind] ([Name], [Description]) VALUES (N'Laboratory',      N'Value determined by laboratory chemical or physical analysis');
INSERT INTO [dbo].[DataProvenanceKind] ([Name], [Description]) VALUES (N'Manual Entry',    N'Value entered manually by an operator or scientist');
INSERT INTO [dbo].[DataProvenanceKind] ([Name], [Description]) VALUES (N'Model Output',    N'Value generated by a simulation, model, or prediction algorithm');
INSERT INTO [dbo].[DataProvenanceKind] ([Name], [Description]) VALUES (N'External Source', N'Value imported from an external dataset or third-party system');
INSERT INTO [dbo].[DataProvenanceKind] ([Name], [Description]) VALUES (N'Forecast',        N'Future-dated value produced by a forecasting model');

-- ProcessingKind (importer configs reference ID=1 "Raw")
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (1, N'Raw',        N'Original, unmodified data as received from the source');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (2, N'Cleaned',    N'Outliers removed and obvious errors corrected');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (3, N'Calibrated', N'Calibration corrections applied');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (4, N'Validated',  N'Manually reviewed and approved for use');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (5, N'Filtered',   N'Signal filtering or smoothing applied');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (6, N'Predicted',  N'Values generated by a model or prediction algorithm');

-- SignalInterfaceKind (looked up by name: "SCADA" and "DirectConnect" used in ingest)
INSERT INTO [dbo].[SignalInterfaceKind] ([Name], [Description]) VALUES (N'PLC',           N'Programmable Logic Controller exposing tags (e.g. Logix5000)');
INSERT INTO [dbo].[SignalInterfaceKind] ([Name], [Description]) VALUES (N'SCADA',         N'SCADA / HMI system publishing tag strings (e.g. Wonderware, Ignition)');
INSERT INTO [dbo].[SignalInterfaceKind] ([Name], [Description]) VALUES (N'Basestation',   N'Vendor basestation or sensor hub relaying one or more probes');
INSERT INTO [dbo].[SignalInterfaceKind] ([Name], [Description]) VALUES (N'IQSensorBus',   N'Hach/WTW IQ Sensor Net or similar multi-probe sensor bus');
INSERT INTO [dbo].[SignalInterfaceKind] ([Name], [Description]) VALUES (N'DirectConnect', N'Single-sensor direct serial/analog link — no upstream controller');
INSERT INTO [dbo].[SignalInterfaceKind] ([Name], [Description]) VALUES (N'Multiplexer',   N'Physical multiplexer (e.g. TresCON) where one port relays many streams');
INSERT INTO [dbo].[SignalInterfaceKind] ([Name], [Description]) VALUES (N'GatewayOther',  N'Other gateway/bridge device not covered by the categories above');

-- SignalInterfacePortKind
INSERT INTO [dbo].[SignalInterfacePortKind] ([Name], [Description]) VALUES (N'AnalogIn',   N'Analog input (4-20 mA, 0-10 V, etc.)');
INSERT INTO [dbo].[SignalInterfacePortKind] ([Name], [Description]) VALUES (N'AnalogOut',  N'Analog output to a field device');
INSERT INTO [dbo].[SignalInterfacePortKind] ([Name], [Description]) VALUES (N'DigitalIn',  N'Discrete digital input');
INSERT INTO [dbo].[SignalInterfacePortKind] ([Name], [Description]) VALUES (N'DigitalOut', N'Discrete digital output');
INSERT INTO [dbo].[SignalInterfacePortKind] ([Name], [Description]) VALUES (N'Serial',     N'Serial fieldbus link (RS-232/485, Modbus, Profibus)');
INSERT INTO [dbo].[SignalInterfacePortKind] ([Name], [Description]) VALUES (N'Network',    N'Ethernet/IP or other network-based port');
INSERT INTO [dbo].[SignalInterfacePortKind] ([Name], [Description]) VALUES (N'Virtual',    N'Logical port with no dedicated physical terminal (e.g. multiplexed sub-channel)');
INSERT INTO [dbo].[SignalInterfacePortKind] ([Name], [Description]) VALUES (N'Unknown',    N'Physical kind not yet traced');

-- QualityCode
INSERT INTO [dbo].[QualityCode] ([Name], [Description], [IsUsable]) VALUES (N'Accepted',   N'Measurement meets quality criteria and is fit for use',              1);
INSERT INTO [dbo].[QualityCode] ([Name], [Description], [IsUsable]) VALUES (N'Suspect',    N'Measurement may be unreliable; flagged for manual review',           1);
INSERT INTO [dbo].[QualityCode] ([Name], [Description], [IsUsable]) VALUES (N'Rejected',   N'Measurement is invalid and must not be used',                       0);
INSERT INTO [dbo].[QualityCode] ([Name], [Description], [IsUsable]) VALUES (N'BelowLoD',   N'Result is below the method''s limit of detection',                  0);
INSERT INTO [dbo].[QualityCode] ([Name], [Description], [IsUsable]) VALUES (N'AboveLoQ',   N'Result exceeds the limit of quantification (instrument saturated)',  0);
INSERT INTO [dbo].[QualityCode] ([Name], [Description], [IsUsable]) VALUES (N'Outlier',    N'Statistical outlier; not automatically invalid but requires review', 1);

-- AnnotationKind
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (1,  N'Fault',              N'Sensor or process fault',                      N'#FF4444');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (2,  N'Maintenance',        N'Sensor under maintenance',                     N'#FFA500');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (3,  N'Calibration Period', N'Data during calibration — may be invalid',     N'#FFD700');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (4,  N'Anomaly',            N'Unexpected behavior, needs investigation',      N'#FF69B4');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (5,  N'Experiment',         N'Data collected during a specific experiment',   N'#4488FF');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (6,  N'Process Event',      N'Known process event (storm, dosing, etc.)',     N'#44BB44');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (7,  N'Data Quality',       N'Suspect data quality (drift, fouling)',          N'#AA44FF');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (8,  N'Note',               N'General commentary',                            N'#888888');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (9,  N'Exclusion',          N'Data should be excluded from analysis',          N'#CC0000');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (10, N'Validated',          N'Data has been reviewed and accepted',            N'#00AA00');

-- BinKind
INSERT INTO [dbo].[BinKind] ([BinKind_ID], [Name], [Description]) VALUES (1, N'interval',              N'Bins defined by lower and upper bounds only');
INSERT INTO [dbo].[BinKind] ([BinKind_ID], [Name], [Description]) VALUES (2, N'interval_with_nominal', N'Bins defined by bounds plus a nominal center value');
INSERT INTO [dbo].[BinKind] ([BinKind_ID], [Name], [Description]) VALUES (3, N'nominal',               N'Bins defined by a single nominal value only');

-- CampaignKind
SET IDENTITY_INSERT [dbo].[CampaignKind] ON;
INSERT INTO [dbo].[CampaignKind] ([CampaignKind_ID], [Name], [Description]) VALUES (1, N'Experiment',    N'Planned scientific investigation under controlled or semi-controlled conditions');
INSERT INTO [dbo].[CampaignKind] ([CampaignKind_ID], [Name], [Description]) VALUES (2, N'Operations',    N'Routine monitoring or operational run of the monitored process');
INSERT INTO [dbo].[CampaignKind] ([CampaignKind_ID], [Name], [Description]) VALUES (3, N'Commissioning', N'Initial setup, calibration, and qualification of equipment or a process');
SET IDENTITY_INSERT [dbo].[CampaignKind] OFF;

-- EquipmentEventKind
SET IDENTITY_INSERT [dbo].[EquipmentEventKind] ON;
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (1, N'Calibration',     N'Adjustment of sensor output to match a known reference standard');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (2, N'Validation',      N'Verification that sensor output meets accuracy requirements without adjustment');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (3, N'Maintenance',     N'Physical cleaning, inspection, or servicing of equipment');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (4, N'Installation',    N'First-time mounting or connection of equipment at its deployment site');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (5, N'Removal',         N'Decommissioning or retrieval of equipment from its deployment site');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (6, N'Firmware Update', N'Update to the embedded software or firmware of the device');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (7, N'Failure',         N'Unplanned malfunction or breakdown requiring corrective action');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (8, N'Repair',          N'Corrective action performed following a recorded failure');
SET IDENTITY_INSERT [dbo].[EquipmentEventKind] OFF;

-- ControlLoopPortKind
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (1, N'MeasuredVariable',    N'The controlled or observed process variable');
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (2, N'ManipulatedVariable', N'The actuator or output adjusted by the controller');
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (3, N'SetPoint',            N'Target value supplied to the controller');
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (4, N'Disturbance',         N'Measured input that affects the process; not manipulated');
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (5, N'PredictedOutput',     N'Model-predicted value of the controlled variable');
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (6, N'Other',               N'Escape hatch for novel kinds; describe in ControlLoop.Description');

-- ProcessUnitKind
SET IDENTITY_INSERT [dbo].[ProcessUnitKind] ON;
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (1,  N'Area',      N'Broad spatial zone (e.g. biological treatment area)');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (2,  N'Zone',      N'Defined functional sub-zone within a process area');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (3,  N'Tank',      N'Enclosed vessel for liquid storage or treatment');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (4,  N'Reactor',   N'Vessel designed for controlled biological or chemical reactions');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (5,  N'Pipe',      N'Conduit transporting liquid between process units');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (6,  N'Pump',      N'Mechanical device for moving liquid');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (7,  N'Valve',     N'Flow control device regulating liquid passage');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (8,  N'Clarifier', N'Gravity settling vessel separating solids from liquid');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (9,  N'Basin',     N'Open or partially open liquid containment structure');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (10, N'Blower',    N'Mechanical device for supplying air or gas');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (11, N'Other',     N'Process unit kind not covered by the standard vocabulary');
SET IDENTITY_INSERT [dbo].[ProcessUnitKind] OFF;

-- SampleKind
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (1, N'Field',           N'Sample collected from a real-world site or process');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (2, N'Synthetic',        N'Laboratory-prepared sample with known composition');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (3, N'Master Standard',  N'Reference standard used to prepare derived standards');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (4, N'Derived Standard', N'Dilution or aliquot derived from a master standard');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (5, N'Blank',            N'Blank sample used to detect contamination or baseline');

-- SampleCollectionKind
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (1, N'Grab',         N'Single instantaneous sample collected at one point in time');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (2, N'Composite24h', N'Flow- or time-proportional composite over a 24-hour period');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (3, N'Composite8h',  N'Flow- or time-proportional composite over an 8-hour period');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (4, N'Passive',      N'Passive sampler deployed over an extended exposure period');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (5, N'Other',        N'Collection kind not covered by the standard vocabulary');

-- ============================================================
-- Procedures (3 standard ones)
-- ============================================================
INSERT INTO [dbo].[Procedures] ([ProcedureName], [ProcedureType], [Description], [ProcedureLocation])
VALUES (N'Grab sampling', N'Sampling', N'Manual grab sample collected at water surface', N'/procedures/grab_sampling.pdf');

INSERT INTO [dbo].[Procedures] ([ProcedureName], [ProcedureType], [Description], [ProcedureLocation])
VALUES (N'24h composite', N'Sampling', N'Time-weighted 24-hour composite sample via autosampler', N'/procedures/composite_24h.pdf');

INSERT INTO [dbo].[Procedures] ([ProcedureName], [ProcedureType], [Description], [ProcedureLocation])
VALUES (N'Online continuous', N'Measurement', N'Continuous in-situ measurement with data logging', N'/procedures/online_continuous.pdf');

-- ============================================================
-- Watershed (1 row, TEST_ prefix)
-- ============================================================
INSERT INTO [dbo].[Watershed] ([Name], [Description], [SurfaceArea], [ConcentrationTime], [ImperviousSurface])
VALUES (N'TEST_Rivière Saint-Charles', N'TEST watershed — Quebec City urban catchment', 550.0, 180, 35.5);

INSERT INTO [dbo].[HydrologicalCharacteristics] ([UrbanArea], [Forest], [Wetlands], [Cropland], [Meadow], [Grassland])
VALUES (35.5, 25.0, 5.0, 10.0, 12.5, 12.0);

INSERT INTO [dbo].[UrbanCharacteristics] ([Commercial], [GreenSpaces], [Industrial], [Institutional], [Residential], [Agricultural], [Recreational])
VALUES (15.0, 8.0, 12.0, 5.0, 45.0, 5.0, 10.0);

-- ============================================================
-- Laboratory (Site_ID is nullable — no dummy site needed)
-- ============================================================
INSERT INTO [dbo].[Laboratory] ([Name], [Site_ID], [Description])
VALUES (N'TEST_modelEAU Water Quality Lab', NULL, N'TEST lab — in-house water quality analysis at Université Laval');

PRINT 'Vocabulary seed loaded: 13 units, 17 parameters, 3 procedures, 1 watershed, 1 lab + all fixed vocabulary tables (ValueKind, ChannelKind, DataProvenanceKind, ProcessingKind, SignalInterfaceKind, SignalInterfacePortKind, QualityCode, AnnotationKind, BinKind, CampaignKind, EquipmentEventKind, ControlLoopPortKind, ProcessUnitKind, SampleKind, SampleCollectionKind).';
