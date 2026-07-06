-- Migration: v2.0.0 -> v2.1.0
-- Platform: mssql
-- Generated: 2026-07-06 17:29:46 UTC
-- Rollback: v2.0.0_to_v2.1.0_mssql_rollback.sql


CREATE TABLE [dbo].[EventKind] (
    [EventKind_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(100) NOT NULL,
    [Description] NVARCHAR(300),
    CONSTRAINT [PK_EventKind] PRIMARY KEY ([EventKind_ID])
);

CREATE TABLE [dbo].[OperationKind] (
    [OperationKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_OperationKind] PRIMARY KEY ([OperationKind_ID])
);

CREATE TABLE [dbo].[ReviewStatus] (
    [ReviewStatus_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_ReviewStatus] PRIMARY KEY ([ReviewStatus_ID])
);

CREATE TABLE [dbo].[StreamKind] (
    [StreamKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_StreamKind] PRIMARY KEY ([StreamKind_ID])
);

CREATE TABLE [dbo].[ChannelTrait] (
    [Stream_ID] INT NOT NULL,
    [OperationKind_ID] INT NOT NULL,
    CONSTRAINT [PK_ChannelTrait] PRIMARY KEY ([Stream_ID], [OperationKind_ID])
);

CREATE TABLE [dbo].[Event] (
    [Event_ID] INT IDENTITY(1,1) NOT NULL,
    [Channel_ID] INT,
    [Equipment_ID] INT,
    [SignalInterface_ID] INT,
    [DataAcquisitionSystem_ID] INT,
    [SamplingPoint_ID] INT,
    [ProcessUnit_ID] INT,
    [Site_ID] INT,
    [Campaign_ID] INT,
    [EventKind_ID] INT NOT NULL,
    [EventDateTimeStart] DATETIME2(7) NOT NULL,
    [IsInstantaneous] BIT NOT NULL DEFAULT 0,
    [EventDateTimeEnd] DATETIME2(7),
    [PerformedByPerson_ID] INT,
    [RecordedByPerson_ID] INT,
    [Notes] NVARCHAR(MAX),
    CONSTRAINT [PK_Event] PRIMARY KEY ([Event_ID]),
    CONSTRAINT [CK_Event_ExclusiveArc] CHECK ((CASE WHEN [Channel_ID] IS NOT NULL THEN 1 ELSE 0 END +
 CASE WHEN [Equipment_ID] IS NOT NULL THEN 1 ELSE 0 END +
 CASE WHEN [SignalInterface_ID] IS NOT NULL THEN 1 ELSE 0 END +
 CASE WHEN [DataAcquisitionSystem_ID] IS NOT NULL THEN 1 ELSE 0 END +
 CASE WHEN [SamplingPoint_ID] IS NOT NULL THEN 1 ELSE 0 END +
 CASE WHEN [ProcessUnit_ID] IS NOT NULL THEN 1 ELSE 0 END +
 CASE WHEN [Site_ID] IS NOT NULL THEN 1 ELSE 0 END +
 CASE WHEN [Campaign_ID] IS NOT NULL THEN 1 ELSE 0 END) = 1)
);

CREATE TABLE [dbo].[Stream] (
    [Stream_ID] INT IDENTITY(1,1) NOT NULL,
    [StreamKind_ID] INT NOT NULL,
    CONSTRAINT [PK_Stream] PRIMARY KEY ([Stream_ID])
);

ALTER TABLE [dbo].[AnalysisSeries] ADD [Stream_ID] INT NOT NULL;

ALTER TABLE [dbo].[Annotation] ADD [Stream_ID] INT NOT NULL;

ALTER TABLE [dbo].[Annotation] ADD [Event_ID] INT;

ALTER TABLE [dbo].[Channel] ADD [Stream_ID] INT NOT NULL;

ALTER TABLE [dbo].[ControlLoopPort] ADD [Stream_ID] INT NOT NULL;

ALTER TABLE [dbo].[LabAnalysis] ADD [ReviewStatus_ID] INT NOT NULL DEFAULT 1;

ALTER TABLE [dbo].[LabAnalysis] ADD [ReviewedByPerson_ID] INT;

ALTER TABLE [dbo].[LabAnalysis] ADD [ReviewDateTime] DATETIME2(7);

ALTER TABLE [dbo].[ProcessingLineage] ADD [Stream_ID] INT NOT NULL;

ALTER TABLE [dbo].[ProcessingStep] ADD [OperationKind_ID] INT;

ALTER TABLE [dbo].[EquipmentLocationHistory] ALTER COLUMN [Campaign_ID] INT;

ALTER TABLE [dbo].[EquipmentModel] ALTER COLUMN [ManualLocation] NVARCHAR(1000);

ALTER TABLE [dbo].[HydrologicalCharacteristics] ALTER COLUMN [Watershed_ID] INT;

ALTER TABLE [dbo].[LandUse] ALTER COLUMN [Watershed_ID] INT;

ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [FK_AnalysisSeries_ProcessingKind_ID];

ALTER TABLE [dbo].[AnalysisSeriesAxis] DROP CONSTRAINT [FK_AnalysisSeriesAxis_AnalysisSeries_ID];

ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [FK_Annotation_Channel_ID];

ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [FK_Annotation_AnalysisSeries_ID];

ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [FK_Annotation_EquipmentEvent_ID];

ALTER TABLE [dbo].[Campaign] DROP CONSTRAINT [FK_Campaign_Site_ID];

ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [FK_Channel_SignalInterfacePort_ID];

ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [FK_Channel_ParentChannel_ID];

ALTER TABLE [dbo].[ChannelAxis] DROP CONSTRAINT [FK_ChannelAxis_Channel_ID];

ALTER TABLE [dbo].[ChannelPortHistory] DROP CONSTRAINT [FK_ChannelPortHistory_Channel_ID];

ALTER TABLE [dbo].[ControlLoopPort] DROP CONSTRAINT [FK_ControlLoopPort_Channel_ID];

ALTER TABLE [dbo].[DatasetChannel] DROP CONSTRAINT [FK_DatasetChannel_Channel_ID];

ALTER TABLE [dbo].[LabAnalysis] DROP CONSTRAINT [FK_LabAnalysis_AnalysisSeries_ID];

ALTER TABLE [dbo].[LabPanelSeries] DROP CONSTRAINT [FK_LabPanelSeries_AnalysisSeries_ID];

ALTER TABLE [dbo].[Observation] DROP CONSTRAINT [FK_Observation_Channel_ID];

ALTER TABLE [dbo].[ProcessingLineage] DROP CONSTRAINT [FK_ProcessingLineage_Channel_ID];

ALTER TABLE [dbo].[ProcessingStep] DROP CONSTRAINT [FK_ProcessingStep_ProcessingKind_ID];

ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [UQ_AnalysisSeries_Identity];

ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [CK_Annotation_Source];

DROP INDEX [IX_Annotation_Channel_Time] ON [dbo].[Annotation];

DROP INDEX [IX_Annotation_Series_Time] ON [dbo].[Annotation];

DROP INDEX [UQ_ControlLoopPort_LoopChannel] ON [dbo].[ControlLoopPort];

DROP INDEX [IX_ProcessingLineage_Channel] ON [dbo].[ProcessingLineage];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.AnalysisSeries') AND c.name = 'AnalysisSeries_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [' + @df + ']');

GO

-- Manual: AnalysisSeries adopts Stream_ID as its PK (Class Table Inheritance
-- under the new Stream supertype, ADR 0004/0005). Pre-release/no-data: the
-- table is empty on every known deployment, so no Stream backfill or
-- Stream_ID population step is needed here — if ever applying this against a
-- populated table, insert a Stream row per existing AnalysisSeries row first
-- and set Stream_ID accordingly before dropping the old PK.
ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [PK_AnalysisSeries];

ALTER TABLE [dbo].[AnalysisSeries] DROP COLUMN [AnalysisSeries_ID];

ALTER TABLE [dbo].[AnalysisSeries] ADD CONSTRAINT [PK_AnalysisSeries] PRIMARY KEY ([Stream_ID]);

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.AnalysisSeries') AND c.name = 'ProcessingKind_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[AnalysisSeries] DROP COLUMN [ProcessingKind_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.Annotation') AND c.name = 'Channel_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[Annotation] DROP COLUMN [Channel_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.Annotation') AND c.name = 'AnalysisSeries_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[Annotation] DROP COLUMN [AnalysisSeries_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.Annotation') AND c.name = 'EquipmentEvent_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[Annotation] DROP COLUMN [EquipmentEvent_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.Campaign') AND c.name = 'Site_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[Campaign] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[Campaign] DROP COLUMN [Site_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.Channel') AND c.name = 'Channel_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [' + @df + ']');

GO

-- Manual: Channel adopts Stream_ID as its PK (Class Table Inheritance under
-- the new Stream supertype, ADR 0004/0005). Pre-release/no-data: the table
-- is empty on every known deployment, so no Stream backfill or Stream_ID
-- population step is needed here — if ever applying this against a
-- populated table, insert a Stream row per existing Channel row first and
-- set Stream_ID accordingly before dropping the old PK.
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [PK_Channel];

ALTER TABLE [dbo].[Channel] DROP COLUMN [Channel_ID];

ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [PK_Channel] PRIMARY KEY ([Stream_ID]);

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.Channel') AND c.name = 'SignalInterfacePort_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[Channel] DROP COLUMN [SignalInterfacePort_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.ControlLoopPort') AND c.name = 'Channel_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[ControlLoopPort] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[ControlLoopPort] DROP COLUMN [Channel_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.ProcessingLineage') AND c.name = 'Channel_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[ProcessingLineage] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[ProcessingLineage] DROP COLUMN [Channel_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.ProcessingStep') AND c.name = 'ProcessingKind_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[ProcessingStep] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[ProcessingStep] DROP COLUMN [ProcessingKind_ID];

DROP TABLE [dbo].[EquipmentEvent];

DROP TABLE [dbo].[ProcessingKind];

DROP TABLE [dbo].[EquipmentEventKind];

CREATE INDEX [IX_Annotation_Stream_Time] ON [dbo].[Annotation] ([Stream_ID], [StartTime], [EndTime]);

CREATE UNIQUE INDEX [UQ_ControlLoopPort_LoopStream] ON [dbo].[ControlLoopPort] ([ControlLoop_ID], [Stream_ID]);

CREATE INDEX [IX_ProcessingLineage_Stream] ON [dbo].[ProcessingLineage] ([Stream_ID]);

CREATE INDEX [IX_ChannelTrait_Stream] ON [dbo].[ChannelTrait] ([Stream_ID]);

CREATE INDEX [IX_Event_Equipment_Start] ON [dbo].[Event] ([Equipment_ID], [EventDateTimeStart]);

CREATE INDEX [IX_Event_Channel_Start] ON [dbo].[Event] ([Channel_ID], [EventDateTimeStart]);

CREATE INDEX [IX_Event_Site_Start] ON [dbo].[Event] ([Site_ID], [EventDateTimeStart]);

CREATE INDEX [IX_Event_Start] ON [dbo].[Event] ([EventDateTimeStart]);

ALTER TABLE [dbo].[AnalysisSeries] ADD CONSTRAINT [UQ_AnalysisSeries_Identity] UNIQUE ([Parameter_ID], [SamplingPoint_ID], [ValueKind_ID]);

ALTER TABLE [dbo].[AnalysisSeries] ADD CONSTRAINT [FK_AnalysisSeries_Stream_ID] FOREIGN KEY ([Stream_ID]) REFERENCES [dbo].[Stream] ([Stream_ID]);

ALTER TABLE [dbo].[AnalysisSeriesAxis] ADD CONSTRAINT [FK_AnalysisSeriesAxis_AnalysisSeries_ID] FOREIGN KEY ([AnalysisSeries_ID]) REFERENCES [dbo].[AnalysisSeries] ([Stream_ID]);

ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Stream_ID] FOREIGN KEY ([Stream_ID]) REFERENCES [dbo].[Stream] ([Stream_ID]);

ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Event_ID] FOREIGN KEY ([Event_ID]) REFERENCES [dbo].[Event] ([Event_ID]);

ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_Stream_ID] FOREIGN KEY ([Stream_ID]) REFERENCES [dbo].[Stream] ([Stream_ID]);

ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_ParentChannel_ID] FOREIGN KEY ([ParentChannel_ID]) REFERENCES [dbo].[Channel] ([Stream_ID]);

ALTER TABLE [dbo].[ChannelAxis] ADD CONSTRAINT [FK_ChannelAxis_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Stream_ID]);

ALTER TABLE [dbo].[ChannelPortHistory] ADD CONSTRAINT [FK_ChannelPortHistory_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Stream_ID]);

ALTER TABLE [dbo].[ControlLoopPort] ADD CONSTRAINT [FK_ControlLoopPort_Stream_ID] FOREIGN KEY ([Stream_ID]) REFERENCES [dbo].[Stream] ([Stream_ID]);

ALTER TABLE [dbo].[DatasetChannel] ADD CONSTRAINT [FK_DatasetChannel_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Stream_ID]);

ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_AnalysisSeries_ID] FOREIGN KEY ([AnalysisSeries_ID]) REFERENCES [dbo].[AnalysisSeries] ([Stream_ID]);

ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_ReviewStatus_ID] FOREIGN KEY ([ReviewStatus_ID]) REFERENCES [dbo].[ReviewStatus] ([ReviewStatus_ID]);

ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_ReviewedByPerson_ID] FOREIGN KEY ([ReviewedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);

ALTER TABLE [dbo].[LabPanelSeries] ADD CONSTRAINT [FK_LabPanelSeries_AnalysisSeries_ID] FOREIGN KEY ([AnalysisSeries_ID]) REFERENCES [dbo].[AnalysisSeries] ([Stream_ID]);

ALTER TABLE [dbo].[Observation] ADD CONSTRAINT [FK_Observation_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Stream_ID]);

ALTER TABLE [dbo].[ProcessingLineage] ADD CONSTRAINT [FK_ProcessingLineage_Stream_ID] FOREIGN KEY ([Stream_ID]) REFERENCES [dbo].[Stream] ([Stream_ID]);

ALTER TABLE [dbo].[ProcessingStep] ADD CONSTRAINT [FK_ProcessingStep_OperationKind_ID] FOREIGN KEY ([OperationKind_ID]) REFERENCES [dbo].[OperationKind] ([OperationKind_ID]);

ALTER TABLE [dbo].[ChannelTrait] ADD CONSTRAINT [FK_ChannelTrait_Stream_ID] FOREIGN KEY ([Stream_ID]) REFERENCES [dbo].[Stream] ([Stream_ID]);

ALTER TABLE [dbo].[ChannelTrait] ADD CONSTRAINT [FK_ChannelTrait_OperationKind_ID] FOREIGN KEY ([OperationKind_ID]) REFERENCES [dbo].[OperationKind] ([OperationKind_ID]);

ALTER TABLE [dbo].[Event] ADD CONSTRAINT [FK_Event_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Stream_ID]);

ALTER TABLE [dbo].[Event] ADD CONSTRAINT [FK_Event_Equipment_ID] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);

ALTER TABLE [dbo].[Event] ADD CONSTRAINT [FK_Event_SignalInterface_ID] FOREIGN KEY ([SignalInterface_ID]) REFERENCES [dbo].[SignalInterface] ([SignalInterface_ID]);

ALTER TABLE [dbo].[Event] ADD CONSTRAINT [FK_Event_DataAcquisitionSystem_ID] FOREIGN KEY ([DataAcquisitionSystem_ID]) REFERENCES [dbo].[DataAcquisitionSystem] ([DataAcquisitionSystem_ID]);

ALTER TABLE [dbo].[Event] ADD CONSTRAINT [FK_Event_SamplingPoint_ID] FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);

ALTER TABLE [dbo].[Event] ADD CONSTRAINT [FK_Event_ProcessUnit_ID] FOREIGN KEY ([ProcessUnit_ID]) REFERENCES [dbo].[ProcessUnit] ([ProcessUnit_ID]);

ALTER TABLE [dbo].[Event] ADD CONSTRAINT [FK_Event_Site_ID] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]);

ALTER TABLE [dbo].[Event] ADD CONSTRAINT [FK_Event_Campaign_ID] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);

ALTER TABLE [dbo].[Event] ADD CONSTRAINT [FK_Event_EventKind_ID] FOREIGN KEY ([EventKind_ID]) REFERENCES [dbo].[EventKind] ([EventKind_ID]);

ALTER TABLE [dbo].[Event] ADD CONSTRAINT [FK_Event_PerformedByPerson_ID] FOREIGN KEY ([PerformedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);

ALTER TABLE [dbo].[Event] ADD CONSTRAINT [FK_Event_RecordedByPerson_ID] FOREIGN KEY ([RecordedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);

ALTER TABLE [dbo].[Stream] ADD CONSTRAINT [FK_Stream_StreamKind_ID] FOREIGN KEY ([StreamKind_ID]) REFERENCES [dbo].[StreamKind] ([StreamKind_ID]);

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

-- ReviewStatus
INSERT INTO [dbo].[ReviewStatus] ([ReviewStatus_ID], [Name], [Description]) VALUES (1, N'Pending', N'Measurement recorded but not yet reviewed/approved');
INSERT INTO [dbo].[ReviewStatus] ([ReviewStatus_ID], [Name], [Description]) VALUES (2, N'Approved', N'Measurement reviewed and approved by a designated reviewer');
INSERT INTO [dbo].[ReviewStatus] ([ReviewStatus_ID], [Name], [Description]) VALUES (3, N'Rejected', N'Measurement reviewed and rejected');

-- StreamKind
INSERT INTO [dbo].[StreamKind] ([StreamKind_ID], [Name], [Description]) VALUES (1, N'Sensor', N'A sensor measurement stream (Channel subtype of Stream)');
INSERT INTO [dbo].[StreamKind] ([StreamKind_ID], [Name], [Description]) VALUES (2, N'Lab', N'A laboratory measurement stream (AnalysisSeries subtype of Stream)');

-- Unit
SET IDENTITY_INSERT [dbo].[Unit] ON;
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (14, N'Nm³/h', NULL, N'3,0,-1,0,0,0,0', 0.000277778, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (15, N'%', N'https://qudt.org/vocab/unit/PERCENT', N'0,0,0,0,0,0,0', 0.01, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (16, N'm/h', N'https://qudt.org/vocab/unit/M-PER-HR', N'1,0,-1,0,0,0,0', 0.000277778, NULL);
INSERT INTO [dbo].[Unit] ([Unit_ID], [Unit], [QUDT_IRI], [UnitVector], [SI_Multiplier], [SI_Offset]) VALUES (17, N'RU', NULL, NULL, NULL, NULL);
SET IDENTITY_INSERT [dbo].[Unit] OFF;

-- Parameter
SET IDENTITY_INSERT [dbo].[Parameter] ON;
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

GO

CREATE OR ALTER VIEW [dbo].[vw_ChannelResolved] AS
SELECT
    c.[Stream_ID],
    c.[SignalInterface_ID],
    c.[TagName],
    cph.[SignalInterfacePort_ID],
    c.[ParentChannel_ID],
    c.[ChannelKind_ID],
    c.[Parameter_ID],
    c.[DataProvenanceKind_ID],
    c.[ProducedByStep_ID],
    c.[ValueKind_ID],
    c.[Unit_ID]
FROM [dbo].[Channel] c
LEFT JOIN [dbo].[ChannelPortHistory] cph
    ON cph.[Channel_ID] = c.[Stream_ID]
    AND cph.[ValidTo] IS NULL;

GO

GO

CREATE OR ALTER VIEW [dbo].[vw_DeploymentCoherence] AS
SELECT
    dlh.[DataAcquisitionSystem_ID]      AS DAS_ID,
    das.[Name]                          AS DASName,
    dlh.[Site_ID]                       AS DASSite_ID,
    dsite.[Name]                        AS DASSiteName,
    e.[Equipment_ID]                    AS Equipment_ID,
    e.[Identifier]                      AS EquipmentName,
    sp.[Site_ID]                        AS EquipmentSite_ID,
    esite.[Name]                        AS EquipmentSiteName,
    sp.[SamplingPoint_ID]               AS SamplingPoint_ID,
    sp.[SamplingPoint]                  AS SamplingPointName
FROM [dbo].[DASLocationHistory] dlh
JOIN [dbo].[DataAcquisitionSystem] das ON das.[DataAcquisitionSystem_ID] = dlh.[DataAcquisitionSystem_ID]
JOIN [dbo].[SignalInterface] si        ON si.[DataAcquisitionSystem_ID] = dlh.[DataAcquisitionSystem_ID]
JOIN [dbo].[EquipmentWiringHistory] ewh ON ewh.[SignalInterface_ID] = si.[SignalInterface_ID]
                                       AND ewh.[ValidTo] IS NULL
JOIN [dbo].[Equipment] e               ON e.[Equipment_ID] = ewh.[Equipment_ID]
JOIN [dbo].[EquipmentLocationHistory] elh ON elh.[Equipment_ID] = e.[Equipment_ID]
                                       AND elh.[ValidTo] IS NULL
JOIN [dbo].[SamplingPoint] sp          ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID]
LEFT JOIN [dbo].[Site] dsite           ON dsite.[Site_ID] = dlh.[Site_ID]
LEFT JOIN [dbo].[Site] esite           ON esite.[Site_ID] = sp.[Site_ID]
WHERE dlh.[ValidTo] IS NULL
  AND sp.[Site_ID] <> dlh.[Site_ID];

GO

GO

CREATE OR ALTER VIEW [dbo].[vw_InactiveParentReferences] AS
SELECT
    N'active-wiring->interface' AS ReferenceType,
    ewh.[EquipmentWiringHistory_ID] AS WiringHistoryID,
    ewh.[Equipment_ID]              AS EquipmentID,
    si.[SignalInterface_ID]         AS ParentID,
    si.[Name]                       AS ParentLabel
FROM [dbo].[EquipmentWiringHistory] ewh
JOIN [dbo].[SignalInterface] si ON si.[SignalInterface_ID] = ewh.[SignalInterface_ID]
WHERE ewh.[ValidTo] IS NULL
  AND si.[IsActive] = 0
UNION ALL
SELECT
    N'active-wiring->port'  AS ReferenceType,
    ewh.[EquipmentWiringHistory_ID] AS WiringHistoryID,
    ewh.[Equipment_ID]              AS EquipmentID,
    sip.[SignalInterfacePort_ID]    AS ParentID,
    sip.[PortIdentifier]            AS ParentLabel
FROM [dbo].[EquipmentWiringHistory] ewh
JOIN [dbo].[SignalInterfacePort] sip ON sip.[SignalInterfacePort_ID] = ewh.[SignalInterfacePort_ID]
WHERE ewh.[ValidTo] IS NULL
  AND sip.[IsActive] = 0;

GO

GO

CREATE OR ALTER VIEW [dbo].[vw_UnlinkedChannels] AS
SELECT
    c.[Stream_ID]          AS ChannelID,
    c.[TagName]            AS TagName,
    c.[SignalInterface_ID] AS SignalInterfaceID,
    si.[Name]              AS SignalInterfaceName,
    COUNT(o.[Observation_ID]) AS ObservationCount,
    MIN(o.[Timestamp])     AS FirstObservation,
    MAX(o.[Timestamp])     AS LastObservation
FROM [dbo].[Channel] c
JOIN [dbo].[Observation] o ON o.[Channel_ID] = c.[Stream_ID]
LEFT JOIN [dbo].[SignalInterface] si ON si.[SignalInterface_ID] = c.[SignalInterface_ID]
WHERE c.[SignalInterface_ID] IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM [dbo].[EquipmentWiringHistory] ewh
      WHERE ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
        AND ewh.[ValidTo] IS NULL
  )
GROUP BY c.[Stream_ID], c.[TagName], c.[SignalInterface_ID], si.[Name];

GO

GO

CREATE OR ALTER VIEW [dbo].[vw_ChannelEquipmentAtTime] AS
WITH channel_wiring AS (
    SELECT
        o.[Observation_ID] AS ObservationID,
        c.[Stream_ID]      AS ChannelID,
        o.[Timestamp]      AS Timestamp,
        c.[SignalInterface_ID],
        c.[SignalInterfacePort_ID],
        ewh.[Equipment_ID] AS EquipmentID,
        ROW_NUMBER() OVER (
            PARTITION BY o.[Observation_ID]
            ORDER BY
                CASE WHEN ewh.[SignalInterfacePort_ID] IS NOT NULL THEN 0 ELSE 1 END,
                ewh.[ValidFrom] DESC
        ) AS rn,
        COUNT(*) OVER (PARTITION BY o.[Observation_ID]) AS match_count
    FROM [dbo].[Observation] o
    JOIN [dbo].[vw_ChannelResolved] c           ON c.[Stream_ID]            = o.[Channel_ID]
    LEFT JOIN [dbo].[EquipmentWiringHistory] ewh ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
                                                AND (
                                                     ewh.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID]
                                                     OR (ewh.[SignalInterfacePort_ID] IS NULL AND c.[SignalInterfacePort_ID] IS NULL)
                                                     OR c.[SignalInterfacePort_ID] IS NULL
                                                    )
                                                AND ewh.[ValidFrom] <= o.[Timestamp]
                                                AND (ewh.[ValidTo] IS NULL OR ewh.[ValidTo] > o.[Timestamp])
)
SELECT
    cw.ObservationID,
    cw.ChannelID,
    cw.Timestamp,
    CASE WHEN cw.match_count > 1 AND cw.[SignalInterfacePort_ID] IS NULL THEN NULL ELSE cw.EquipmentID END AS EquipmentID,
    e.[Identifier]     AS EquipmentName,
    CASE
        WHEN cw.EquipmentID IS NULL AND cw.match_count = 0 THEN N'unlinked'
        WHEN cw.match_count > 1 AND cw.[SignalInterfacePort_ID] IS NULL THEN N'ambiguous'
        ELSE N'resolved'
    END AS Resolution
FROM channel_wiring cw
LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = cw.EquipmentID
WHERE cw.rn = 1;

GO

GO

CREATE OR ALTER VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Stream_ID]       AS StatusChannelID,
    valueC.[Stream_ID]        AS MeasurementChannelID,
    e.[Equipment_ID]          AS EquipmentID,
    e.[Identifier]            AS EquipmentName,
    p.[Parameter]             AS MeasurementParameter,
    o.[Timestamp],
    CAST(v.[Value] AS INT)    AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]   o       ON o.[Observation_ID]   = v.[Observation_ID]
JOIN [dbo].[Channel]       statusC ON statusC.[Stream_ID]  = o.[Channel_ID]
JOIN [dbo].[ChannelKind]   role    ON role.[ChannelKind_ID] = statusC.[ChannelKind_ID]
JOIN [dbo].[vw_ChannelResolved] valueC ON valueC.[Stream_ID] = statusC.[ParentChannel_ID]
JOIN [dbo].[Parameter]     p       ON p.[Parameter_ID]     = valueC.[Parameter_ID]
LEFT JOIN [dbo].[EquipmentWiringHistory] ewh
       ON ewh.[SignalInterface_ID] = valueC.[SignalInterface_ID]
      AND (
           ewh.[SignalInterfacePort_ID] = valueC.[SignalInterfacePort_ID]
           OR valueC.[SignalInterfacePort_ID] IS NULL
          )
      AND ewh.[ValidTo] IS NULL
LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ewh.[Equipment_ID]
WHERE role.[Name] = N'Status'
  AND statusC.[ParentChannel_ID] IS NOT NULL;

GO

GO

CREATE OR ALTER VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Stream_ID]        AS StatusChannelID,
    e.[Equipment_ID]           AS EquipmentID,
    e.[Identifier]             AS EquipmentName,
    o.[Timestamp],
    CAST(v.[Value] AS INT)     AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]  o       ON o.[Observation_ID]   = v.[Observation_ID]
JOIN [dbo].[Channel]      statusC ON statusC.[Stream_ID]  = o.[Channel_ID]
JOIN [dbo].[ChannelKind]  role    ON role.[ChannelKind_ID] = statusC.[ChannelKind_ID]
JOIN [dbo].[vw_ChannelResolved] valueC ON valueC.[Stream_ID] = statusC.[ParentChannel_ID]
JOIN [dbo].[EquipmentWiringHistory] ewh
       ON ewh.[SignalInterface_ID] = valueC.[SignalInterface_ID]
      AND (
           ewh.[SignalInterfacePort_ID] = valueC.[SignalInterfacePort_ID]
           OR valueC.[SignalInterfacePort_ID] IS NULL
          )
      AND ewh.[ValidTo] IS NULL
JOIN [dbo].[Equipment]    e       ON e.[Equipment_ID]     = ewh.[Equipment_ID]
WHERE role.[Name] = N'Status';

GO

GO

CREATE OR ALTER VIEW [dbo].[vw_ChannelLocationAtTime] AS
SELECT
    cea.ObservationID,
    cea.ChannelID,
    cea.Timestamp,
    cea.EquipmentID,
    cea.Resolution,
    elh.[SamplingPoint_ID] AS SamplingPointID,
    sp.[SamplingPoint]     AS SamplingPointName,
    CASE
        WHEN cea.EquipmentID IS NULL              THEN N'no-equipment'
        WHEN elh.[SamplingPoint_ID] IS NOT NULL   THEN N'resolved'
        ELSE N'no-location'
    END AS LocationResolution
FROM [dbo].[vw_ChannelEquipmentAtTime] cea
LEFT JOIN [dbo].[EquipmentLocationHistory] elh ON elh.[Equipment_ID] = cea.EquipmentID
                                              AND elh.[ValidFrom]   <= cea.Timestamp
                                              AND (elh.[ValidTo] IS NULL OR elh.[ValidTo] > cea.Timestamp)
LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID];

GO

INSERT INTO [dbo].[SchemaVersion] ([Version], [Description]) VALUES (N'2.1.0', N'Consolidated release covering all schema work since the 2.0.0 baseline: Stream supertype (Channel/AnalysisSeries repoint PK to Stream_ID), OperationKind replaces ProcessingKind, EquipmentEvent generalised into an 8-FK exclusive-arc Event table, LabAnalysis review workflow, multi-site campaigns, and broken-link/DAS-move coherence visibility views. See migrations/v2.0.0_to_v2.1.0_mssql.sql for the full change list.');
