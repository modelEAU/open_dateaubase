-- ============================================================
-- Rollback: v2.2.0 --> v2.1.0
-- Platform:  mssql
-- Generated: 2026-03-16
-- Forward:   migrations/v2.1.0_to_v2.2.0_mssql.sql
--
-- WARNING: Test in a dev environment before running on production data.
-- Rebuilding IDENTITY columns (Value_ID, ValueImage_ID) uses a temp-column pattern
-- because SQL Server cannot add IDENTITY to existing columns.
--
-- NOTE: Value_ID and ValueImage_ID will be synthetic surrogates after rollback.
-- Original IDENTITY values are not restored.
-- ============================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;
SET QUOTED_IDENTIFIER ON;

-- Guards
IF OBJECT_ID('dbo.Observation') IS NULL
    RAISERROR('Observation table not found — this rollback expects v2.2.0 schema (already rolled back?).', 16, 1);
IF OBJECT_ID('dbo.Value') IS NULL
    RAISERROR('Value table not found — something is wrong with this database.', 16, 1);
GO

BEGIN TRANSACTION;
GO

-- ==============================================================
-- ROLLBACK STEP 1: Restore views to pre-v2.2.0 form
-- Drop views now; recreate after Value is restored (Step 8).
-- At this point Value still has Observation_ID; old views will be
-- replaced once Value has Channel_ID + Timestamp back.
-- ==============================================================
DROP VIEW IF EXISTS [dbo].[vw_ChannelStatus];
DROP VIEW IF EXISTS [dbo].[vw_DeviceStatus];
GO

-- ==============================================================
-- ROLLBACK STEP 2: Remove Annotation.Observation_ID
-- ==============================================================
ALTER TABLE [dbo].[Annotation] DROP CONSTRAINT [FK_Annotation_Observation];
ALTER TABLE [dbo].[Annotation] DROP COLUMN [Observation_ID];
GO

-- ==============================================================
-- ROLLBACK STEP 3: Restore ValueImage
-- ==============================================================

-- Add back Channel_ID and Timestamp from Observation join (nullable until populated).
ALTER TABLE [dbo].[ValueImage] ADD [Channel_ID] INT NULL;
ALTER TABLE [dbo].[ValueImage] ADD [Timestamp]  DATETIME2(7) NULL;
GO

-- Populate from Observation.
UPDATE vi
SET vi.[Channel_ID] = o.[Channel_ID],
    vi.[Timestamp]  = o.[Timestamp]
FROM [dbo].[ValueImage] vi
JOIN [dbo].[Observation] o ON o.[Observation_ID] = vi.[Observation_ID];
GO

-- Make non-nullable now that all rows are populated.
ALTER TABLE [dbo].[ValueImage] ALTER COLUMN [Channel_ID] INT NOT NULL;
ALTER TABLE [dbo].[ValueImage] ALTER COLUMN [Timestamp]  DATETIME2(7) NOT NULL;
GO

-- Drop FK_ValueImage_Observation and current PK (on Observation_ID).
ALTER TABLE [dbo].[ValueImage] DROP CONSTRAINT [FK_ValueImage_Observation];
ALTER TABLE [dbo].[ValueImage] DROP CONSTRAINT [PK_ValueImage];
GO

-- Drop Observation_ID column.
ALTER TABLE [dbo].[ValueImage] DROP COLUMN [Observation_ID];
GO

-- Restore synthetic surrogate ValueImage_ID (IDENTITY values not recoverable;
-- use ROW_NUMBER pattern since SQL Server cannot ADD IDENTITY to existing columns).
ALTER TABLE [dbo].[ValueImage] ADD [ValueImage_ID] BIGINT NULL;
GO

UPDATE vi
SET vi.[ValueImage_ID] = rn.rn
FROM [dbo].[ValueImage] vi
JOIN (
    SELECT [Channel_ID], [Timestamp],
           ROW_NUMBER() OVER (ORDER BY [Channel_ID], [Timestamp]) AS rn
    FROM [dbo].[ValueImage]
) rn ON rn.[Channel_ID] = vi.[Channel_ID] AND rn.[Timestamp] = vi.[Timestamp];
GO

-- Make non-nullable and restore PK + constraints.
ALTER TABLE [dbo].[ValueImage] ALTER COLUMN [ValueImage_ID] BIGINT NOT NULL;
ALTER TABLE [dbo].[ValueImage] ADD CONSTRAINT [PK_ValueImage] PRIMARY KEY ([ValueImage_ID]);
ALTER TABLE [dbo].[ValueImage] ADD CONSTRAINT [UQ_ValueImage_ChannelTimestamp] UNIQUE ([Channel_ID], [Timestamp]);
ALTER TABLE [dbo].[ValueImage] ADD CONSTRAINT [FK_ValueImage_Channel]
    FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
GO

-- ==============================================================
-- ROLLBACK STEP 4: Restore ValueMatrix
-- ==============================================================

-- Add back Channel_ID and Timestamp (nullable until populated).
ALTER TABLE [dbo].[ValueMatrix] ADD [Channel_ID] INT NULL;
ALTER TABLE [dbo].[ValueMatrix] ADD [Timestamp]  DATETIME2(7) NULL;
GO

-- Populate from Observation.
UPDATE vm
SET vm.[Channel_ID] = o.[Channel_ID],
    vm.[Timestamp]  = o.[Timestamp]
FROM [dbo].[ValueMatrix] vm
JOIN [dbo].[Observation] o ON o.[Observation_ID] = vm.[Observation_ID];
GO

-- Make non-nullable.
ALTER TABLE [dbo].[ValueMatrix] ALTER COLUMN [Channel_ID] INT NOT NULL;
ALTER TABLE [dbo].[ValueMatrix] ALTER COLUMN [Timestamp]  DATETIME2(7) NOT NULL;
GO

-- Drop FK_ValueMatrix_Observation and current PK.
ALTER TABLE [dbo].[ValueMatrix] DROP CONSTRAINT [FK_ValueMatrix_Observation];
ALTER TABLE [dbo].[ValueMatrix] DROP CONSTRAINT [PK_ValueMatrix];
GO

-- Drop Observation_ID column.
ALTER TABLE [dbo].[ValueMatrix] DROP COLUMN [Observation_ID];
GO

-- Restore original composite PK and FK.
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [PK_ValueMatrix]
    PRIMARY KEY ([Channel_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_Channel]
    FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
GO

-- ==============================================================
-- ROLLBACK STEP 5: Restore ValueVector
-- ==============================================================

-- Add back Channel_ID and Timestamp (nullable until populated).
ALTER TABLE [dbo].[ValueVector] ADD [Channel_ID] INT NULL;
ALTER TABLE [dbo].[ValueVector] ADD [Timestamp]  DATETIME2(7) NULL;
GO

-- Populate from Observation.
UPDATE vv
SET vv.[Channel_ID] = o.[Channel_ID],
    vv.[Timestamp]  = o.[Timestamp]
FROM [dbo].[ValueVector] vv
JOIN [dbo].[Observation] o ON o.[Observation_ID] = vv.[Observation_ID];
GO

-- Make non-nullable.
ALTER TABLE [dbo].[ValueVector] ALTER COLUMN [Channel_ID] INT NOT NULL;
ALTER TABLE [dbo].[ValueVector] ALTER COLUMN [Timestamp]  DATETIME2(7) NOT NULL;
GO

-- Drop FK_ValueVector_Observation and current PK.
ALTER TABLE [dbo].[ValueVector] DROP CONSTRAINT [FK_ValueVector_Observation];
ALTER TABLE [dbo].[ValueVector] DROP CONSTRAINT [PK_ValueVector];
GO

-- Drop Observation_ID column.
ALTER TABLE [dbo].[ValueVector] DROP COLUMN [Observation_ID];
GO

-- Restore original composite PK and FK.
ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [PK_ValueVector]
    PRIMARY KEY ([Channel_ID], [Timestamp], [ValueBin_ID]);
ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [FK_ValueVector_Channel]
    FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
GO

-- ==============================================================
-- ROLLBACK STEP 6: Restore Value
-- ==============================================================

-- Add back Channel_ID + Timestamp (nullable until populated).
ALTER TABLE [dbo].[Value] ADD [Channel_ID] INT NULL;
ALTER TABLE [dbo].[Value] ADD [Timestamp]  DATETIME2(7) NULL;
GO

-- Populate from Observation.
UPDATE v
SET v.[Channel_ID] = o.[Channel_ID],
    v.[Timestamp]  = o.[Timestamp]
FROM [dbo].[Value] v
JOIN [dbo].[Observation] o ON o.[Observation_ID] = v.[Observation_ID];
GO

-- Make non-nullable.
ALTER TABLE [dbo].[Value] ALTER COLUMN [Channel_ID] INT NOT NULL;
ALTER TABLE [dbo].[Value] ALTER COLUMN [Timestamp]  DATETIME2(7) NOT NULL;
GO

-- Drop FK + PK on Observation_ID.
ALTER TABLE [dbo].[Value] DROP CONSTRAINT [FK_Value_Observation];
ALTER TABLE [dbo].[Value] DROP CONSTRAINT [PK_Value];
GO

-- Drop Observation_ID column.
ALTER TABLE [dbo].[Value] DROP COLUMN [Observation_ID];
GO

-- Add synthetic Value_ID (not original IDENTITY values — structure only).
-- SQL Server cannot add IDENTITY to an existing column; use ROW_NUMBER pattern.
ALTER TABLE [dbo].[Value] ADD [Value_ID] BIGINT NULL;
GO

UPDATE v
SET v.[Value_ID] = rn.rn
FROM [dbo].[Value] v
JOIN (
    SELECT [Channel_ID], [Timestamp],
           ROW_NUMBER() OVER (ORDER BY [Channel_ID], [Timestamp]) AS rn
    FROM [dbo].[Value]
) rn ON rn.[Channel_ID] = v.[Channel_ID] AND rn.[Timestamp] = v.[Timestamp];
GO

-- Make non-nullable and restore PK + FK.
ALTER TABLE [dbo].[Value] ALTER COLUMN [Value_ID] BIGINT NOT NULL;
ALTER TABLE [dbo].[Value] ADD CONSTRAINT [PK_Value] PRIMARY KEY ([Value_ID]);
ALTER TABLE [dbo].[Value] ADD CONSTRAINT [FK_Value_Channel]
    FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
GO

-- ==============================================================
-- ROLLBACK STEP 7: Drop Observation table
-- (all FK references removed in Steps 3-6 above)
-- ==============================================================
DROP TABLE [dbo].[Observation];
GO

-- ==============================================================
-- ROLLBACK STEP 8: Restore views (v2.1.0 form — Value has Channel_ID back)
-- ==============================================================
CREATE OR ALTER VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    statusC.[StatusChannel_ID]  AS MeasurementChannelID,
    measC.[Equipment_ID]        AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    p.[Parameter]               AS MeasurementParameter,
    v.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Channel]   statusC ON statusC.[Channel_ID]       = v.[Channel_ID]
JOIN [dbo].[Channel]   measC   ON measC.[Channel_ID]         = statusC.[StatusChannel_ID]
JOIN [dbo].[Parameter] p       ON p.[Parameter_ID]           = measC.[Parameter_ID]
JOIN [dbo].[Equipment] e       ON e.[Equipment_ID]           = measC.[Equipment_ID]
WHERE statusC.[StatusChannel_ID] IS NOT NULL;
GO

CREATE OR ALTER VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    esc.[Equipment_ID]          AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Channel]                statusC ON statusC.[Channel_ID]   = v.[Channel_ID]
JOIN [dbo].[EquipmentStatusChannel] esc     ON esc.[StatusChannel_ID] = statusC.[Channel_ID]
JOIN [dbo].[Equipment]              e       ON e.[Equipment_ID]       = esc.[Equipment_ID];
GO

-- ==============================================================
-- ROLLBACK STEP 9: Record rollback in SchemaVersion
-- ==============================================================
INSERT INTO [dbo].[SchemaVersion] ([Version], [Description], [MigrationScript])
VALUES (
    '2.1.0',
    'Rolled back v2.2.0 Observation migration',
    'v2.1.0_to_v2.2.0_mssql_rollback.sql'
);
GO

COMMIT TRANSACTION;
GO

PRINT 'Rollback to v2.1.0 completed. NOTE: Value_ID and ValueImage_ID are synthetic surrogates — original IDENTITY values are not restored.';
