-- Migration: v1.6.0 -> v1.7.0
-- Platform: mssql
-- Generated: 2026-02-18
-- Rollback: v1.6.0_to_v1.7.0_mssql_rollback.sql
-- Breaking changes: NONE
--
-- Phase 5a: Time Series Annotations
--   Task 1 — Create AnnotationType lookup table with seed data
--   Task 2 — Create Annotation table with FK constraints and indexes

-- ============================================================
-- Task 1: AnnotationType lookup table
-- ============================================================

CREATE TABLE [dbo].[AnnotationType] (
    [AnnotationType_ID]   INT            NOT NULL,
    [AnnotationTypeName]  NVARCHAR(100)  NOT NULL,
    [Description]         NVARCHAR(500)  NULL,
    [Color]               NVARCHAR(7)    NULL,

    CONSTRAINT [PK_AnnotationType] PRIMARY KEY ([AnnotationType_ID])
);
GO

-- Seed: 10 standard annotation types
INSERT INTO [dbo].[AnnotationType] ([AnnotationType_ID], [AnnotationTypeName], [Description], [Color])
VALUES
    (1,  N'Fault',              N'Sensor or process fault',                  N'#FF4444'),
    (2,  N'Maintenance',        N'Sensor under maintenance',                 N'#FFA500'),
    (3,  N'Calibration Period', N'Data during calibration — may be invalid', N'#FFD700'),
    (4,  N'Anomaly',            N'Unexpected behavior, needs investigation', N'#FF69B4'),
    (5,  N'Experiment',         N'Data collected during a specific experiment', N'#4488FF'),
    (6,  N'Process Event',      N'Known process event (storm, dosing, etc.)', N'#44BB44'),
    (7,  N'Data Quality',       N'Suspect data quality (drift, fouling)',    N'#AA44FF'),
    (8,  N'Note',               N'General commentary',                       N'#888888'),
    (9,  N'Exclusion',          N'Data should be excluded from analysis',    N'#CC0000'),
    (10, N'Validated',          N'Data has been reviewed and accepted',      N'#00AA00');
GO

-- ============================================================
-- Task 2: Annotation table
-- ============================================================

CREATE TABLE [dbo].[Annotation] (
    [Annotation_ID]       INT             IDENTITY(1,1) NOT NULL,
    [Metadata_ID]         INT             NOT NULL,
    [AnnotationType_ID]   INT             NOT NULL,
    [StartTime]           DATETIME2(7)    NOT NULL,
    [EndTime]             DATETIME2(7)    NULL,
    [AuthorPerson_ID]     INT             NULL,
    [Campaign_ID]         INT             NULL,
    [EquipmentEvent_ID]   INT             NULL,
    [Title]               NVARCHAR(200)   NULL,
    [Comment]             NVARCHAR(MAX)   NULL,
    [CreatedAt]           DATETIME2(7)    NOT NULL CONSTRAINT [DF_Annotation_CreatedAt] DEFAULT SYSUTCDATETIME(),
    [ModifiedAt]          DATETIME2(7)    NULL,

    CONSTRAINT [PK_Annotation] PRIMARY KEY ([Annotation_ID]),
    CONSTRAINT [FK_Annotation_MetaData]
        FOREIGN KEY ([Metadata_ID]) REFERENCES [dbo].[MetaData] ([Metadata_ID]),
    CONSTRAINT [FK_Annotation_AnnotationType]
        FOREIGN KEY ([AnnotationType_ID]) REFERENCES [dbo].[AnnotationType] ([AnnotationType_ID]),
    CONSTRAINT [FK_Annotation_AuthorPerson]
        FOREIGN KEY ([AuthorPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]),
    CONSTRAINT [FK_Annotation_Campaign]
        FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]),
    CONSTRAINT [FK_Annotation_EquipmentEvent]
        FOREIGN KEY ([EquipmentEvent_ID]) REFERENCES [dbo].[EquipmentEvent] ([EquipmentEvent_ID])
);
GO

CREATE INDEX [IX_Annotation_MetaData_Time]
    ON [dbo].[Annotation] ([Metadata_ID], [StartTime], [EndTime]);
GO

CREATE INDEX [IX_Annotation_Author]
    ON [dbo].[Annotation] ([AuthorPerson_ID], [CreatedAt]);
GO

-- ============================================================
-- Update SchemaVersion
-- ============================================================

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedAt], [Description], [MigrationScript])
VALUES (
    '1.7.0',
    GETUTCDATE(),
    'Phase 5a: Time Series Annotations — AnnotationType + Annotation tables for human-authored interval annotations',
    'v1.6.0_to_v1.7.0_mssql.sql'
);
GO
