-- Migration: v2.1.0 -> v2.0.0 (ROLLBACK)
-- Platform: mssql
-- Generated: 2026-07-06 17:29:46 UTC
-- Rollback: v2.1.0_to_v2.0.0_mssql_rollback.sql


DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'2.1.0';

DELETE FROM [dbo].[ParameterHasUnit] WHERE [Parameter_ID] IN (19, 20, 21, 22, 23, 24);

DELETE FROM [dbo].[Parameter] WHERE [Parameter_ID] IN (19, 20, 21, 22, 23, 24);

DELETE FROM [dbo].[Procedures] WHERE [Procedure_ID] IN (1, 2, 3);

DELETE FROM [dbo].[Unit] WHERE [Unit_ID] IN (14, 15, 16, 17);

ALTER TABLE [dbo].[ChannelTrait] DROP CONSTRAINT [FK_ChannelTrait_Stream_ID];

ALTER TABLE [dbo].[ChannelTrait] DROP CONSTRAINT [FK_ChannelTrait_OperationKind_ID];

ALTER TABLE [dbo].[Event] DROP CONSTRAINT [FK_Event_Channel_ID];

ALTER TABLE [dbo].[Event] DROP CONSTRAINT [FK_Event_Equipment_ID];

ALTER TABLE [dbo].[Event] DROP CONSTRAINT [FK_Event_SignalInterface_ID];

ALTER TABLE [dbo].[Event] DROP CONSTRAINT [FK_Event_DataAcquisitionSystem_ID];

ALTER TABLE [dbo].[Event] DROP CONSTRAINT [FK_Event_SamplingPoint_ID];

ALTER TABLE [dbo].[Event] DROP CONSTRAINT [FK_Event_ProcessUnit_ID];

ALTER TABLE [dbo].[Event] DROP CONSTRAINT [FK_Event_Site_ID];

ALTER TABLE [dbo].[Event] DROP CONSTRAINT [FK_Event_Campaign_ID];

ALTER TABLE [dbo].[Event] DROP CONSTRAINT [FK_Event_EventKind_ID];

ALTER TABLE [dbo].[Event] DROP CONSTRAINT [FK_Event_PerformedByPerson_ID];

ALTER TABLE [dbo].[Event] DROP CONSTRAINT [FK_Event_RecordedByPerson_ID];

ALTER TABLE [dbo].[Stream] DROP CONSTRAINT [FK_Stream_StreamKind_ID];

ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [FK_AnalysisSeries_Stream_ID];

ALTER TABLE [dbo].[AnalysisSeriesAxis] DROP CONSTRAINT [FK_AnalysisSeriesAxis_AnalysisSeries_ID];

ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [FK_Annotation_Stream_ID];

ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [FK_Annotation_Event_ID];

ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [FK_Channel_Stream_ID];

ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [FK_Channel_ParentChannel_ID];

ALTER TABLE [dbo].[ChannelAxis] DROP CONSTRAINT [FK_ChannelAxis_Channel_ID];

ALTER TABLE [dbo].[ChannelPortHistory] DROP CONSTRAINT [FK_ChannelPortHistory_Channel_ID];

ALTER TABLE [dbo].[ControlLoopPort] DROP CONSTRAINT [FK_ControlLoopPort_Stream_ID];

ALTER TABLE [dbo].[DatasetChannel] DROP CONSTRAINT [FK_DatasetChannel_Channel_ID];

ALTER TABLE [dbo].[LabAnalysis] DROP CONSTRAINT [FK_LabAnalysis_AnalysisSeries_ID];

ALTER TABLE [dbo].[LabAnalysis] DROP CONSTRAINT [FK_LabAnalysis_ReviewStatus_ID];

ALTER TABLE [dbo].[LabAnalysis] DROP CONSTRAINT [FK_LabAnalysis_ReviewedByPerson_ID];

ALTER TABLE [dbo].[LabPanelSeries] DROP CONSTRAINT [FK_LabPanelSeries_AnalysisSeries_ID];

ALTER TABLE [dbo].[Observation] DROP CONSTRAINT [FK_Observation_Channel_ID];

ALTER TABLE [dbo].[ProcessingLineage] DROP CONSTRAINT [FK_ProcessingLineage_Stream_ID];

ALTER TABLE [dbo].[ProcessingStep] DROP CONSTRAINT [FK_ProcessingStep_OperationKind_ID];

ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [UQ_AnalysisSeries_Identity];

DROP INDEX [IX_ChannelTrait_Stream] ON [dbo].[ChannelTrait];

DROP INDEX [IX_Event_Equipment_Start] ON [dbo].[Event];

DROP INDEX [IX_Event_Channel_Start] ON [dbo].[Event];

DROP INDEX [IX_Event_Site_Start] ON [dbo].[Event];

DROP INDEX [IX_Event_Start] ON [dbo].[Event];

DROP INDEX [IX_Annotation_Stream_Time] ON [dbo].[Annotation];

DROP INDEX [UQ_ControlLoopPort_LoopStream] ON [dbo].[ControlLoopPort];

DROP INDEX [IX_ProcessingLineage_Stream] ON [dbo].[ProcessingLineage];

ALTER TABLE [dbo].[AnalysisSeries] ADD [AnalysisSeries_ID] INT IDENTITY(1,1) NOT NULL;

-- Manual: undo the Stream_ID PK repoint — restore AnalysisSeries_ID as PK.
ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [PK_AnalysisSeries];

ALTER TABLE [dbo].[AnalysisSeries] ADD CONSTRAINT [PK_AnalysisSeries] PRIMARY KEY ([AnalysisSeries_ID]);

ALTER TABLE [dbo].[AnalysisSeries] ADD [ProcessingKind_ID] INT NOT NULL DEFAULT 1;

ALTER TABLE [dbo].[Annotation] ADD [Channel_ID] INT;

ALTER TABLE [dbo].[Annotation] ADD [AnalysisSeries_ID] INT;

ALTER TABLE [dbo].[Annotation] ADD [EquipmentEvent_ID] INT;

ALTER TABLE [dbo].[Campaign] ADD [Site_ID] INT NOT NULL;

ALTER TABLE [dbo].[Channel] ADD [Channel_ID] INT IDENTITY(1,1) NOT NULL;

-- Manual: undo the Stream_ID PK repoint — restore Channel_ID as PK.
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [PK_Channel];

ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [PK_Channel] PRIMARY KEY ([Channel_ID]);

ALTER TABLE [dbo].[Channel] ADD [SignalInterfacePort_ID] INT;

ALTER TABLE [dbo].[ControlLoopPort] ADD [Channel_ID] INT NOT NULL;

ALTER TABLE [dbo].[ProcessingLineage] ADD [Channel_ID] INT NOT NULL;

ALTER TABLE [dbo].[ProcessingStep] ADD [ProcessingKind_ID] INT;

CREATE INDEX [IX_Annotation_Channel_Time] ON [dbo].[Annotation] ([Channel_ID], [StartTime], [EndTime]);

CREATE INDEX [IX_Annotation_Series_Time] ON [dbo].[Annotation] ([AnalysisSeries_ID], [StartTime], [EndTime]);

CREATE UNIQUE INDEX [UQ_ControlLoopPort_LoopChannel] ON [dbo].[ControlLoopPort] ([ControlLoop_ID], [Channel_ID]);

CREATE INDEX [IX_ProcessingLineage_Channel] ON [dbo].[ProcessingLineage] ([Channel_ID]);

ALTER TABLE [dbo].[AnalysisSeries] ADD CONSTRAINT [UQ_AnalysisSeries_Identity] UNIQUE ([Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [ProcessingKind_ID]);

GO

ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [CK_Annotation_Source] CHECK ((Channel_ID IS NOT NULL AND AnalysisSeries_ID IS NULL) OR (Channel_ID IS NULL AND AnalysisSeries_ID IS NOT NULL));

GO

ALTER TABLE [dbo].[EquipmentLocationHistory] ALTER COLUMN [Campaign_ID] INT;

ALTER TABLE [dbo].[EquipmentModel] ALTER COLUMN [ManualLocation] NVARCHAR(100);

ALTER TABLE [dbo].[HydrologicalCharacteristics] ALTER COLUMN [Watershed_ID] INT;

ALTER TABLE [dbo].[LandUse] ALTER COLUMN [Watershed_ID] INT;

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.AnalysisSeries') AND c.name = 'Stream_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[AnalysisSeries] DROP COLUMN [Stream_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.Annotation') AND c.name = 'Stream_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[Annotation] DROP COLUMN [Stream_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.Annotation') AND c.name = 'Event_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[Annotation] DROP COLUMN [Event_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.Channel') AND c.name = 'Stream_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[Channel] DROP COLUMN [Stream_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.ControlLoopPort') AND c.name = 'Stream_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[ControlLoopPort] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[ControlLoopPort] DROP COLUMN [Stream_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.LabAnalysis') AND c.name = 'ReviewStatus_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[LabAnalysis] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[LabAnalysis] DROP COLUMN [ReviewStatus_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.LabAnalysis') AND c.name = 'ReviewedByPerson_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[LabAnalysis] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[LabAnalysis] DROP COLUMN [ReviewedByPerson_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.LabAnalysis') AND c.name = 'ReviewDateTime';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[LabAnalysis] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[LabAnalysis] DROP COLUMN [ReviewDateTime];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.ProcessingLineage') AND c.name = 'Stream_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[ProcessingLineage] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[ProcessingLineage] DROP COLUMN [Stream_ID];

GO

DECLARE @df NVARCHAR(200);
SELECT @df = dc.name FROM sys.default_constraints dc
JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
WHERE dc.parent_object_id = OBJECT_ID('dbo.ProcessingStep') AND c.name = 'OperationKind_ID';
IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[ProcessingStep] DROP CONSTRAINT [' + @df + ']');

GO

ALTER TABLE [dbo].[ProcessingStep] DROP COLUMN [OperationKind_ID];

DROP TABLE [dbo].[Stream];

DROP TABLE [dbo].[Event];

DROP TABLE [dbo].[ChannelTrait];

DROP TABLE [dbo].[StreamKind];

DROP TABLE [dbo].[ReviewStatus];

DROP TABLE [dbo].[OperationKind];

DROP TABLE [dbo].[EventKind];

CREATE TABLE [dbo].[EquipmentEventKind] (
    [EquipmentEventKind_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(100) NOT NULL,
    [Description] NVARCHAR(300),
    CONSTRAINT [PK_EquipmentEventKind] PRIMARY KEY ([EquipmentEventKind_ID])
);

CREATE TABLE [dbo].[ProcessingKind] (
    [ProcessingKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_ProcessingKind] PRIMARY KEY ([ProcessingKind_ID])
);

CREATE TABLE [dbo].[EquipmentEvent] (
    [EquipmentEvent_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID] INT NOT NULL,
    [EquipmentEventKind_ID] INT NOT NULL,
    [EventDateTimeStart] DATETIME2(7) NOT NULL,
    [IsInstantaneous] BIT NOT NULL DEFAULT 0,
    [EventDateTimeEnd] DATETIME2(7),
    [PerformedByPerson_ID] INT,
    [RecordedByPerson_ID] INT,
    [Notes] NVARCHAR(MAX),
    CONSTRAINT [PK_EquipmentEvent] PRIMARY KEY ([EquipmentEvent_ID])
);

CREATE INDEX [IX_EquipmentEvent_Equipment_Start] ON [dbo].[EquipmentEvent] ([Equipment_ID], [EventDateTimeStart]);

ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_Equipment_ID] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);

ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_EquipmentEventKind_ID] FOREIGN KEY ([EquipmentEventKind_ID]) REFERENCES [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID]);

ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_PerformedByPerson_ID] FOREIGN KEY ([PerformedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);

ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_RecordedByPerson_ID] FOREIGN KEY ([RecordedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);

ALTER TABLE [dbo].[AnalysisSeries] ADD CONSTRAINT [FK_AnalysisSeries_ProcessingKind_ID] FOREIGN KEY ([ProcessingKind_ID]) REFERENCES [dbo].[ProcessingKind] ([ProcessingKind_ID]);

ALTER TABLE [dbo].[AnalysisSeriesAxis] ADD CONSTRAINT [FK_AnalysisSeriesAxis_AnalysisSeries_ID] FOREIGN KEY ([AnalysisSeries_ID]) REFERENCES [dbo].[AnalysisSeries] ([AnalysisSeries_ID]);

ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);

ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_AnalysisSeries_ID] FOREIGN KEY ([AnalysisSeries_ID]) REFERENCES [dbo].[AnalysisSeries] ([AnalysisSeries_ID]);

ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_EquipmentEvent_ID] FOREIGN KEY ([EquipmentEvent_ID]) REFERENCES [dbo].[EquipmentEvent] ([EquipmentEvent_ID]);

ALTER TABLE [dbo].[Campaign] ADD CONSTRAINT [FK_Campaign_Site_ID] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]);

ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_SignalInterfacePort_ID] FOREIGN KEY ([SignalInterfacePort_ID]) REFERENCES [dbo].[SignalInterfacePort] ([SignalInterfacePort_ID]);

ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_ParentChannel_ID] FOREIGN KEY ([ParentChannel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);

ALTER TABLE [dbo].[ChannelAxis] ADD CONSTRAINT [FK_ChannelAxis_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);

ALTER TABLE [dbo].[ChannelPortHistory] ADD CONSTRAINT [FK_ChannelPortHistory_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);

ALTER TABLE [dbo].[ControlLoopPort] ADD CONSTRAINT [FK_ControlLoopPort_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);

ALTER TABLE [dbo].[DatasetChannel] ADD CONSTRAINT [FK_DatasetChannel_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);

ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_AnalysisSeries_ID] FOREIGN KEY ([AnalysisSeries_ID]) REFERENCES [dbo].[AnalysisSeries] ([AnalysisSeries_ID]);

ALTER TABLE [dbo].[LabPanelSeries] ADD CONSTRAINT [FK_LabPanelSeries_AnalysisSeries_ID] FOREIGN KEY ([AnalysisSeries_ID]) REFERENCES [dbo].[AnalysisSeries] ([AnalysisSeries_ID]);

ALTER TABLE [dbo].[Observation] ADD CONSTRAINT [FK_Observation_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);

ALTER TABLE [dbo].[ProcessingLineage] ADD CONSTRAINT [FK_ProcessingLineage_Channel_ID] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);

ALTER TABLE [dbo].[ProcessingStep] ADD CONSTRAINT [FK_ProcessingStep_ProcessingKind_ID] FOREIGN KEY ([ProcessingKind_ID]) REFERENCES [dbo].[ProcessingKind] ([ProcessingKind_ID]);

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

-- ProcessingKind
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (1, N'Raw', N'Original, unmodified data as received from the source');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (2, N'Free of outliers', N'Spikes and statistical outliers have been removed or flagged');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (3, N'Free of drift', N'Sensor drift or baseline shift has been corrected');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (4, N'Free of faults', N'Instrument faults and implausible values have been removed');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (5, N'Smoothed', N'Noise reduced by a smoothing or averaging algorithm');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (6, N'Interpolated', N'Missing values filled by interpolation');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (7, N'Predicted', N'Values generated by a predictive model or algorithm');
INSERT INTO [dbo].[ProcessingKind] ([ProcessingKind_ID], [Name], [Description]) VALUES (8, N'Derived', N'Computed from one or more other channels (e.g. dimensionality reduction, transformation)');

GO

DROP VIEW [dbo].[vw_UnlinkedChannels];

GO

GO

DROP VIEW [dbo].[vw_InactiveParentReferences];

GO

GO

DROP VIEW [dbo].[vw_DeploymentCoherence];

GO

GO

DROP VIEW [dbo].[vw_ChannelResolved];

GO

GO

CREATE OR ALTER VIEW [dbo].[vw_ChannelEquipmentAtTime] AS
WITH channel_wiring AS (
    SELECT
        o.[Observation_ID] AS ObservationID,
        c.[Channel_ID]     AS ChannelID,
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
    JOIN [dbo].[Channel] c                      ON c.[Channel_ID]           = o.[Channel_ID]
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
    statusC.[Channel_ID]      AS StatusChannelID,
    valueC.[Channel_ID]       AS MeasurementChannelID,
    e.[Equipment_ID]          AS EquipmentID,
    e.[Identifier]            AS EquipmentName,
    p.[Parameter]             AS MeasurementParameter,
    o.[Timestamp],
    CAST(v.[Value] AS INT)    AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]   o       ON o.[Observation_ID]   = v.[Observation_ID]
JOIN [dbo].[Channel]       statusC ON statusC.[Channel_ID] = o.[Channel_ID]
JOIN [dbo].[ChannelKind]   role    ON role.[ChannelKind_ID] = statusC.[ChannelKind_ID]
JOIN [dbo].[Channel]       valueC  ON valueC.[Channel_ID]   = statusC.[ParentChannel_ID]
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
    statusC.[Channel_ID]       AS StatusChannelID,
    e.[Equipment_ID]           AS EquipmentID,
    e.[Identifier]             AS EquipmentName,
    o.[Timestamp],
    CAST(v.[Value] AS INT)     AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]  o       ON o.[Observation_ID]   = v.[Observation_ID]
JOIN [dbo].[Channel]      statusC ON statusC.[Channel_ID] = o.[Channel_ID]
JOIN [dbo].[ChannelKind]  role    ON role.[ChannelKind_ID] = statusC.[ChannelKind_ID]
JOIN [dbo].[Channel]      valueC  ON valueC.[Channel_ID]   = statusC.[ParentChannel_ID]
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
    elh.[SamplingPoint_ID] AS SamplingPointID,
    sp.[SamplingPoint]     AS SamplingPointName
FROM [dbo].[vw_ChannelEquipmentAtTime] cea
LEFT JOIN [dbo].[EquipmentLocationHistory] elh ON elh.[Equipment_ID] = cea.EquipmentID
                                              AND elh.[ValidFrom]   <= cea.Timestamp
                                              AND (elh.[ValidTo] IS NULL OR elh.[ValidTo] > cea.Timestamp)
LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID];

GO
