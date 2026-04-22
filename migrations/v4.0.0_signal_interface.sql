-- ============================================================
-- Migration: v3.0.0 → v4.0.0 — SignalInterface redesign (Issue #24)
--
-- BREAKING: drops the SignalPort* stack entirely. Channel keeps its name
-- but is re-anchored to (SignalInterface_ID, TagName, optional
-- SignalInterfacePort_ID). Equipment wiring and location move to
-- dedicated Equipment-anchored history tables.
--
-- Drops: SignalPort, SignalPortType, SignalPortEquipmentHistory,
--        SignalPortLocationHistory.
-- Adds:  SignalInterface, SignalInterfaceType, SignalInterfacePort,
--        SignalInterfacePortKind, ChannelRole, EquipmentWiringHistory,
--        EquipmentLocationHistory, ChannelPortHistory.
-- Alters: Channel (drop SignalPort_ID; add SignalInterface_ID, TagName,
--         SignalInterfacePort_ID, ParentChannel_ID, ChannelRole_ID).
-- Recreates: ControlLoopPort (FK → Channel), vw_ChannelStatus,
--            vw_DeviceStatus. Adds vw_ChannelEquipmentAtTime and
--            vw_ChannelLocationAtTime.
--
-- This migration is drop-and-recreate: assumes no production data at
-- the Channel/SignalPort level (fresh-volume boot). No data preservation.
-- ============================================================

SET XACT_ABORT ON;
BEGIN TRANSACTION;

-- ============================================================
-- 1. Drop v3 views that depend on SignalPort
-- ============================================================
DROP VIEW IF EXISTS [dbo].[vw_ChannelStatus];
DROP VIEW IF EXISTS [dbo].[vw_DeviceStatus];
GO

-- ============================================================
-- 2. Drop ControlLoopPort (FK -> SignalPort). Rebuilt in step 10.
-- ============================================================
IF OBJECT_ID('dbo.ControlLoopPort', 'U') IS NOT NULL
BEGIN
    ALTER TABLE [dbo].[ControlLoopPort] DROP CONSTRAINT [FK_ControlLoopPort_Loop];
    ALTER TABLE [dbo].[ControlLoopPort] DROP CONSTRAINT [FK_ControlLoopPort_Port];
    ALTER TABLE [dbo].[ControlLoopPort] DROP CONSTRAINT [FK_ControlLoopPort_Role];
    DROP TABLE [dbo].[ControlLoopPort];
END
GO

-- ============================================================
-- 3. Drop Channel.SignalPort_ID (and its FK / UQ index)
-- ============================================================
DROP INDEX IF EXISTS [UQ_Channel_SignalStream] ON [dbo].[Channel];
GO

-- Dynamic drop of FK on Channel.SignalPort_ID (name unknown-safe).
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT @sql = @sql + N'ALTER TABLE [dbo].[Channel] DROP CONSTRAINT ['
              + fk.[name] + N'];' + CHAR(10)
FROM   sys.foreign_keys        fk
JOIN   sys.foreign_key_columns fkc
    ON fk.[object_id] = fkc.[constraint_object_id]
WHERE  fk.[parent_object_id] = OBJECT_ID('dbo.Channel')
  AND  COL_NAME(fkc.[parent_object_id], fkc.[parent_column_id]) = N'SignalPort_ID';
IF LEN(@sql) > 0
    EXEC sp_executesql @sql;
GO

ALTER TABLE [dbo].[Channel] DROP COLUMN [SignalPort_ID];
GO

-- ============================================================
-- 4. Drop SignalPort* history + base tables + type vocab
-- ============================================================
DROP INDEX IF EXISTS [UQ_SignalPortEquipmentHistory_ActiveRow] ON [dbo].[SignalPortEquipmentHistory];
DROP INDEX IF EXISTS [UQ_SignalPortLocationHistory_ActiveRow] ON [dbo].[SignalPortLocationHistory];
GO

DROP TABLE IF EXISTS [dbo].[SignalPortEquipmentHistory];
DROP TABLE IF EXISTS [dbo].[SignalPortLocationHistory];
DROP TABLE IF EXISTS [dbo].[SignalPort];
DROP TABLE IF EXISTS [dbo].[SignalPortType];
GO

-- ============================================================
-- 5. Create vocab tables: ChannelRole, SignalInterfaceType,
--    SignalInterfacePortKind
-- ============================================================
CREATE TABLE [dbo].[ChannelRole] (
    [ChannelRole_ID] INT NOT NULL,
    [Name]           NVARCHAR(50) NOT NULL,
    [Description]    NVARCHAR(200),
    CONSTRAINT [PK_ChannelRole] PRIMARY KEY ([ChannelRole_ID]),
    CONSTRAINT [UQ_ChannelRole_Name] UNIQUE ([Name])
);
GO

INSERT INTO [dbo].[ChannelRole] ([ChannelRole_ID], [Name], [Description]) VALUES
    (1, N'Value',       N'Primary measurement or output value'),
    (2, N'Status',      N'Device or measurement status flag'),
    (3, N'Alarm',       N'Alarm or alert indicator'),
    (4, N'Uncertainty', N'Measurement uncertainty estimate');
GO

CREATE TABLE [dbo].[SignalInterfaceType] (
    [SignalInterfaceType_ID] INT NOT NULL,
    [Name]                   NVARCHAR(50)  NOT NULL,
    [Description]            NVARCHAR(300),
    CONSTRAINT [PK_SignalInterfaceType] PRIMARY KEY ([SignalInterfaceType_ID]),
    CONSTRAINT [UQ_SignalInterfaceType_Name] UNIQUE ([Name])
);
GO

INSERT INTO [dbo].[SignalInterfaceType] ([SignalInterfaceType_ID], [Name], [Description]) VALUES
    (1, N'PLC',           N'Programmable Logic Controller exposing tags (e.g. Logix5000)'),
    (2, N'SCADA',         N'SCADA / HMI system publishing tag strings (e.g. Wonderware, Ignition)'),
    (3, N'Basestation',   N'Vendor basestation or sensor hub relaying one or more probes'),
    (4, N'IQSensorBus',   N'Hach/WTW IQ Sensor Net or similar multi-probe sensor bus'),
    (5, N'DirectConnect', N'Single-sensor direct serial/analog link — no upstream controller'),
    (6, N'Multiplexer',   N'Physical multiplexer (e.g. TresCON) where one port relays many streams'),
    (7, N'GatewayOther',  N'Other gateway/bridge device not covered by the categories above');
GO

CREATE TABLE [dbo].[SignalInterfacePortKind] (
    [SignalInterfacePortKind_ID] INT NOT NULL,
    [Name]                       NVARCHAR(50)  NOT NULL,
    [Description]                NVARCHAR(200),
    CONSTRAINT [PK_SignalInterfacePortKind] PRIMARY KEY ([SignalInterfacePortKind_ID]),
    CONSTRAINT [UQ_SignalInterfacePortKind_Name] UNIQUE ([Name])
);
GO

INSERT INTO [dbo].[SignalInterfacePortKind] ([SignalInterfacePortKind_ID], [Name], [Description]) VALUES
    (1, N'AnalogIn',   N'Analog input (4-20 mA, 0-10 V, etc.)'),
    (2, N'AnalogOut',  N'Analog output to a field device'),
    (3, N'DigitalIn',  N'Discrete digital input'),
    (4, N'DigitalOut', N'Discrete digital output'),
    (5, N'Serial',     N'Serial fieldbus link (RS-232/485, Modbus, Profibus)'),
    (6, N'Network',    N'Ethernet/IP or other network-based port'),
    (7, N'Virtual',    N'Logical port with no dedicated physical terminal (e.g. multiplexed sub-channel)'),
    (8, N'Unknown',    N'Physical kind not yet traced');
GO

-- ============================================================
-- 6. Create SignalInterface + SignalInterfacePort
-- ============================================================
CREATE TABLE [dbo].[SignalInterface] (
    [SignalInterface_ID]       INT IDENTITY(1,1) NOT NULL,
    [DataAcquisitionSystem_ID] INT NOT NULL,
    [SignalInterfaceType_ID]   INT NOT NULL,
    [Name]                     NVARCHAR(200) NOT NULL,
    [Make]                     NVARCHAR(100),
    [Model]                    NVARCHAR(100),
    [SerialNumber]             NVARCHAR(100),
    [Description]              NVARCHAR(MAX),
    [IsActive]                 BIT NOT NULL CONSTRAINT [DF_SignalInterface_IsActive] DEFAULT 1,
    CONSTRAINT [PK_SignalInterface] PRIMARY KEY ([SignalInterface_ID]),
    CONSTRAINT [FK_SignalInterface_DataAcquisitionSystem]
        FOREIGN KEY ([DataAcquisitionSystem_ID]) REFERENCES [dbo].[DataAcquisitionSystem] ([DataAcquisitionSystem_ID]),
    CONSTRAINT [FK_SignalInterface_SignalInterfaceType]
        FOREIGN KEY ([SignalInterfaceType_ID]) REFERENCES [dbo].[SignalInterfaceType] ([SignalInterfaceType_ID])
);
GO

CREATE UNIQUE INDEX [UQ_SignalInterface_DAS_Name]
    ON [dbo].[SignalInterface] ([DataAcquisitionSystem_ID], [Name]);
GO

CREATE TABLE [dbo].[SignalInterfacePort] (
    [SignalInterfacePort_ID]     INT IDENTITY(1,1) NOT NULL,
    [SignalInterface_ID]         INT NOT NULL,
    [PortIdentifier]             NVARCHAR(100) NOT NULL,
    [SignalInterfacePortKind_ID] INT NOT NULL,
    [Description]                NVARCHAR(MAX),
    [IsActive]                   BIT NOT NULL CONSTRAINT [DF_SignalInterfacePort_IsActive] DEFAULT 1,
    CONSTRAINT [PK_SignalInterfacePort] PRIMARY KEY ([SignalInterfacePort_ID]),
    CONSTRAINT [FK_SignalInterfacePort_SignalInterface]
        FOREIGN KEY ([SignalInterface_ID]) REFERENCES [dbo].[SignalInterface] ([SignalInterface_ID]),
    CONSTRAINT [FK_SignalInterfacePort_SignalInterfacePortKind]
        FOREIGN KEY ([SignalInterfacePortKind_ID]) REFERENCES [dbo].[SignalInterfacePortKind] ([SignalInterfacePortKind_ID])
);
GO

CREATE UNIQUE INDEX [UQ_SignalInterfacePort_Interface_PortId]
    ON [dbo].[SignalInterfacePort] ([SignalInterface_ID], [PortIdentifier]);
GO

-- ============================================================
-- 7. Add new Channel columns and rebuild unique stream index
-- ============================================================
-- Safe fresh-volume pattern: NOT NULL + temp DEFAULT, then drop default.
ALTER TABLE [dbo].[Channel]
    ADD [SignalInterface_ID] INT NOT NULL
        CONSTRAINT [DF_Channel_SignalInterface_Temp] DEFAULT 0;
GO
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [DF_Channel_SignalInterface_Temp];
GO

ALTER TABLE [dbo].[Channel]
    ADD [TagName] NVARCHAR(200) NOT NULL
        CONSTRAINT [DF_Channel_TagName_Temp] DEFAULT N'';
GO
ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [DF_Channel_TagName_Temp];
GO

ALTER TABLE [dbo].[Channel]
    ADD [SignalInterfacePort_ID] INT NULL,
        [ParentChannel_ID]        INT NULL,
        [ChannelRole_ID]          INT NOT NULL CONSTRAINT [DF_Channel_ChannelRole] DEFAULT 1;
GO

ALTER TABLE [dbo].[Channel]
    ADD CONSTRAINT [FK_Channel_SignalInterface]
        FOREIGN KEY ([SignalInterface_ID]) REFERENCES [dbo].[SignalInterface] ([SignalInterface_ID]);
ALTER TABLE [dbo].[Channel]
    ADD CONSTRAINT [FK_Channel_SignalInterfacePort]
        FOREIGN KEY ([SignalInterfacePort_ID]) REFERENCES [dbo].[SignalInterfacePort] ([SignalInterfacePort_ID]);
ALTER TABLE [dbo].[Channel]
    ADD CONSTRAINT [FK_Channel_ParentChannel]
        FOREIGN KEY ([ParentChannel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[Channel]
    ADD CONSTRAINT [FK_Channel_ChannelRole]
        FOREIGN KEY ([ChannelRole_ID]) REFERENCES [dbo].[ChannelRole] ([ChannelRole_ID]);
GO

CREATE UNIQUE INDEX [UQ_Channel_SignalStream]
    ON [dbo].[Channel] ([SignalInterface_ID], [TagName], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID]);
CREATE INDEX [IX_Channel_ParentChannel]
    ON [dbo].[Channel] ([ParentChannel_ID]);
GO

-- ============================================================
-- 8. Equipment wiring + location history tables
-- ============================================================
CREATE TABLE [dbo].[EquipmentWiringHistory] (
    [EquipmentWiringHistory_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID]              INT          NOT NULL,
    [SignalInterface_ID]        INT          NOT NULL,
    [SignalInterfacePort_ID]    INT          NULL,
    [ValidFrom]                 DATETIME2(7) NOT NULL,
    [ValidTo]                   DATETIME2(7) NULL,
    [Note]                      NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_EquipmentWiringHistory] PRIMARY KEY ([EquipmentWiringHistory_ID]),
    CONSTRAINT [FK_EquipmentWiringHistory_Equipment]
        FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]),
    CONSTRAINT [FK_EquipmentWiringHistory_SignalInterface]
        FOREIGN KEY ([SignalInterface_ID]) REFERENCES [dbo].[SignalInterface] ([SignalInterface_ID]),
    CONSTRAINT [FK_EquipmentWiringHistory_SignalInterfacePort]
        FOREIGN KEY ([SignalInterfacePort_ID]) REFERENCES [dbo].[SignalInterfacePort] ([SignalInterfacePort_ID])
);
GO

CREATE UNIQUE INDEX [UQ_EquipmentWiringHistory_ActiveRow]
    ON [dbo].[EquipmentWiringHistory] ([Equipment_ID])
    WHERE [ValidTo] IS NULL;
CREATE INDEX [IX_EquipmentWiringHistory_Interface]
    ON [dbo].[EquipmentWiringHistory] ([SignalInterface_ID], [ValidFrom]);
GO

CREATE TABLE [dbo].[EquipmentLocationHistory] (
    [EquipmentLocationHistory_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID]                INT          NOT NULL,
    [SamplingPoint_ID]            INT          NOT NULL,
    [ValidFrom]                   DATETIME2(7) NOT NULL,
    [ValidTo]                     DATETIME2(7) NULL,
    [Campaign_ID]                 INT          NULL,
    [Notes]                       NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_EquipmentLocationHistory] PRIMARY KEY ([EquipmentLocationHistory_ID]),
    CONSTRAINT [FK_EquipmentLocationHistory_Equipment]
        FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]),
    CONSTRAINT [FK_EquipmentLocationHistory_SamplingPoint]
        FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]),
    CONSTRAINT [FK_EquipmentLocationHistory_Campaign]
        FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID])
);
GO

CREATE UNIQUE INDEX [UQ_EquipmentLocationHistory_ActiveRow]
    ON [dbo].[EquipmentLocationHistory] ([Equipment_ID])
    WHERE [ValidTo] IS NULL;
CREATE INDEX [IX_EquipmentLocationHistory_SamplingPoint]
    ON [dbo].[EquipmentLocationHistory] ([SamplingPoint_ID], [ValidFrom]);
GO

-- ============================================================
-- 9. ChannelPortHistory (for mux gating and retroactive port backfill)
-- ============================================================
CREATE TABLE [dbo].[ChannelPortHistory] (
    [ChannelPortHistory_ID]  INT IDENTITY(1,1) NOT NULL,
    [Channel_ID]             INT          NOT NULL,
    [SignalInterfacePort_ID] INT          NULL,
    [ValidFrom]              DATETIME2(7) NOT NULL,
    [ValidTo]                DATETIME2(7) NULL,
    [GatingNote]             NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_ChannelPortHistory] PRIMARY KEY ([ChannelPortHistory_ID]),
    CONSTRAINT [FK_ChannelPortHistory_Channel]
        FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]),
    CONSTRAINT [FK_ChannelPortHistory_SignalInterfacePort]
        FOREIGN KEY ([SignalInterfacePort_ID]) REFERENCES [dbo].[SignalInterfacePort] ([SignalInterfacePort_ID])
);
GO

CREATE UNIQUE INDEX [UQ_ChannelPortHistory_ActiveRow]
    ON [dbo].[ChannelPortHistory] ([Channel_ID])
    WHERE [ValidTo] IS NULL;
CREATE INDEX [IX_ChannelPortHistory_Port]
    ON [dbo].[ChannelPortHistory] ([SignalInterfacePort_ID], [ValidFrom]);
GO

-- ============================================================
-- 10. Rebuild ControlLoopPort keyed on Channel
-- ============================================================
CREATE TABLE [dbo].[ControlLoopPort] (
    [ControlLoopPort_ID]     INT IDENTITY(1,1) NOT NULL,
    [ControlLoop_ID]         INT NOT NULL,
    [Channel_ID]             INT NOT NULL,
    [ControlLoopPortRole_ID] INT NOT NULL,
    CONSTRAINT [PK_ControlLoopPort] PRIMARY KEY ([ControlLoopPort_ID]),
    CONSTRAINT [FK_ControlLoopPort_ControlLoop]
        FOREIGN KEY ([ControlLoop_ID]) REFERENCES [dbo].[ControlLoop] ([ControlLoop_ID]),
    CONSTRAINT [FK_ControlLoopPort_Channel]
        FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]),
    CONSTRAINT [FK_ControlLoopPort_ControlLoopPortRole]
        FOREIGN KEY ([ControlLoopPortRole_ID]) REFERENCES [dbo].[ControlLoopPortRole] ([ControlLoopPortRole_ID])
);
GO

CREATE UNIQUE INDEX [UQ_ControlLoopPort_LoopChannel]
    ON [dbo].[ControlLoopPort] ([ControlLoop_ID], [Channel_ID]);
GO

-- ============================================================
-- 11. Views
-- ============================================================
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

CREATE OR ALTER VIEW [dbo].[vw_ChannelLocationAtTime] AS
SELECT
    cea.ObservationID,
    cea.ChannelID,
    cea.Timestamp,
    cea.EquipmentID,
    elh.[SamplingPoint_ID]   AS SamplingPointID,
    sp.[SamplingPoint]       AS SamplingPointName
FROM [dbo].[vw_ChannelEquipmentAtTime] cea
LEFT JOIN [dbo].[EquipmentLocationHistory] elh ON elh.[Equipment_ID] = cea.EquipmentID
                                              AND elh.[ValidFrom]   <= cea.Timestamp
                                              AND (elh.[ValidTo] IS NULL OR elh.[ValidTo] > cea.Timestamp)
LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID];
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
JOIN [dbo].[Observation]   o       ON o.[Observation_ID]    = v.[Observation_ID]
JOIN [dbo].[Channel]       statusC ON statusC.[Channel_ID]  = o.[Channel_ID]
JOIN [dbo].[ChannelRole]   role    ON role.[ChannelRole_ID] = statusC.[ChannelRole_ID]
JOIN [dbo].[Channel]       valueC  ON valueC.[Channel_ID]   = statusC.[ParentChannel_ID]
JOIN [dbo].[Parameter]     p       ON p.[Parameter_ID]      = valueC.[Parameter_ID]
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

CREATE OR ALTER VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]       AS StatusChannelID,
    e.[Equipment_ID]           AS EquipmentID,
    e.[Identifier]             AS EquipmentName,
    o.[Timestamp],
    CAST(v.[Value] AS INT)     AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]  o       ON o.[Observation_ID]    = v.[Observation_ID]
JOIN [dbo].[Channel]      statusC ON statusC.[Channel_ID]  = o.[Channel_ID]
JOIN [dbo].[ChannelRole]  role    ON role.[ChannelRole_ID] = statusC.[ChannelRole_ID]
JOIN [dbo].[Channel]      valueC  ON valueC.[Channel_ID]   = statusC.[ParentChannel_ID]
JOIN [dbo].[EquipmentWiringHistory] ewh
       ON ewh.[SignalInterface_ID] = valueC.[SignalInterface_ID]
      AND (
           ewh.[SignalInterfacePort_ID] = valueC.[SignalInterfacePort_ID]
           OR valueC.[SignalInterfacePort_ID] IS NULL
          )
      AND ewh.[ValidTo] IS NULL
JOIN [dbo].[Equipment]    e       ON e.[Equipment_ID]      = ewh.[Equipment_ID]
WHERE role.[Name] = N'Status';
GO

-- ============================================================
-- 12. Record schema version
-- ============================================================
INSERT INTO [dbo].[SchemaVersion] ([Version], [Description], [MigrationScript])
VALUES (
    N'4.0.0',
    N'v4.0.0 — SignalInterface redesign (Issue #24): drops SignalPort* stack, introduces SignalInterface/Port, Equipment wiring + location history, Channel.ParentChannel + ChannelRole, ControlLoopPort→Channel.',
    N'v4.0.0_signal_interface.sql'
);
GO

COMMIT TRANSACTION;
GO

PRINT 'Migration to v4.0.0 completed successfully.';
