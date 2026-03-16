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

-- ============================================================
-- STEP 2: Data integrity check + backfill Observation from Value;
--         restructure Value as lean scalar payload
-- ============================================================

-- Pre-migration duplicate check — fail if any (Channel_ID, Timestamp) pair
-- appears more than once in Value (would violate UQ_Observation_ChannelTimestampType).
IF EXISTS (
    SELECT [Channel_ID], [Timestamp]
    FROM [dbo].[Value]
    WHERE [Channel_ID] IS NOT NULL AND [Timestamp] IS NOT NULL
    GROUP BY [Channel_ID], [Timestamp]
    HAVING COUNT(*) > 1
)
    RAISERROR('Duplicate (Channel_ID, Timestamp) pairs in dbo.Value — deduplicate before migrating.', 16, 1);
GO

-- Backfill Observation rows from Value (one per scalar row).
INSERT INTO [dbo].[Observation] ([Channel_ID], [Timestamp], [DataType])
SELECT [Channel_ID], [Timestamp], 'Scalar'
FROM [dbo].[Value]
WHERE [Channel_ID] IS NOT NULL AND [Timestamp] IS NOT NULL;
GO

-- Add Observation_ID column to Value (nullable until populated).
ALTER TABLE [dbo].[Value] ADD [Observation_ID] BIGINT NULL;
GO

-- Populate Observation_ID by joining back to Observation.
UPDATE v
SET v.[Observation_ID] = o.[Observation_ID]
FROM [dbo].[Value] v
JOIN [dbo].[Observation] o
    ON o.[Channel_ID] = v.[Channel_ID]
   AND o.[Timestamp]  = v.[Timestamp]
   AND o.[DataType]   = 'Scalar';
GO

-- Make Observation_ID NOT NULL now that all rows are populated.
ALTER TABLE [dbo].[Value] ALTER COLUMN [Observation_ID] BIGINT NOT NULL;
GO

-- Drop FK_Value_Channel (blocks column drop).
ALTER TABLE [dbo].[Value] DROP CONSTRAINT [FK_Value_Channel];
GO

-- Drop PK on Value_ID (use dynamic name lookup for safety).
DECLARE @pk NVARCHAR(200) = (
    SELECT name FROM sys.key_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.Value') AND type = 'PK'
);
IF @pk IS NOT NULL
    EXEC('ALTER TABLE [dbo].[Value] DROP CONSTRAINT [' + @pk + ']');
GO

-- Drop Value_ID (IDENTITY — no other table FKs into Value.Value_ID).
ALTER TABLE [dbo].[Value] DROP COLUMN [Value_ID];
GO

-- Drop Channel_ID and Timestamp (now redundant, encoded in Observation).
ALTER TABLE [dbo].[Value] DROP COLUMN [Channel_ID];
ALTER TABLE [dbo].[Value] DROP COLUMN [Timestamp];
GO

-- Add new PK on Observation_ID.
ALTER TABLE [dbo].[Value]
    ADD CONSTRAINT [PK_Value] PRIMARY KEY ([Observation_ID]);
GO

-- Add FK Observation_ID → Observation.
ALTER TABLE [dbo].[Value]
    ADD CONSTRAINT [FK_Value_Observation]
    FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
GO
