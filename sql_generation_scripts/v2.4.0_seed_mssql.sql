-- Seed data for schema v2.4.0
-- Platform: mssql
-- Generated: 2026-07-29 16:45:02 UTC
-- AnnotationKind
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (4, N'Anomaly', N'Unexplained behaviour — something happened here that no known event accounts for', N'#FF69B4');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (7, N'Data Quality', N'Suspect data quality (drift, fouling); cite the Event that caused it if known', N'#AA44FF');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (8, N'Note', N'General commentary', N'#888888');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (9, N'Exclusion', N'Data should be excluded from analysis', N'#CC0000');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (10, N'Confirmed', N'Data has been reviewed and accepted as valid', N'#00AA00');
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
-- EventKind
SET IDENTITY_INSERT [dbo].[EventKind] ON;
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (1, N'Calibration', N'Adjustment of sensor output to match a known reference standard');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (2, N'Cleaning', N'Physical cleaning or flushing of a sensor or sampling point to restore signal quality');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (3, N'Repair', N'Corrective action performed following a recorded failure');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (4, N'PartReplacement', N'Replacement of a sub-component (membrane, electrode, probe tip) without swapping the full unit');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (5, N'Replacement', N'Full swap of a sensor or equipment unit');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (6, N'SoftwareUpdate', N'Update to embedded firmware, driver, or control software of a device');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (7, N'Validation', N'Formal check confirming that sensor outputs meet defined acceptance criteria');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (8, N'Verification', N'Comparison of sensor reading against a reference under controlled conditions (in-situ or bench)');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (9, N'VisualInspection', N'Non-destructive observation of equipment condition without intervention');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (10, N'Commissioning', N'Formal activation of equipment or a system node into operational service');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (11, N'Decommissioning', N'Formal retirement of equipment or a system node from operational service');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (12, N'OutOfService', N'Planned or unplanned removal from service (shutdown, isolation) without full decommissioning');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (13, N'PowerOutage', N'Loss of electrical power affecting a device, interface, or site');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (14, N'ControllerCrash', N'Unplanned software or hardware fault causing a controller or DAS to stop functioning');
INSERT INTO [dbo].[EventKind] ([EventKind_ID], [Name], [Description]) VALUES (15, N'OperationalChange', N'Any deliberate change in operational configuration, set-point, or procedure not covered by a more specific kind');
SET IDENTITY_INSERT [dbo].[EventKind] OFF;
-- OperationKind
INSERT INTO [dbo].[OperationKind] ([OperationKind_ID], [Name], [Description]) VALUES (1, N'Unprocessed', N'No operations applied — used for the raw channel trait only');
INSERT INTO [dbo].[OperationKind] ([OperationKind_ID], [Name], [Description]) VALUES (2, N'OutlierRemoval', N'Spikes and statistical outliers removed or flagged');
INSERT INTO [dbo].[OperationKind] ([OperationKind_ID], [Name], [Description]) VALUES (3, N'DriftCorrection', N'Sensor drift or baseline shift corrected');
INSERT INTO [dbo].[OperationKind] ([OperationKind_ID], [Name], [Description]) VALUES (4, N'FaultRemoval', N'Instrument faults and implausible values removed');
INSERT INTO [dbo].[OperationKind] ([OperationKind_ID], [Name], [Description]) VALUES (5, N'Smoothing', N'Noise reduced by a smoothing or averaging algorithm');
INSERT INTO [dbo].[OperationKind] ([OperationKind_ID], [Name], [Description]) VALUES (6, N'Interpolation', N'Missing values filled by interpolation or reconstruction');
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
-- QualityCode
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (1, N'Accepted', N'Measurement meets quality criteria and is fit for use', 1);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (2, N'Suspect', N'Measurement may be unreliable; flagged for manual review', 1);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (3, N'Rejected', N'Measurement is invalid and must not be used', 0);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (4, N'BelowLoD', N'Result is below the method''s limit of detection', 0);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (5, N'AboveLoQ', N'Result exceeds the limit of quantification (instrument saturated)', 0);
INSERT INTO [dbo].[QualityCode] ([QualityCode_ID], [Name], [Description], [IsUsable]) VALUES (6, N'Outlier', N'Statistical outlier; not automatically invalid but requires review', 1);
-- ReviewStatus
INSERT INTO [dbo].[ReviewStatus] ([ReviewStatus_ID], [Name], [Description]) VALUES (1, N'Pending', N'Measurement recorded but not yet reviewed/approved');
INSERT INTO [dbo].[ReviewStatus] ([ReviewStatus_ID], [Name], [Description]) VALUES (2, N'Approved', N'Measurement reviewed and approved by a designated reviewer');
INSERT INTO [dbo].[ReviewStatus] ([ReviewStatus_ID], [Name], [Description]) VALUES (3, N'Rejected', N'Measurement reviewed and rejected');
-- SampleCollectionKind
SET IDENTITY_INSERT [dbo].[SampleCollectionKind] ON;
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (1, N'Grab', N'Single instantaneous sample collected at one point in time');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (2, N'Composite24h', N'Flow- or time-proportional composite over a 24-hour period');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (3, N'Composite8h', N'Flow- or time-proportional composite over an 8-hour period');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (4, N'Passive', N'Passive sampler deployed over an extended exposure period');
INSERT INTO [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID], [Name], [Description]) VALUES (5, N'Other', N'Collection kind not covered by the standard vocabulary');
SET IDENTITY_INSERT [dbo].[SampleCollectionKind] OFF;
-- SampleKind
SET IDENTITY_INSERT [dbo].[SampleKind] ON;
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (1, N'Field', N'Sample collected from a real-world site or process');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (2, N'Synthetic', N'Laboratory-prepared sample with known composition');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (3, N'Master Standard', N'Reference standard used to prepare derived standards');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (4, N'Derived Standard', N'Dilution or aliquot derived from a master standard');
INSERT INTO [dbo].[SampleKind] ([SampleKind_ID], [Name], [Description]) VALUES (5, N'Blank', N'Blank sample used to detect contamination or baseline');
SET IDENTITY_INSERT [dbo].[SampleKind] OFF;
-- SampleMaterialKind
SET IDENTITY_INSERT [dbo].[SampleMaterialKind] ON;
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (1, N'grit', N'Sand, gravel, and heavy inert solids removed at the headworks');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (2, N'domestic wastewater', N'Sanitary sewage of primarily domestic origin');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (3, N'combined wastewater', N'Mixed sanitary and stormwater flow from a combined sewer');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (4, N'stormwater', N'Runoff collected from rainfall or snowmelt');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (5, N'preliminary effluent', N'Flow after preliminary treatment (screening, grit removal)');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (6, N'primary effluent', N'Clarified flow leaving primary settling');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (7, N'secondary effluent', N'Clarified flow leaving secondary (biological) treatment');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (8, N'tertiary effluent', N'Flow leaving tertiary/advanced treatment or final polishing');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (9, N'mixed liquor', N'Aerated mixture of wastewater and activated sludge in the bioreactor');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (10, N'settled activated sludge', N'Settled biomass returned or wasted from clarifiers (RAS/WAS)');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (11, N'floating activated sludge', N'Poorly-settling (bulking) flocs floating at the surface of basins or clarifiers');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (12, N'sludge blanket', N'Settled sludge layer at the bottom of a clarifier or thickener');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (13, N'scum/foam', N'Floating scum or biological foam skimmed from tank surfaces');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (14, N'digester sludge', N'Sludge inside an anaerobic or aerobic digester');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (15, N'digestate', N'Combined liquid/solid output of a digestion process');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (16, N'digested sludge', N'Stabilised sludge withdrawn after digestion');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (17, N'dewatered sludge', N'Sludge cake after mechanical dewatering');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (18, N'dried sludge', N'Thermally or air-dried sludge solids');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (19, N'concentrate', N'Reject/retentate stream from a membrane process');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (20, N'permeate', N'Filtered stream passing through a membrane');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (21, N'tap water', N'Potable water from the distribution network');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (22, N'demineralized water', N'Water with dissolved minerals removed');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (23, N'deionized water', N'Water with ions removed by ion exchange');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (24, N'nanofiltered water', N'Water treated by nanofiltration');
INSERT INTO [dbo].[SampleMaterialKind] ([SampleMaterialKind_ID], [Name], [Description]) VALUES (25, N'ultrafiltered water', N'Water treated by ultrafiltration');
SET IDENTITY_INSERT [dbo].[SampleMaterialKind] OFF;
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
-- StreamKind
INSERT INTO [dbo].[StreamKind] ([StreamKind_ID], [Name], [Description]) VALUES (1, N'Sensor', N'A sensor measurement stream (Channel subtype of Stream)');
INSERT INTO [dbo].[StreamKind] ([StreamKind_ID], [Name], [Description]) VALUES (2, N'Lab', N'A laboratory measurement stream (AnalysisSeries subtype of Stream)');
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
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (14, N'Nm³/h', NULL, N'3,0,-1,0,0,0,0', 0.000277778, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (15, N'%', N'https://qudt.org/vocab/unit/PERCENT', N'0,0,0,0,0,0,0', 0.01, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (16, N'm/h', N'https://qudt.org/vocab/unit/M-PER-HR', N'1,0,-1,0,0,0,0', 0.000277778, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (17, N'RU', NULL, NULL, NULL, NULL);
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
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Nitrite-N concentration', 19, N'Nitrite nitrogen concentration (NO2-N)', NULL, 1, N'http://qudt.org/vocab/quantitykind/MassConcentration');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'NOx-N concentration', 20, N'Total oxidized nitrogen (NO3-N + NO2-N)', NULL, 1, N'http://qudt.org/vocab/quantitykind/MassConcentration');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Air flow', 21, N'Volumetric air/gas flow rate', NULL, 1, N'http://qudt.org/vocab/quantitykind/VolumeFlowRate');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Valve position', 22, N'Control valve analog output position (0-100%)', NULL, 1, NULL);
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'TSS mass fraction', 23, N'Fraction of total suspended-solids mass in a settling-velocity class (ViCAs distribution, vector over m/h axis)', NULL, 2, N'http://qudt.org/vocab/quantitykind/DimensionlessRatio');
INSERT INTO [dbo].[Parameter] ([Parameter], [Parameter_ID], [Description], [ENVO_IRI], [ValueKind_ID], [QUDT_QuantityKind_IRI]) VALUES (N'Fluorescence', 24, N'Fluorescence excitation-emission matrix (EEM) intensity, matrix over excitation-nm x emission-nm axes', NULL, 3, NULL);
SET IDENTITY_INSERT [dbo].[Parameter] OFF;
-- Procedures
SET IDENTITY_INSERT [dbo].[Procedures] ON;
INSERT INTO [dbo].[Procedures] ([Procedure_ID], [ProcedureName], [Description], [ProcedureLocation]) VALUES (1, N'Grab sampling', N'Manual grab sample collected at water surface', N'/procedures/grab_sampling.pdf');
INSERT INTO [dbo].[Procedures] ([Procedure_ID], [ProcedureName], [Description], [ProcedureLocation]) VALUES (2, N'24h composite', N'Time-weighted 24-hour composite sample via autosampler', N'/procedures/composite_24h.pdf');
INSERT INTO [dbo].[Procedures] ([Procedure_ID], [ProcedureName], [Description], [ProcedureLocation]) VALUES (3, N'Online continuous', N'Continuous in-situ measurement with data logging', N'/procedures/online_continuous.pdf');
SET IDENTITY_INSERT [dbo].[Procedures] OFF;

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
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (19, 1);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (20, 1);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (21, 12);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (21, 14);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (22, 15);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (23, 11);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (23, 15);
INSERT INTO [dbo].[ParameterHasUnit] ([Parameter_ID], [Unit_ID]) VALUES (24, 17);
