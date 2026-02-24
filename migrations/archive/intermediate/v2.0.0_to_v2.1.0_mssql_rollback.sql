-- =============================================================================
-- Phase C — Rollback (v2.1.0 → v2.0.0)
-- =============================================================================
-- Reverses the Phase C forward migration:
--  1. Rebuild views using old column names
--  2. Add back StatusOfMetaDataID and StatusOfEquipmentID columns to Channel
--  3. Restore StatusOfMetaDataID data from StatusChannel_ID
--  4. Restore StatusOfEquipmentID data from EquipmentStatusChannel
--  5. Add back FK constraints
--  6. Add back check constraint
--  7. Drop FK_Channel_StatusChannel and StatusChannel_ID column
--  8. Drop EquipmentStatusChannel table
--  9. Insert SchemaVersion rollback row
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Step 1: Rebuild views using old column names
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS [dbo].[vw_ChannelStatus];
GO

CREATE VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Channel_ID]              AS StatusChannelID,
    statusC.[StatusOfMetaDataID]      AS MeasurementChannelID,
    measC.[Equipment_ID]              AS EquipmentID,
    e.[identifier]                    AS EquipmentName,
    p.[Parameter]                     AS MeasurementParameter,
    v.[Timestamp],
    CAST(v.[Value] AS INT)            AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]               statusC ON statusC.[Channel_ID]      = v.[Channel_ID]
JOIN [dbo].[Channel]               measC   ON measC.[Channel_ID]        = statusC.[StatusOfMetaDataID]
JOIN [dbo].[Parameter]             p       ON p.[Parameter_ID]          = measC.[Parameter_ID]
JOIN [dbo].[Equipment]             e       ON e.[Equipment_ID]          = measC.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc      ON sc.[StatusCodeID]         = CAST(v.[Value] AS INT)
WHERE statusC.[StatusOfMetaDataID] IS NOT NULL;
GO

DROP VIEW IF EXISTS [dbo].[vw_DeviceStatus];
GO

CREATE VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]              AS StatusChannelID,
    statusC.[StatusOfEquipmentID]     AS EquipmentID,
    e.[identifier]                    AS EquipmentName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)            AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]               statusC ON statusC.[Channel_ID]      = v.[Channel_ID]
JOIN [dbo].[Equipment]             e       ON e.[Equipment_ID]          = statusC.[StatusOfEquipmentID]
LEFT JOIN [dbo].[SensorStatusCode] sc      ON sc.[StatusCodeID]         = CAST(v.[Value] AS INT)
WHERE statusC.[StatusOfEquipmentID] IS NOT NULL;
GO

-- ---------------------------------------------------------------------------
-- Step 2: Add back StatusOfMetaDataID and StatusOfEquipmentID columns
-- ---------------------------------------------------------------------------
ALTER TABLE [dbo].[Channel]
    ADD [StatusOfMetaDataID]  INT NULL,
        [StatusOfEquipmentID] INT NULL;

-- ---------------------------------------------------------------------------
-- Step 3: Restore StatusOfMetaDataID from StatusChannel_ID
-- ---------------------------------------------------------------------------
UPDATE [dbo].[Channel]
SET    [StatusOfMetaDataID] = [StatusChannel_ID]
WHERE  [StatusChannel_ID] IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Step 4: Restore StatusOfEquipmentID from EquipmentStatusChannel
-- ---------------------------------------------------------------------------
UPDATE c
SET    c.[StatusOfEquipmentID] = esc.[Equipment_ID]
FROM   [dbo].[Channel]              c
JOIN   [dbo].[EquipmentStatusChannel] esc ON esc.[StatusChannel_ID] = c.[Channel_ID];

-- ---------------------------------------------------------------------------
-- Step 5: Add back FK constraints
-- ---------------------------------------------------------------------------
ALTER TABLE [dbo].[Channel]
    ADD CONSTRAINT [FK_MetaData_MetaData]
        FOREIGN KEY ([StatusOfMetaDataID]) REFERENCES [dbo].[Channel] ([Channel_ID]);

ALTER TABLE [dbo].[Channel]
    ADD CONSTRAINT [FK_Channel_StatusOfEquipment]
        FOREIGN KEY ([StatusOfEquipmentID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);

-- ---------------------------------------------------------------------------
-- Step 6: Add back check constraint
-- ---------------------------------------------------------------------------
ALTER TABLE [dbo].[Channel]
    ADD CONSTRAINT [CK_MetaData_StatusTarget]
        CHECK (NOT (StatusOfMetaDataID IS NOT NULL AND StatusOfEquipmentID IS NOT NULL));

-- ---------------------------------------------------------------------------
-- Step 7: Drop FK_Channel_StatusChannel and StatusChannel_ID column
-- ---------------------------------------------------------------------------
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [FK_Channel_StatusChannel];
ALTER TABLE [dbo].[Channel] DROP COLUMN [StatusChannel_ID];

-- ---------------------------------------------------------------------------
-- Step 8: Drop EquipmentStatusChannel table
-- ---------------------------------------------------------------------------
ALTER TABLE [dbo].[EquipmentStatusChannel] DROP CONSTRAINT [FK_EquipmentStatusChannel_Channel];
ALTER TABLE [dbo].[EquipmentStatusChannel] DROP CONSTRAINT [FK_EquipmentStatusChannel_Equipment];
DROP TABLE [dbo].[EquipmentStatusChannel];

-- ---------------------------------------------------------------------------
-- Step 9: Record rollback in SchemaVersion
-- ---------------------------------------------------------------------------
INSERT INTO [dbo].[SchemaVersion] ([Version], [Description], [AppliedAt])
VALUES (
    '2.0.0',
    'Phase C rollback — restored StatusOfMetaDataID/StatusOfEquipmentID on Channel',
    SYSUTCDATETIME()
);
