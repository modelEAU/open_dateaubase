-- Migration: v1.7.0 -> v1.8.0
-- Platform: mssql
-- Generated: 2026-02-18
-- Rollback: v1.7.0_to_v1.8.0_mssql_rollback.sql

-- Create SensorStatusCode lookup table
CREATE TABLE [dbo].[SensorStatusCode] (
    [StatusCodeID] INT NOT NULL,
    [StatusName] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200) NULL,
    [IsOperational] BIT NOT NULL DEFAULT 1,
    [Severity] INT NOT NULL DEFAULT 0,
    CONSTRAINT [PK_SensorStatusCode] PRIMARY KEY ([StatusCodeID])
);

-- Insert seed data for SensorStatusCode
INSERT INTO [dbo].[SensorStatusCode] ([StatusCodeID], [StatusName], [Description], [IsOperational], [Severity]) VALUES
    (0, N'Unknown', N'Status not reported or not available', 0, 1),
    (1, N'Operational', N'Sensor channel is functioning normally', 1, 0),
    (2, N'Warning', N'Sensor is operational but a warning condition exists', 1, 1),
    (3, N'Fault', N'Sensor channel has faulted, data is unreliable', 0, 2),
    (4, N'Maintenance', N'Sensor is undergoing maintenance', 0, 1),
    (5, N'Calibrating', N'Sensor channel is being calibrated', 0, 1),
    (6, N'Starting Up', N'Sensor is in startup/warmup phase', 0, 1),
    (7, N'Shutting Down', N'Sensor is shutting down', 0, 1),
    (8, N'Offline', N'Sensor is powered off or disconnected', 0, 0),
    (9, N'Degraded', N'Sensor is operational but accuracy may be reduced', 1, 1),
    (10, N'Fouled', N'Sensor probe is fouled, readings likely biased', 1, 2);

-- Add StatusOfMetaDataID column to MetaData
ALTER TABLE [dbo].[MetaData] ADD [StatusOfMetaDataID] INT NULL;

-- Add StatusOfEquipmentID column to MetaData
ALTER TABLE [dbo].[MetaData] ADD [StatusOfEquipmentID] INT NULL;

-- Add FK constraint for StatusOfMetaDataID (self-referential to MetaData)
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_StatusOfMetaDataID]
    FOREIGN KEY ([StatusOfMetaDataID]) REFERENCES [dbo].[MetaData] ([Metadata_ID]);

-- Add FK constraint for StatusOfEquipmentID
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_StatusOfEquipmentID]
    FOREIGN KEY ([StatusOfEquipmentID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);

-- Add CHECK constraint to ensure at most one status link is non-NULL
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [CK_MetaData_StatusTarget]
    CHECK (NOT ([StatusOfMetaDataID] IS NOT NULL AND [StatusOfEquipmentID] IS NOT NULL));

-- Seed Parameter rows for status time series
IF NOT EXISTS (SELECT 1 FROM [dbo].[Parameter] WHERE [Parameter] = N'Sensor Status')
    INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
    VALUES (N'Sensor Status', N'Per-channel operational status code. Values reference dbo.SensorStatusCode.');
GO

IF NOT EXISTS (SELECT 1 FROM [dbo].[Parameter] WHERE [Parameter] = N'Device Status')
    INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
    VALUES (N'Device Status', N'Overall equipment health status. Values reference dbo.SensorStatusCode.');
GO

-- Seed Unit row for status values
IF NOT EXISTS (SELECT 1 FROM [dbo].[Unit] WHERE [Unit] = N'Status Code')
    INSERT INTO [dbo].[Unit] ([Unit])
    VALUES (N'Status Code');
GO

-- Create convenience views
CREATE VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusMD.[Metadata_ID]        AS StatusMetaDataID,
    statusMD.[StatusOfMetaDataID] AS MeasurementMetaDataID,
    measMD.[Equipment_ID]         AS EquipmentID,
    e.[identifier]                AS EquipmentName,
    p.[Parameter]                 AS MeasurementParameter,
    sp.[Sampling_point]           AS LocationName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)        AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData] statusMD
    ON statusMD.[Metadata_ID] = v.[Metadata_ID]
JOIN [dbo].[MetaData] measMD
    ON measMD.[Metadata_ID] = statusMD.[StatusOfMetaDataID]
JOIN [dbo].[Parameter] p
    ON p.[Parameter_ID] = measMD.[Parameter_ID]
JOIN [dbo].[SamplingPoints] sp
    ON sp.[Sampling_point_ID] = measMD.[Sampling_point_ID]
JOIN [dbo].[Equipment] e
    ON e.[Equipment_ID] = measMD.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc
    ON sc.[StatusCodeID] = CAST(v.[Value] AS INT)
WHERE statusMD.[StatusOfMetaDataID] IS NOT NULL;
GO

CREATE VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusMD.[Metadata_ID]         AS StatusMetaDataID,
    statusMD.[StatusOfEquipmentID] AS EquipmentID,
    e.[identifier]                 AS EquipmentName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)         AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[MetaData] statusMD
    ON statusMD.[Metadata_ID] = v.[Metadata_ID]
JOIN [dbo].[Equipment] e
    ON e.[Equipment_ID] = statusMD.[StatusOfEquipmentID]
LEFT JOIN [dbo].[SensorStatusCode] sc
    ON sc.[StatusCodeID] = CAST(v.[Value] AS INT)
WHERE statusMD.[StatusOfEquipmentID] IS NOT NULL;
GO

-- Update SchemaVersion
INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.8.0',
    GETUTCDATE(),
    'Phase 5b: Sensor Status — SensorStatusCode lookup, MetaData status link columns, vw_ChannelStatus and vw_DeviceStatus views',
    'v1.7.0_to_v1.8.0_mssql.sql'
);
GO