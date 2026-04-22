-- ============================================================
-- Rollback: v4.0.0 → v3.0.0 — revert SignalInterface redesign
--
-- Assumes no production data on the v4.0.0 tables
-- (drop-and-recreate migration has no backfill path). Recreates
-- the v3.0.0 SignalPort stack empty, along with v3-style views.
-- ============================================================

SET XACT_ABORT ON;
BEGIN TRANSACTION;

-- 1. Drop v4 views
DROP VIEW IF EXISTS [dbo].[vw_ChannelStatus];
DROP VIEW IF EXISTS [dbo].[vw_DeviceStatus];
DROP VIEW IF EXISTS [dbo].[vw_ChannelLocationAtTime];
DROP VIEW IF EXISTS [dbo].[vw_ChannelEquipmentAtTime];
GO

-- 2. Drop ControlLoopPort (v4 shape — Channel_ID)
IF OBJECT_ID('dbo.ControlLoopPort', 'U') IS NOT NULL
BEGIN
    ALTER TABLE [dbo].[ControlLoopPort] DROP CONSTRAINT [FK_ControlLoopPort_ControlLoop];
    ALTER TABLE [dbo].[ControlLoopPort] DROP CONSTRAINT [FK_ControlLoopPort_Channel];
    ALTER TABLE [dbo].[ControlLoopPort] DROP CONSTRAINT [FK_ControlLoopPort_ControlLoopPortRole];
    DROP TABLE [dbo].[ControlLoopPort];
END
GO

-- 3. Drop ChannelPortHistory
DROP INDEX IF EXISTS [UQ_ChannelPortHistory_ActiveRow] ON [dbo].[ChannelPortHistory];
DROP INDEX IF EXISTS [IX_ChannelPortHistory_Port]    ON [dbo].[ChannelPortHistory];
DROP TABLE IF EXISTS [dbo].[ChannelPortHistory];
GO

-- 4. Drop Equipment history tables
DROP INDEX IF EXISTS [UQ_EquipmentLocationHistory_ActiveRow] ON [dbo].[EquipmentLocationHistory];
DROP INDEX IF EXISTS [IX_EquipmentLocationHistory_SamplingPoint] ON [dbo].[EquipmentLocationHistory];
DROP TABLE IF EXISTS [dbo].[EquipmentLocationHistory];

DROP INDEX IF EXISTS [UQ_EquipmentWiringHistory_ActiveRow] ON [dbo].[EquipmentWiringHistory];
DROP INDEX IF EXISTS [IX_EquipmentWiringHistory_Interface] ON [dbo].[EquipmentWiringHistory];
DROP TABLE IF EXISTS [dbo].[EquipmentWiringHistory];
GO

-- 5. Drop new Channel columns + their FKs/indexes
DROP INDEX IF EXISTS [UQ_Channel_SignalStream] ON [dbo].[Channel];
DROP INDEX IF EXISTS [IX_Channel_ParentChannel] ON [dbo].[Channel];
GO

IF OBJECT_ID('dbo.FK_Channel_SignalInterface',     'F') IS NOT NULL ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [FK_Channel_SignalInterface];
IF OBJECT_ID('dbo.FK_Channel_SignalInterfacePort', 'F') IS NOT NULL ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [FK_Channel_SignalInterfacePort];
IF OBJECT_ID('dbo.FK_Channel_ParentChannel',       'F') IS NOT NULL ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [FK_Channel_ParentChannel];
IF OBJECT_ID('dbo.FK_Channel_ChannelRole',         'F') IS NOT NULL ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [FK_Channel_ChannelRole];
IF OBJECT_ID('dbo.DF_Channel_ChannelRole',         'D') IS NOT NULL ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [DF_Channel_ChannelRole];
GO

ALTER TABLE [dbo].[Channel] DROP COLUMN [ChannelRole_ID];
ALTER TABLE [dbo].[Channel] DROP COLUMN [ParentChannel_ID];
ALTER TABLE [dbo].[Channel] DROP COLUMN [SignalInterfacePort_ID];
ALTER TABLE [dbo].[Channel] DROP COLUMN [TagName];
ALTER TABLE [dbo].[Channel] DROP COLUMN [SignalInterface_ID];
GO

-- 6. Drop SignalInterface + Port
DROP INDEX IF EXISTS [UQ_SignalInterfacePort_Interface_PortId] ON [dbo].[SignalInterfacePort];
DROP TABLE IF EXISTS [dbo].[SignalInterfacePort];

DROP INDEX IF EXISTS [UQ_SignalInterface_DAS_Name] ON [dbo].[SignalInterface];
DROP TABLE IF EXISTS [dbo].[SignalInterface];
GO

-- 7. Drop vocab tables
DROP TABLE IF EXISTS [dbo].[SignalInterfacePortKind];
DROP TABLE IF EXISTS [dbo].[SignalInterfaceType];
DROP TABLE IF EXISTS [dbo].[ChannelRole];
GO

-- ============================================================
-- 8. Recreate v3.0.0 SignalPort* tables (empty)
-- ============================================================
CREATE TABLE [dbo].[SignalPortType] (
    [SignalPortType_ID] INT           NOT NULL,
    [Name]              NVARCHAR(50)  NOT NULL,
    [Description]       NVARCHAR(200) NULL,
    CONSTRAINT [PK_SignalPortType] PRIMARY KEY ([SignalPortType_ID]),
    CONSTRAINT [UQ_SignalPortType_Name] UNIQUE ([Name])
);
GO

INSERT INTO [dbo].[SignalPortType] ([SignalPortType_ID], [Name], [Description]) VALUES
    (1, N'Value',  N'Carries a measurement or control value'),
    (2, N'Status', N'Carries a device or measurement status flag');
GO

CREATE TABLE [dbo].[SignalPort] (
    [SignalPort_ID]            INT IDENTITY(1,1) NOT NULL,
    [DataAcquisitionSystem_ID] INT           NOT NULL,
    [Tag]                      NVARCHAR(200) NOT NULL,
    [SignalPortType_ID]        INT           NOT NULL,
    [ParentPort_ID]            INT           NULL,
    [IsActive]                 BIT           NOT NULL CONSTRAINT [DF_SignalPort_IsActive] DEFAULT 1,
    [Description]              NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_SignalPort] PRIMARY KEY ([SignalPort_ID]),
    CONSTRAINT [UQ_SignalPort_DAS_Tag]
        UNIQUE ([DataAcquisitionSystem_ID], [Tag]),
    CONSTRAINT [FK_SignalPort_DAS]
        FOREIGN KEY ([DataAcquisitionSystem_ID])
        REFERENCES [dbo].[DataAcquisitionSystem] ([DataAcquisitionSystem_ID]),
    CONSTRAINT [FK_SignalPort_Type]
        FOREIGN KEY ([SignalPortType_ID])
        REFERENCES [dbo].[SignalPortType] ([SignalPortType_ID]),
    CONSTRAINT [FK_SignalPort_ParentPort]
        FOREIGN KEY ([ParentPort_ID])
        REFERENCES [dbo].[SignalPort] ([SignalPort_ID])
);
GO

CREATE TABLE [dbo].[SignalPortLocationHistory] (
    [SignalPortLocationHistory_ID] INT IDENTITY(1,1) NOT NULL,
    [SignalPort_ID]                INT          NOT NULL,
    [SamplingPoint_ID]             INT          NOT NULL,
    [StartTime]                    DATETIME2(7) NOT NULL,
    [EndTime]                      DATETIME2(7) NULL,
    [Notes]                        NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_SignalPortLocationHistory] PRIMARY KEY ([SignalPortLocationHistory_ID]),
    CONSTRAINT [FK_SignalPortLocationHistory_Port]
        FOREIGN KEY ([SignalPort_ID])
        REFERENCES [dbo].[SignalPort] ([SignalPort_ID]),
    CONSTRAINT [FK_SignalPortLocationHistory_SamplingPoint]
        FOREIGN KEY ([SamplingPoint_ID])
        REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID])
);
GO
CREATE UNIQUE INDEX [UQ_SignalPortLocationHistory_ActiveRow]
    ON [dbo].[SignalPortLocationHistory] ([SignalPort_ID])
    WHERE [EndTime] IS NULL;
GO

CREATE TABLE [dbo].[SignalPortEquipmentHistory] (
    [SignalPortEquipmentHistory_ID] INT IDENTITY(1,1) NOT NULL,
    [SignalPort_ID]                 INT          NOT NULL,
    [Equipment_ID]                  INT          NULL,
    [StartTime]                     DATETIME2(7) NOT NULL,
    [EndTime]                       DATETIME2(7) NULL,
    [Notes]                         NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_SignalPortEquipmentHistory] PRIMARY KEY ([SignalPortEquipmentHistory_ID]),
    CONSTRAINT [FK_SignalPortEquipmentHistory_Port]
        FOREIGN KEY ([SignalPort_ID])
        REFERENCES [dbo].[SignalPort] ([SignalPort_ID]),
    CONSTRAINT [FK_SignalPortEquipmentHistory_Equipment]
        FOREIGN KEY ([Equipment_ID])
        REFERENCES [dbo].[Equipment] ([Equipment_ID])
);
GO
CREATE UNIQUE INDEX [UQ_SignalPortEquipmentHistory_ActiveRow]
    ON [dbo].[SignalPortEquipmentHistory] ([SignalPort_ID])
    WHERE [EndTime] IS NULL;
GO

-- 9. Re-add Channel.SignalPort_ID (empty table, so NOT NULL is safe)
ALTER TABLE [dbo].[Channel]
    ADD [SignalPort_ID] INT NOT NULL
    CONSTRAINT [DF_Channel_SignalPort_Temp] DEFAULT 0;
GO
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [DF_Channel_SignalPort_Temp];
GO

ALTER TABLE [dbo].[Channel]
    ADD CONSTRAINT [FK_Channel_SignalPort]
    FOREIGN KEY ([SignalPort_ID]) REFERENCES [dbo].[SignalPort] ([SignalPort_ID]);
GO

CREATE UNIQUE INDEX [UQ_Channel_SignalStream]
    ON [dbo].[Channel] ([SignalPort_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID])
    WHERE [Parameter_ID] IS NOT NULL;
GO

-- 10. Recreate v3 ControlLoopPort (Channel-style FK removed, SignalPort-based)
CREATE TABLE [dbo].[ControlLoopPort] (
    [ControlLoopPort_ID]     INT IDENTITY(1,1) NOT NULL,
    [ControlLoop_ID]         INT NOT NULL,
    [SignalPort_ID]          INT NOT NULL,
    [ControlLoopPortRole_ID] INT NOT NULL,
    CONSTRAINT [PK_ControlLoopPort] PRIMARY KEY ([ControlLoopPort_ID]),
    CONSTRAINT [UQ_ControlLoopPort_LoopPort] UNIQUE ([ControlLoop_ID], [SignalPort_ID]),
    CONSTRAINT [FK_ControlLoopPort_Loop]
        FOREIGN KEY ([ControlLoop_ID]) REFERENCES [dbo].[ControlLoop] ([ControlLoop_ID]),
    CONSTRAINT [FK_ControlLoopPort_Port]
        FOREIGN KEY ([SignalPort_ID]) REFERENCES [dbo].[SignalPort] ([SignalPort_ID]),
    CONSTRAINT [FK_ControlLoopPort_Role]
        FOREIGN KEY ([ControlLoopPortRole_ID]) REFERENCES [dbo].[ControlLoopPortRole] ([ControlLoopPortRole_ID])
);
GO

-- 11. Recreate v3 views
CREATE OR ALTER VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    valueC.[Channel_ID]         AS MeasurementChannelID,
    e.[Equipment_ID]            AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    p.[Parameter]               AS MeasurementParameter,
    o.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]               o        ON o.[Observation_ID]      = v.[Observation_ID]
JOIN [dbo].[Channel]                   statusC  ON statusC.[Channel_ID]    = o.[Channel_ID]
JOIN [dbo].[SignalPort]                statusP  ON statusP.[SignalPort_ID] = statusC.[SignalPort_ID]
JOIN [dbo].[SignalPortType]            spt      ON spt.[SignalPortType_ID] = statusP.[SignalPortType_ID]
JOIN [dbo].[SignalPort]                valueP   ON valueP.[SignalPort_ID]  = statusP.[ParentPort_ID]
JOIN [dbo].[Channel]                   valueC   ON valueC.[SignalPort_ID]  = valueP.[SignalPort_ID]
JOIN [dbo].[Parameter]                 p        ON p.[Parameter_ID]        = valueC.[Parameter_ID]
LEFT JOIN [dbo].[SignalPortEquipmentHistory] peh ON peh.[SignalPort_ID]    = valueP.[SignalPort_ID]
                                                 AND peh.[EndTime] IS NULL
LEFT JOIN [dbo].[Equipment]            e        ON e.[Equipment_ID]        = peh.[Equipment_ID]
WHERE spt.[Name] = N'Status'
  AND statusP.[ParentPort_ID] IS NOT NULL;
GO

CREATE OR ALTER VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    e.[Equipment_ID]            AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    o.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]                o       ON o.[Observation_ID]      = v.[Observation_ID]
JOIN [dbo].[Channel]                    statusC ON statusC.[Channel_ID]    = o.[Channel_ID]
JOIN [dbo].[SignalPort]                 statusP ON statusP.[SignalPort_ID] = statusC.[SignalPort_ID]
JOIN [dbo].[SignalPortType]             spt     ON spt.[SignalPortType_ID] = statusP.[SignalPortType_ID]
JOIN [dbo].[SignalPortEquipmentHistory] peh     ON peh.[SignalPort_ID]     = statusP.[SignalPort_ID]
                                                AND peh.[EndTime] IS NULL
JOIN [dbo].[Equipment]                  e       ON e.[Equipment_ID]        = peh.[Equipment_ID]
WHERE spt.[Name] = N'Status';
GO

-- 12. Record rollback
DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'4.0.0';
INSERT INTO [dbo].[SchemaVersion] ([Version], [Description], [MigrationScript])
VALUES (N'3.0.0', N'Rollback from v4.0.0 — SignalInterface redesign reverted', N'v4.0.0_signal_interface_rollback.sql');
GO

COMMIT TRANSACTION;
GO

PRINT 'Rollback to v3.0.0 completed successfully.';
