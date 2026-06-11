-- Seed data for schema v2.0.0
-- Platform: mssql
-- Generated: 2026-06-11 15:36:46 UTC
-- AnnotationKind
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (1, N'Fault', N'Sensor or process fault', N'#FF4444');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (2, N'Maintenance', N'Sensor under maintenance', N'#FFA500');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (3, N'Calibration Period', N'Data during calibration — may be invalid', N'#FFD700');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (4, N'Anomaly', N'Unexpected behavior, needs investigation', N'#FF69B4');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (5, N'Experiment', N'Data collected for a specific experiment', N'#4488FF');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (6, N'Process Event', N'Known process event (storm, dosing, etc.)', N'#44BB44');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (7, N'Data Quality', N'Suspect data quality (drift, fouling)', N'#AA44FF');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (8, N'Note', N'General commentary', N'#888888');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (9, N'Exclusion', N'Data should be excluded from analysis', N'#CC0000');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (10, N'Confirmed', N'Data has been reviewed and accepted as valid', N'#00AA00');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (11, N'Equipment Relocation', N'Equipment was physically moved to a new location', N'#8888FF');
-- BinKind
INSERT INTO [dbo].[BinKind] ([BinKind_ID], [Name], [Description]) VALUES (1, N'interval', N'Bins defined by lower and upper bounds only');
INSERT INTO [dbo].[BinKind] ([BinKind_ID], [Name], [Description]) VALUES (2, N'interval_with_nominal', N'Bins defined by bounds plus a nominal center value (e.g., comes from a table with columns showing the mean settling velocity, but the bin in fact collects data between a min and max value (not a point value)).');
INSERT INTO [dbo].[BinKind] ([BinKind_ID], [Name], [Description]) VALUES (3, N'nominal', N'Bins defined by a single nominal (exact) value only (e.g., absorbance at exactly 200 nm).');
-- CampaignKind
SET IDENTITY_INSERT [dbo].[CampaignKind] ON;
INSERT INTO [dbo].[CampaignKind] ([CampaignKind_ID], [Name], [Description]) VALUES (1, N'Experiment', N'Planned scientific investigation under controlled or semi-controlled conditions');
INSERT INTO [dbo].[CampaignKind] ([CampaignKind_ID], [Name], [Description]) VALUES (2, N'Regular operation', N'Routine monitoring or operational run of the monitored process');
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
-- ControllerKind
SET IDENTITY_INSERT [dbo].[ControllerKind] ON;
INSERT INTO [dbo].[ControllerKind] ([ControllerKind_ID], [Name], [Description]) VALUES (1, N'PID', N'Proportional-Integral-Derivative controller');
INSERT INTO [dbo].[ControllerKind] ([ControllerKind_ID], [Name], [Description]) VALUES (2, N'Feedforward', N'Open-loop controller that acts on predicted disturbances');
INSERT INTO [dbo].[ControllerKind] ([ControllerKind_ID], [Name], [Description]) VALUES (3, N'MPC', N'Model Predictive Controller using an internal process model');
INSERT INTO [dbo].[ControllerKind] ([ControllerKind_ID], [Name], [Description]) VALUES (4, N'On-Off', N'Bang-bang (on/off) controller with fixed setpoint');
INSERT INTO [dbo].[ControllerKind] ([ControllerKind_ID], [Name], [Description]) VALUES (5, N'Manual', N'Operator-driven manual control with no automated loop');
INSERT INTO [dbo].[ControllerKind] ([ControllerKind_ID], [Name], [Description]) VALUES (6, N'Other', N'Controller type not covered by the other categories');
SET IDENTITY_INSERT [dbo].[ControllerKind] OFF;
-- DataAcquisitionSystemKind
SET IDENTITY_INSERT [dbo].[DataAcquisitionSystemKind] ON;
INSERT INTO [dbo].[DataAcquisitionSystemKind] ([DataAcquisitionSystemKind_ID], [Name], [Description]) VALUES (1, N'SCADA', N'Supervisory Control and Data Acquisition system.');
INSERT INTO [dbo].[DataAcquisitionSystemKind] ([DataAcquisitionSystemKind_ID], [Name], [Description]) VALUES (2, N'PLC', N'Programmable Logic Controller.');
INSERT INTO [dbo].[DataAcquisitionSystemKind] ([DataAcquisitionSystemKind_ID], [Name], [Description]) VALUES (3, N'Field monitoring station', N'Deployable measurement station capable of hosting multiple devices and recording their data streams.');
INSERT INTO [dbo].[DataAcquisitionSystemKind] ([DataAcquisitionSystemKind_ID], [Name], [Description]) VALUES (4, N'IoT Gateway', N'Internet-of-Things gateway aggregating sensor streams.');
INSERT INTO [dbo].[DataAcquisitionSystemKind] ([DataAcquisitionSystemKind_ID], [Name], [Description]) VALUES (5, N'Manual entry', N'Data entered manually by an operator (spreadsheet, form).');
INSERT INTO [dbo].[DataAcquisitionSystemKind] ([DataAcquisitionSystemKind_ID], [Name], [Description]) VALUES (6, N'Other', N'System type not covered by the other categories.');
SET IDENTITY_INSERT [dbo].[DataAcquisitionSystemKind] OFF;
-- DataProvenanceKind
SET IDENTITY_INSERT [dbo].[DataProvenanceKind] ON;
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (1, N'Sensor', N'Value acquired directly from an instrument or sensor in the field');
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (2, N'Laboratory', N'Value determined by laboratory chemical or physical analysis');
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (3, N'Controller Output', N'Value generated by a control algorithm.');
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (4, N'Model Output', N'Value generated by a simulation, model, or prediction algorithm not involved in control.');
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (5, N'External Source', N'Value imported from an external dataset or third-party system');
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (6, N'Forecast', N'Future-dated value produced by a forecasting model');
INSERT INTO [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID], [Name], [Description]) VALUES (7, N'Derived', N'Value produced by applying a data-processing algorithm to one or more existing channels.');
SET IDENTITY_INSERT [dbo].[DataProvenanceKind] OFF;
-- EquipmentEventKind
SET IDENTITY_INSERT [dbo].[EquipmentEventKind] ON;
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (1, N'Calibration', N'Adjustment of sensor output to match a known reference standard');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (2, N'Commissioning', N'Formal activation of equipment into operational service');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (3, N'Maintenance', N'Physical cleaning, inspection, or servicing of equipment');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (4, N'Installation', N'First-time mounting or connection of equipment at its deployment site');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (5, N'Removal', N'Decommissioning or retrieval of equipment from its deployment site');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (6, N'Firmware Update', N'Update to the embedded software or firmware of the device');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (7, N'Failure', N'Unplanned malfunction or breakdown requiring corrective action');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (8, N'Repair', N'Corrective action performed following a recorded failure');
INSERT INTO [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID], [Name], [Description]) VALUES (9, N'Decommissioning', N'Formal retirement of equipment from operational service');
SET IDENTITY_INSERT [dbo].[EquipmentEventKind] OFF;
-- ProcedureKind
SET IDENTITY_INSERT [dbo].[ProcedureKind] ON;
INSERT INTO [dbo].[ProcedureKind] ([ProcedureKind_ID], [Name], [Description]) VALUES (1, N'Maintenance and Cleaning Protocol', N'Procedures for routine maintenance, cleaning, and upkeep of equipment');
INSERT INTO [dbo].[ProcedureKind] ([ProcedureKind_ID], [Name], [Description]) VALUES (2, N'Calibration Protocol', N'Step-by-step instructions for calibrating instruments or sensors');
INSERT INTO [dbo].[ProcedureKind] ([ProcedureKind_ID], [Name], [Description]) VALUES (3, N'Validation Protocol', N'Procedures for validating measurements, methods, or models');
INSERT INTO [dbo].[ProcedureKind] ([ProcedureKind_ID], [Name], [Description]) VALUES (4, N'Laboratory Method Protocol', N'Standardised laboratory analytical methods (e.g. ISO, ASTM, APHA)');
INSERT INTO [dbo].[ProcedureKind] ([ProcedureKind_ID], [Name], [Description]) VALUES (5, N'Software Manual', N'User or operational manuals for software tools used in data acquisition or processing');
SET IDENTITY_INSERT [dbo].[ProcedureKind] OFF;
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
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (2, N'Free of outliers', N'Spikes and statistical outliers have been removed or flagged');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (3, N'Free of drift', N'Sensor drift or baseline shift has been corrected');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (4, N'Free of faults', N'Instrument faults and implausible values have been removed');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (5, N'Smoothed', N'Noise reduced by a smoothing or averaging algorithm');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (6, N'Interpolated', N'Missing values filled by interpolation');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (7, N'Predicted', N'Values generated by a predictive model or algorithm');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (8, N'Derived', N'Computed from one or more other channels (e.g. dimensionality reduction, transformation)');
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
-- SiteKind
SET IDENTITY_INSERT [dbo].[SiteKind] ON;
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (1, N'Municipal Wastewater Treatment Plant', N'Municipal or industrial facility treating wastewater before discharge');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (2, N'Combined Sewer Overflow', N'Point where combined sewer system discharges during high-flow events');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (3, N'River / Stream', N'Natural flowing surface water body');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (4, N'Lake / Reservoir', N'Natural or artificial standing body of water');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (5, N'Groundwater / Well', N'Subsurface water source accessed via a well or borehole');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (6, N'Drinking Water Distribution Network Access Point', N'Monitoring point within a potable water distribution network');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (7, N'Canal', N'Artificial waterway for water transport or drainage');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (8, N'Wastewater Pumping Station', N'Facility that pumps wastewater through the collection network');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (9, N'Combined Drainage Network Access Point', N'Monitoring point within a combined stormwater and wastewater network');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (10, N'Rainwater Drainage Network Access Point', N'Monitoring point within a stormwater-only drainage network');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (11, N'Wastewater Drainage Network Access Point', N'Monitoring point within a sanitary sewer network');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (12, N'Experimental Wastewater Treatment Plant', N'Small-scale experimental treatment or process facility');
INSERT INTO [dbo].[SiteKind] ([SiteKind_ID], [Name], [Description]) VALUES (13, N'Other', N'Site kind not covered by the standard vocabulary');
SET IDENTITY_INSERT [dbo].[SiteKind] OFF;
-- Unit
SET IDENTITY_INSERT [dbo].[Unit] ON;
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (1, N'mg/L', N'https://qudt.org/vocab/unit/MilliGM-PER-L', N'0,1,-3,0,0,0,0', 0.001, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (2, N'NTU', N'https://qudt.org/vocab/unit/NTU', N'0,0,0,0,0,0,0', NULL, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (3, N'pH units', N'https://qudt.org/vocab/unit/PH', N'0,0,0,0,0,0,0', NULL, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (4, N'°C', N'https://qudt.org/vocab/unit/DEG_C', N'0,0,0,0,1,0,0', 1.0, 273.15);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (5, N'mS/cm', N'https://qudt.org/vocab/unit/MilliS-PER-CentiM', N'-3,-1,3,2,0,0,0', 0.1, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (6, N'nm', N'https://qudt.org/vocab/unit/NanoM', N'1,0,0,0,0,0,0', 1e-09, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (7, N'µm', N'https://qudt.org/vocab/unit/MicroM', N'1,0,0,0,0,0,0', 1e-06, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (8, N'm/s', N'https://qudt.org/vocab/unit/M-PER-SEC', N'1,0,-1,0,0,0,0', 1.0, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (9, N'Status Code', NULL, NULL, NULL, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (10, N'AU', N'https://qudt.org/vocab/unit/ABSORBANCE_UNIT', N'0,0,0,0,0,0,0', NULL, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (11, N'-', N'https://qudt.org/vocab/unit/UNITLESS', N'0,0,0,0,0,0,0', 1.0, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (12, N'm³/h', N'https://qudt.org/vocab/unit/M3-PER-HR', N'3,0,-1,0,0,0,0', 0.000277778, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (13, N'm', N'https://qudt.org/vocab/unit/M', N'1,0,0,0,0,0,0', 1.0, NULL);
SET IDENTITY_INSERT [dbo].[Unit] OFF;
-- ValueKind
SET IDENTITY_INSERT [dbo].[ValueKind] ON;
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (1, N'Scalar', N'A single numeric measurement value (e.g. temperature, concentration)');
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (2, N'Vector', N'An ordered sequence of numeric values (e.g. particle size distribution)');
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (3, N'Matrix', N'A two-dimensional array of values (e.g. excitation-emission matrix)');
INSERT INTO [dbo].[ValueKind] ([ValueKind_ID], [Name], [Description]) VALUES (4, N'Image', N'A raster image stored as a binary file');
SET IDENTITY_INSERT [dbo].[ValueKind] OFF;
-- Parameter
SET IDENTITY_INSERT [dbo].[Parameter] ON;
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'TSS concentration', 1, N'Total suspended solids', N'http://purl.obolibrary.org/obo/ENVO_01001502', 1, N'http://qudt.org/vocab/quantitykind/MassConcentration');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'COD concentration', 2, N'Chemical oxygen demand', N'http://purl.obolibrary.org/obo/ENVO_01000632', 1, N'http://qudt.org/vocab/quantitykind/MassConcentration');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'pH', 3, N'Hydrogen ion concentration', N'http://purl.obolibrary.org/obo/ENVO_09200019', 1, N'http://qudt.org/vocab/quantitykind/PH');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Temperature', 4, N'Water temperature', N'http://purl.obolibrary.org/obo/ENVO_01001501', 1, N'http://qudt.org/vocab/quantitykind/Temperature');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Conductivity', 5, N'Electrical conductivity', N'http://purl.obolibrary.org/obo/ENVO_09200010', 1, N'http://qudt.org/vocab/quantitykind/ElectricConductivity');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Sensor Status', 6, N'Per-channel operational status code', NULL, 1, NULL);
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Device Status', 7, N'Overall equipment health status code', NULL, 1, NULL);
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Dissolved oxygen concentration', 8, N'Dissolved oxygen concentration in water', N'http://purl.obolibrary.org/obo/ENVO_01001111', 1, N'http://qudt.org/vocab/quantitykind/MassConcentration');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Turbidity', 9, N'Water turbidity measured by nephelometry', N'http://purl.obolibrary.org/obo/ENVO_01001573', 1, N'http://qudt.org/vocab/quantitykind/Turbidity');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Absorbance spectrum', 10, N'UV-Vis spectral absorbance (per-wavelength vector, unit AU)', NULL, 2, NULL);
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Ammonium-N concentration', 11, N'Ammonium nitrogen concentration (NH4-N)', N'http://purl.obolibrary.org/obo/CHEBI_49786', 1, N'http://qudt.org/vocab/quantitykind/MassConcentration');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Nitrate-N concentration', 12, N'Nitrate nitrogen concentration as NO3-N equivalent', N'http://purl.obolibrary.org/obo/CHEBI_17632', 1, N'http://qudt.org/vocab/quantitykind/MassConcentration');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'COD filtered concentration', 13, N'Filtered COD (CODf) — soluble fraction of chemical oxygen demand', NULL, 1, N'http://qudt.org/vocab/quantitykind/MassConcentration');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Flow', 14, N'Volumetric flow rate', N'http://purl.obolibrary.org/obo/ENVO_01001020', 1, N'http://qudt.org/vocab/quantitykind/VolumeFlowRate');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Level', 15, N'Water level / depth', NULL, 1, N'http://qudt.org/vocab/quantitykind/Length');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'floc_morphology', 16, N'Activated sludge floc morphology image from inline microscope', NULL, 4, NULL);
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Potassium concentration', 17, N'Potassium concentration (K)', NULL, 1, N'http://qudt.org/vocab/quantitykind/MassConcentration');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Light Absorbance', 18, N'Scalar light absorbance measurement', NULL, 1, N'http://qudt.org/vocab/quantitykind/Absorbance');
SET IDENTITY_INSERT [dbo].[Parameter] OFF;

-- ParameterHasUnit (generated by ontology_query.py)
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (1, 1);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (2, 1);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (3, 3);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (4, 4);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (5, 5);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (8, 1);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (9, 2);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (10, 10);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (11, 1);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (12, 1);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (13, 1);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (14, 12);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (15, 6);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (15, 7);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (15, 13);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (17, 1);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (18, 10);
