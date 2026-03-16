-- ============================================================
-- Rollback: v2.2.0 --> v2.1.0
-- Platform:  mssql
-- Generated: 2026-03-16
--
-- Applies to: a database at schema v2.2.0.
-- Produces:   the v2.1.0 schema.
-- Forward:    migrations/v2.1.0_to_v2.2.0_mssql.sql
--
-- WARNING — DATA LOSS
--   This rollback is DESTRUCTIVE. Any data stored in payload tables
--   (Value, ValueVector, ValueMatrix, ValueImage) after the forward
--   migration will be lost if those tables were restructured and
--   Observation rows added for them.
--
--   Only run this rollback on a TEST database or when you have
--   verified that the v2.2.0 schema changes are safe to reverse.
-- ============================================================

SET NOCOUNT ON;
SET XACT_ABORT ON;
SET QUOTED_IDENTIFIER ON;

-- Guard: ensure we are starting from v2.2.0.
IF OBJECT_ID('dbo.Observation') IS NULL
    RAISERROR('Observation table not found — this rollback expects a v2.2.0 schema.', 16, 1);
IF OBJECT_ID('dbo.Value') IS NULL
    RAISERROR('Value table not found — cannot perform rollback.', 16, 1);
GO

BEGIN TRANSACTION;
GO

-- ============================================================
-- ROLLBACK STEP 2: Restore Value table to v2.1.0 structure
-- ============================================================

-- Drop FK from Value to Observation.
ALTER TABLE [dbo].[Value] DROP CONSTRAINT [FK_Value_Observation];
GO

-- Drop PK on Observation_ID.
ALTER TABLE [dbo].[Value] DROP CONSTRAINT [PK_Value];
GO

-- Add back Channel_ID and Timestamp (nullable for population).
ALTER TABLE [dbo].[Value] ADD [Channel_ID] INT NULL;
ALTER TABLE [dbo].[Value] ADD [Timestamp]  DATETIME2(7) NULL;
GO

-- Repopulate Channel_ID and Timestamp from Observation.
UPDATE v
SET v.[Channel_ID] = o.[Channel_ID],
    v.[Timestamp]  = o.[Timestamp]
FROM [dbo].[Value] v
JOIN [dbo].[Observation] o
    ON o.[Observation_ID] = v.[Observation_ID];
GO

-- Drop Observation_ID column.
ALTER TABLE [dbo].[Value] DROP COLUMN [Observation_ID];
GO

-- Add Value_ID as an IDENTITY column (new identity values; originals are unrecoverable).
ALTER TABLE [dbo].[Value] ADD [Value_ID] BIGINT IDENTITY(1,1) NOT NULL;
GO

-- Restore PK on Value_ID.
ALTER TABLE [dbo].[Value]
    ADD CONSTRAINT [PK_Value] PRIMARY KEY ([Value_ID]);
GO

-- Restore FK Value.Channel_ID → Channel.
ALTER TABLE [dbo].[Value]
    ADD CONSTRAINT [FK_Value_Channel]
    FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
GO

-- ============================================================
-- ROLLBACK STEP 1: Drop Observation table
-- ============================================================

DROP INDEX [IX_Observation_Channel_Timestamp] ON [dbo].[Observation];
GO

DROP TABLE [dbo].[Observation];
GO

COMMIT;
GO
