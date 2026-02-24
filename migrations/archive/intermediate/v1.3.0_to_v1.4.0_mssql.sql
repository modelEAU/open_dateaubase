-- Migration: v1.3.0 -> v1.4.0
-- Platform: mssql
-- Generated: 2026-02-18
-- Rollback: v1.3.0_to_v1.4.0_mssql_rollback.sql
-- Breaking changes: NONE
--
-- Phase 2c: Sensor Lifecycle Tracking
--   Task 2c.1 — Create EquipmentEventType and EquipmentEvent tables
--   Task 2c.2 — Create EquipmentEventMetaData junction table
--   Task 2c.3 — Create EquipmentInstallation table; add ValidFrom, ValidTo, CreatedByCampaign_ID to SamplingPoints

-- ============================================================
-- Task 2c.1: EquipmentEventType lookup table
-- ============================================================

CREATE TABLE [dbo].[EquipmentEventType] (
    [EquipmentEventType_ID] INT IDENTITY(1,1) NOT NULL,
    [EquipmentEventType_Name] NVARCHAR(100) NOT NULL,
    CONSTRAINT [PK_EquipmentEventType] PRIMARY KEY ([EquipmentEventType_ID])
);
GO

INSERT INTO [dbo].[EquipmentEventType] ([EquipmentEventType_Name])
VALUES
    ('Calibration'),
    ('Validation'),
    ('Maintenance'),
    ('Installation'),
    ('Removal'),
    ('Firmware Update'),
    ('Failure'),
    ('Repair');
GO

-- ============================================================
-- Task 2c.1: EquipmentEvent table
-- ============================================================

CREATE TABLE [dbo].[EquipmentEvent] (
    [EquipmentEvent_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID] INT NOT NULL,
    [EquipmentEventType_ID] INT NOT NULL,
    [EventDateTimeStart] DATETIME2(7) NOT NULL,
    [EventDateTimeEnd] DATETIME2(7) NULL,
    [PerformedByPerson_ID] INT NULL,
    [Campaign_ID] INT NULL,
    [Notes] NVARCHAR(1000) NULL,
    CONSTRAINT [PK_EquipmentEvent] PRIMARY KEY ([EquipmentEvent_ID]),
    CONSTRAINT [FK_EquipmentEvent_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]),
    CONSTRAINT [FK_EquipmentEvent_EventType] FOREIGN KEY ([EquipmentEventType_ID]) REFERENCES [dbo].[EquipmentEventType] ([EquipmentEventType_ID]),
    CONSTRAINT [FK_EquipmentEvent_Person] FOREIGN KEY ([PerformedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]),
    CONSTRAINT [FK_EquipmentEvent_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID])
);
GO

CREATE INDEX [IX_EquipmentEvent_Equipment_Start]
    ON [dbo].[EquipmentEvent] ([Equipment_ID], [EventDateTimeStart]);
GO

-- ============================================================
-- Task 2c.2: EquipmentEventMetaData junction table
-- ============================================================

CREATE TABLE [dbo].[EquipmentEventMetaData] (
    [EquipmentEvent_ID] INT NOT NULL,
    [Metadata_ID] INT NOT NULL,
    [WindowStart] DATETIME2(7) NULL,    -- optional: narrow sensor readings to this window
    [WindowEnd] DATETIME2(7) NULL,
    CONSTRAINT [PK_EquipmentEventMetaData] PRIMARY KEY ([EquipmentEvent_ID], [Metadata_ID]),
    CONSTRAINT [FK_EquipmentEventMetaData_Event] FOREIGN KEY ([EquipmentEvent_ID]) REFERENCES [dbo].[EquipmentEvent] ([EquipmentEvent_ID]),
    CONSTRAINT [FK_EquipmentEventMetaData_MetaData] FOREIGN KEY ([Metadata_ID]) REFERENCES [dbo].[MetaData] ([Metadata_ID])
);
GO

-- ============================================================
-- Task 2c.3: EquipmentInstallation table
-- ============================================================

CREATE TABLE [dbo].[EquipmentInstallation] (
    [Installation_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID] INT NOT NULL,
    [Sampling_point_ID] INT NOT NULL,
    [InstalledDate] DATETIME2(7) NOT NULL,
    [RemovedDate] DATETIME2(7) NULL,
    [Campaign_ID] INT NULL,
    [Notes] NVARCHAR(500) NULL,
    CONSTRAINT [PK_EquipmentInstallation] PRIMARY KEY ([Installation_ID]),
    CONSTRAINT [FK_EquipmentInstallation_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]),
    CONSTRAINT [FK_EquipmentInstallation_SamplingPoints] FOREIGN KEY ([Sampling_point_ID]) REFERENCES [dbo].[SamplingPoints] ([Sampling_point_ID]),
    CONSTRAINT [FK_EquipmentInstallation_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID])
);
GO

CREATE INDEX [IX_EquipmentInstallation_Equipment]
    ON [dbo].[EquipmentInstallation] ([Equipment_ID], [InstalledDate]);
GO

CREATE INDEX [IX_EquipmentInstallation_SamplingPoint]
    ON [dbo].[EquipmentInstallation] ([Sampling_point_ID], [InstalledDate]);
GO

-- ============================================================
-- Task 2c.3: Temporal columns on SamplingPoints
-- ============================================================

ALTER TABLE [dbo].[SamplingPoints]
    ADD [ValidFrom] DATETIME2(7) NULL;
GO
ALTER TABLE [dbo].[SamplingPoints]
    ADD [ValidTo] DATETIME2(7) NULL;
GO
ALTER TABLE [dbo].[SamplingPoints]
    ADD [CreatedByCampaign_ID] INT NULL;
GO
ALTER TABLE [dbo].[SamplingPoints]
    ADD CONSTRAINT [FK_SamplingPoints_Campaign]
    FOREIGN KEY ([CreatedByCampaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
GO

-- ============================================================
-- Update SchemaVersion
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.4.0',
    GETUTCDATE(),
    'Phase 2c: Sensor Lifecycle Tracking — EquipmentEventType, EquipmentEvent, EquipmentEventMetaData, EquipmentInstallation; temporal columns on SamplingPoints',
    'v1.3.0_to_v1.4.0_mssql.sql'
);
GO
