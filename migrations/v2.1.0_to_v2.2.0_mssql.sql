-- ============================================================
-- Migration: v2.1.0 --> v2.2.0
-- Platform:  mssql
-- Generated: 2026-03-16
-- Introduces the Observation hub table; restructures Value, ValueVector,
-- ValueMatrix, ValueImage as lean payload tables keyed by Observation_ID.
-- Annotation gains optional Observation_ID FK for point-level annotations.
-- Rollback: migrations/v2.1.0_to_v2.2.0_rollback_mssql.sql
-- ============================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;
SET QUOTED_IDENTIFIER ON;

IF OBJECT_ID('dbo.Value') IS NULL
    RAISERROR('Value table not found — migration expects v2.1.0 baseline.', 16, 1);
IF OBJECT_ID('dbo.Observation') IS NOT NULL
    RAISERROR('Observation table already exists — migration may have already been applied.', 16, 1);
GO

BEGIN TRANSACTION;
GO

-- ============================================================
-- STEP 1: Create Observation hub table
-- ============================================================

CREATE TABLE [dbo].[Observation] (
    [Observation_ID] BIGINT        IDENTITY(1,1) NOT NULL,
    [Channel_ID]     INT           NOT NULL,
    [Timestamp]      DATETIME2(7)  NOT NULL,
    [DataType]       VARCHAR(10)   NOT NULL,
    CONSTRAINT [PK_Observation] PRIMARY KEY ([Observation_ID]),
    CONSTRAINT [UQ_Observation_ChannelTimestampType]
        UNIQUE ([Channel_ID], [Timestamp], [DataType]),
    CONSTRAINT [FK_Observation_Channel]
        FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]),
    CONSTRAINT [CK_Observation_DataType]
        CHECK ([DataType] IN ('Scalar','Vector','Matrix','Image'))
);
GO

CREATE INDEX [IX_Observation_Channel_Timestamp]
    ON [dbo].[Observation] ([Channel_ID], [Timestamp]);
GO
