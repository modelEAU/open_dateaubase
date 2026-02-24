-- =============================================================================
-- Phase C — Status System Cleanup (v2.0.0 → v2.1.0)
-- =============================================================================
-- Goal: Replace the v1.8.0 self-referential hack (StatusOfMetaDataID /
--       StatusOfEquipmentID on Channel) with clean FKs.
--
--  StatusOfMetaDataID → Channel.StatusChannel_ID (nullable FK → Channel)
--  StatusOfEquipmentID → EquipmentStatusChannel table (Equipment_ID PK → Equipment,
--                          StatusChannel_ID → Channel)
--
-- Order of operations
--  1. Add Channel.StatusChannel_ID column + FK
--  2. Create EquipmentStatusChannel table
--  3. Migrate data: StatusOfMetaDataID  → StatusChannel_ID
--  4. Migrate data: StatusOfEquipmentID → EquipmentStatusChannel
--  5. Drop check constraint CK_MetaData_StatusTarget
--  6. Drop FK on StatusOfMetaDataID (dynamic — constraint name not guaranteed)
--  7. Drop FK on StatusOfEquipmentID (dynamic — may share name FK_MetaData_Equipment)
--  8. Drop columns StatusOfMetaDataID, StatusOfEquipmentID
--  9. Rebuild vw_ChannelStatus and vw_DeviceStatus
-- 10. Insert SchemaVersion row
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Step 1: Add StatusChannel_ID to Channel
-- ---------------------------------------------------------------------------
ALTER TABLE [dbo].[Channel]
    ADD [StatusChannel_ID] INT NULL;

ALTER TABLE [dbo].[Channel]
    ADD CONSTRAINT [FK_Channel_StatusChannel]
        FOREIGN KEY ([StatusChannel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);

-- ---------------------------------------------------------------------------
-- Step 2: Create EquipmentStatusChannel table
-- ---------------------------------------------------------------------------
CREATE TABLE [dbo].[EquipmentStatusChannel] (
    [Equipment_ID]     INT NOT NULL,
    [StatusChannel_ID] INT NOT NULL,
    CONSTRAINT [PK_EquipmentStatusChannel] PRIMARY KEY ([Equipment_ID]),
    CONSTRAINT [FK_EquipmentStatusChannel_Equipment]
        FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]),
    CONSTRAINT [FK_EquipmentStatusChannel_Channel]
        FOREIGN KEY ([StatusChannel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID])
);

-- ---------------------------------------------------------------------------
-- Step 3: Migrate channel-level status links
-- ---------------------------------------------------------------------------
UPDATE [dbo].[Channel]
SET    [StatusChannel_ID] = [StatusOfMetaDataID]
WHERE  [StatusOfMetaDataID] IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Step 4: Migrate equipment-level status links
-- ---------------------------------------------------------------------------
INSERT INTO [dbo].[EquipmentStatusChannel] ([Equipment_ID], [StatusChannel_ID])
SELECT DISTINCT [StatusOfEquipmentID], [Channel_ID]
FROM   [dbo].[Channel]
WHERE  [StatusOfEquipmentID] IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Step 5: Drop check constraint (name is known from v1.x baseline)
-- ---------------------------------------------------------------------------
IF EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE  parent_object_id = OBJECT_ID('dbo.Channel')
    AND    name = 'CK_MetaData_StatusTarget'
)
    ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [CK_MetaData_StatusTarget];

-- ---------------------------------------------------------------------------
-- Step 6: Drop FK on StatusOfMetaDataID (discover name dynamically)
-- ---------------------------------------------------------------------------
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT @sql = @sql + N'ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [' + fk.[name] + N'];'
FROM   sys.foreign_keys                 fk
JOIN   sys.foreign_key_columns          fkc ON fk.[object_id] = fkc.[constraint_object_id]
WHERE  fk.[parent_object_id] = OBJECT_ID('dbo.Channel')
  AND  COL_NAME(fkc.[parent_object_id], fkc.[parent_column_id]) = 'StatusOfMetaDataID';

IF LEN(@sql) > 0
    EXEC sp_executesql @sql;

-- ---------------------------------------------------------------------------
-- Step 7: Drop FK on StatusOfEquipmentID (discover name dynamically)
-- ---------------------------------------------------------------------------
SET @sql = N'';
SELECT @sql = @sql + N'ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [' + fk.[name] + N'];'
FROM   sys.foreign_keys                 fk
JOIN   sys.foreign_key_columns          fkc ON fk.[object_id] = fkc.[constraint_object_id]
WHERE  fk.[parent_object_id] = OBJECT_ID('dbo.Channel')
  AND  COL_NAME(fkc.[parent_object_id], fkc.[parent_column_id]) = 'StatusOfEquipmentID';

IF LEN(@sql) > 0
    EXEC sp_executesql @sql;

-- ---------------------------------------------------------------------------
-- Step 8: Drop old columns
-- ---------------------------------------------------------------------------
ALTER TABLE [dbo].[Channel] DROP COLUMN [StatusOfMetaDataID];
ALTER TABLE [dbo].[Channel] DROP COLUMN [StatusOfEquipmentID];

-- ---------------------------------------------------------------------------
-- Step 9: Rebuild views
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS [dbo].[vw_ChannelStatus];
GO

CREATE VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Channel_ID]          AS StatusChannelID,
    statusC.[StatusChannel_ID]    AS MeasurementChannelID,
    measC.[Equipment_ID]          AS EquipmentID,
    e.[identifier]                AS EquipmentName,
    p.[Parameter]                 AS MeasurementParameter,
    v.[Timestamp],
    CAST(v.[Value] AS INT)        AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]               statusC ON statusC.[Channel_ID]      = v.[Channel_ID]
JOIN [dbo].[Channel]               measC   ON measC.[Channel_ID]        = statusC.[StatusChannel_ID]
JOIN [dbo].[Parameter]             p       ON p.[Parameter_ID]          = measC.[Parameter_ID]
JOIN [dbo].[Equipment]             e       ON e.[Equipment_ID]          = measC.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc      ON sc.[StatusCodeID]         = CAST(v.[Value] AS INT)
WHERE statusC.[StatusChannel_ID] IS NOT NULL;
GO

DROP VIEW IF EXISTS [dbo].[vw_DeviceStatus];
GO

CREATE VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]          AS StatusChannelID,
    esc.[Equipment_ID]            AS EquipmentID,
    e.[identifier]                AS EquipmentName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)        AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]                 statusC ON statusC.[Channel_ID]   = v.[Channel_ID]
JOIN [dbo].[EquipmentStatusChannel]  esc     ON esc.[StatusChannel_ID] = statusC.[Channel_ID]
JOIN [dbo].[Equipment]               e       ON e.[Equipment_ID]       = esc.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode]   sc      ON sc.[StatusCodeID]      = CAST(v.[Value] AS INT);
GO

-- ---------------------------------------------------------------------------
-- Step 10: Record schema version
-- ---------------------------------------------------------------------------
INSERT INTO [dbo].[SchemaVersion] ([Version], [Description], [AppliedAt])
VALUES (
    '2.1.0',
    'Phase C — Status system cleanup: StatusChannel_ID + EquipmentStatusChannel table',
    SYSUTCDATETIME()
);
