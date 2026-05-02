-- Seed data for schema v4.0.0
-- Platform: mssql
-- Generated: 2026-05-02 20:23:01 UTC
-- AnnotationKind
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (1, N'Fault', N'Sensor or process fault', N'#FF4444');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (2, N'Maintenance', N'Sensor under maintenance', N'#FFA500');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (3, N'Calibration Period', N'Data during calibration — may be invalid', N'#FFD700');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (4, N'Anomaly', N'Unexpected behavior, needs investigation', N'#FF69B4');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (5, N'Experiment', N'Data collected during a specific experiment', N'#4488FF');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (6, N'Process Event', N'Known process event (storm, dosing, etc.)', N'#44BB44');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (7, N'Data Quality', N'Suspect data quality (drift, fouling)', N'#AA44FF');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (8, N'Note', N'General commentary', N'#888888');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (9, N'Exclusion', N'Data should be excluded from analysis', N'#CC0000');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (10, N'Validated', N'Data has been reviewed and accepted', N'#00AA00');
-- BinKind
INSERT INTO [dbo].[BinKind] ([BinKind_ID], [Name], [Description]) VALUES (1, N'interval', N'Bins defined by lower and upper bounds only');
INSERT INTO [dbo].[BinKind] ([BinKind_ID], [Name], [Description]) VALUES (2, N'interval_with_nominal', N'Bins defined by bounds plus a nominal center value');
INSERT INTO [dbo].[BinKind] ([BinKind_ID], [Name], [Description]) VALUES (3, N'nominal', N'Bins defined by a single nominal value only');
-- CampaignKind
SET IDENTITY_INSERT [dbo].[CampaignKind] ON;
INSERT INTO [dbo].[CampaignKind] ([CampaignKind_ID], [Name], [Description]) VALUES (1, N'Experiment', N'Planned scientific investigation under controlled or semi-controlled conditions');
INSERT INTO [dbo].[CampaignKind] ([CampaignKind_ID], [Name], [Description]) VALUES (2, N'Operations', N'Routine monitoring or operational run of the monitored process');
INSERT INTO [dbo].[CampaignKind] ([CampaignKind_ID], [Name], [Description]) VALUES (3, N'Commissioning', N'Initial setup, calibration, and qualification of equipment or a process');
SET IDENTITY_INSERT [dbo].[CampaignKind] OFF;
-- ChannelKind
INSERT INTO [dbo].[ChannelKind] ([ChannelKind_ID], [Name], [Description]) VALUES (1, N'Value', N'Primary measurement or output value');
INSERT INTO [dbo].[ChannelKind] ([ChannelKind_ID], [Name], [Description]) VALUES (2, N'Status', N'Device or measurement status flag');
INSERT INTO [dbo].[ChannelKind] ([ChannelKind_ID], [Name], [Description]) VALUES (3, N'Alarm', N'Alarm or alert indicator');
INSERT INTO [dbo].[ChannelKind] ([ChannelKind_ID], [Name], [Description]) VALUES (4, N'Uncertainty', N'Measurement uncertainty estimate');
-- ControlLoopPortKind
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (1, N'MeasuredVariable', N'The controlled or observed process variable');
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (2, N'ManipulatedVariable', N'The actuator or output adjusted by the controller');
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (3, N'SetPoint', N'Target value supplied to the controller');
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (4, N'Disturbance', N'Measured input that affects the process; not manipulated');
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (5, N'PredictedOutput', N'Model-predicted value of the controlled variable');
INSERT INTO [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID], [Name], [Description]) VALUES (6, N'Other', N'Escape hatch for novel kinds; describe in ControlLoop.Description');
-- DataProvenanceKind
SET IDENTITY_INSERT [dbo].[DataProvenanceKind] ON;
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (1, N'Sensor', N'Value acquired directly from an instrument or sensor in the field');
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (2, N'Laboratory', N'Value determined by laboratory chemical or physical analysis');
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (3, N'Manual Entry', N'Value entered manually by an operator or scientist');
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (4, N'Model Output', N'Value generated by a simulation, model, or prediction algorithm');
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (5, N'External Source', N'Value imported from an external dataset or third-party system');
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (6, N'Forecast', N'Future-dated value produced by a forecasting model');
SET IDENTITY_INSERT [dbo].[DataProvenanceKind] OFF;
-- EquipmentEventKind
SET IDENTITY_INSERT [dbo].[EquipmentEventKind] ON;
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (1, N'Calibration', N'Adjustment of sensor output to match a known reference standard');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (2, N'Validation', N'Verification that sensor output meets accuracy requirements without adjustment');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (3, N'Maintenance', N'Physical cleaning, inspection, or servicing of equipment');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (4, N'Installation', N'First-time mounting or connection of equipment at its deployment site');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (5, N'Removal', N'Decommissioning or retrieval of equipment from its deployment site');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (6, N'Firmware Update', N'Update to the embedded software or firmware of the device');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (7, N'Failure', N'Unplanned malfunction or breakdown requiring corrective action');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (8, N'Repair', N'Corrective action performed following a recorded failure');
SET IDENTITY_INSERT [dbo].[EquipmentEventKind] OFF;
-- ProcessUnitKind
SET IDENTITY_INSERT [dbo].[ProcessUnitKind] ON;
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (1, N'Area', N'Broad spatial zone (e.g. biological treatment area)');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (2, N'Zone', N'Defined functional sub-zone within a process area');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (3, N'Tank', N'Enclosed vessel for liquid storage or treatment');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (4, N'Reactor', N'Vessel designed for controlled biological or chemical reactions');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (5, N'Pipe', N'Conduit transporting liquid between process units');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (6, N'Pump', N'Mechanical device for moving liquid');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (7, N'Valve', N'Flow control device regulating liquid passage');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (8, N'Clarifier', N'Gravity settling vessel separating solids from liquid');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (9, N'Basin', N'Open or partially open liquid containment structure');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (10, N'Blower', N'Mechanical device for supplying air or gas');
INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Name], [Description]) VALUES (11, N'Other', N'Process unit kind not covered by the standard vocabulary');
SET IDENTITY_INSERT [dbo].[ProcessUnitKind] OFF;
-- ProcessingKind
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (1, N'Raw', N'Original, unmodified data as received from the source');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (2, N'Cleaned', N'Outliers removed and obvious errors corrected');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (3, N'Calibrated', N'Calibration corrections applied');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (4, N'Validated', N'Manually reviewed and approved for use');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (5, N'Filtered', N'Signal filtering or smoothing applied');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (6, N'Predicted', N'Values generated by a model or prediction algorithm');
-- QualityCode
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (1, N'Accepted', N'Measurement meets quality criteria and is fit for use', 1);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (2, N'Suspect', N'Measurement may be unreliable; flagged for manual review', 1);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (3, N'Rejected', N'Measurement is invalid and must not be used', 0);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (4, N'BelowLoD', N'Result is below the method''s limit of detection', 0);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (5, N'AboveLoQ', N'Result exceeds the limit of quantification (instrument saturated)', 0);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (6, N'Outlier', N'Statistical outlier; not automatically invalid but requires review', 1);
-- SampleCollectionKind
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (1, N'Grab', N'Single instantaneous sample collected at one point in time');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (2, N'Composite24h', N'Flow- or time-proportional composite over a 24-hour period');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (3, N'Composite8h', N'Flow- or time-proportional composite over an 8-hour period');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (4, N'Passive', N'Passive sampler deployed over an extended exposure period');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (5, N'Other', N'Collection kind not covered by the standard vocabulary');
-- SampleKind
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (1, N'Field', N'Sample collected from a real-world site or process');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (2, N'Synthetic', N'Laboratory-prepared sample with known composition');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (3, N'Master Standard', N'Reference standard used to prepare derived standards');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (4, N'Derived Standard', N'Dilution or aliquot derived from a master standard');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (5, N'Blank', N'Blank sample used to detect contamination or baseline');
-- SignalInterfaceKind
INSERT INTO [dbo].[SignalInterfaceKind] ([SignalInterfaceKind_ID], [Name], [Description]) VALUES (1, N'PLC', N'Programmable Logic Controller exposing tags (e.g. Logix5000)');
INSERT INTO [dbo].[SignalInterfaceKind] ([SignalInterfaceKind_ID], [Name], [Description]) VALUES (2, N'SCADA', N'SCADA / HMI system publishing tag strings (e.g. Wonderware, Ignition)');
INSERT INTO [dbo].[SignalInterfaceKind] ([SignalInterfaceKind_ID], [Name], [Description]) VALUES (3, N'Basestation', N'Vendor basestation or sensor hub relaying one or more probes');
INSERT INTO [dbo].[SignalInterfaceKind] ([SignalInterfaceKind_ID], [Name], [Description]) VALUES (4, N'IQSensorBus', N'Hach/WTW IQ Sensor Net or similar multi-probe sensor bus');
INSERT INTO [dbo].[SignalInterfaceKind] ([SignalInterfaceKind_ID], [Name], [Description]) VALUES (5, N'DirectConnect', N'Single-sensor direct serial/analog link — no upstream controller');
INSERT INTO [dbo].[SignalInterfaceKind] ([SignalInterfaceKind_ID], [Name], [Description]) VALUES (6, N'Multiplexer', N'Physical multiplexer (e.g. TresCON) where one port relays many streams');
INSERT INTO [dbo].[SignalInterfaceKind] ([SignalInterfaceKind_ID], [Name], [Description]) VALUES (7, N'GatewayOther', N'Other gateway/bridge device not covered by the categories above');
-- SignalInterfacePortKind
INSERT INTO [dbo].[SignalInterfacePortKind] ([SignalInterfacePortKind_ID], [Name], [Description]) VALUES (1, N'AnalogIn', N'Analog input (4-20 mA, 0-10 V, etc.)');
INSERT INTO [dbo].[SignalInterfacePortKind] ([SignalInterfacePortKind_ID], [Name], [Description]) VALUES (2, N'AnalogOut', N'Analog output to a field device');
INSERT INTO [dbo].[SignalInterfacePortKind] ([SignalInterfacePortKind_ID], [Name], [Description]) VALUES (3, N'DigitalIn', N'Discrete digital input');
INSERT INTO [dbo].[SignalInterfacePortKind] ([SignalInterfacePortKind_ID], [Name], [Description]) VALUES (4, N'DigitalOut', N'Discrete digital output');
INSERT INTO [dbo].[SignalInterfacePortKind] ([SignalInterfacePortKind_ID], [Name], [Description]) VALUES (5, N'Serial', N'Serial fieldbus link (RS-232/485, Modbus, Profibus)');
INSERT INTO [dbo].[SignalInterfacePortKind] ([SignalInterfacePortKind_ID], [Name], [Description]) VALUES (6, N'Network', N'Ethernet/IP or other network-based port');
INSERT INTO [dbo].[SignalInterfacePortKind] ([SignalInterfacePortKind_ID], [Name], [Description]) VALUES (7, N'Virtual', N'Logical port with no dedicated physical terminal (e.g. multiplexed sub-channel)');
INSERT INTO [dbo].[SignalInterfacePortKind] ([SignalInterfacePortKind_ID], [Name], [Description]) VALUES (8, N'Unknown', N'Physical kind not yet traced');
-- ValueKind
SET IDENTITY_INSERT [dbo].[ValueKind] ON;
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (1, N'Scalar', N'A single numeric measurement value (e.g. temperature, concentration)');
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (2, N'Vector', N'An ordered sequence of numeric values (e.g. particle size distribution)');
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (3, N'Matrix', N'A two-dimensional array of values (e.g. excitation-emission matrix)');
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (4, N'Image', N'A raster image stored as a binary file');
SET IDENTITY_INSERT [dbo].[ValueKind] OFF;
