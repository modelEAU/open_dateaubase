-- ============================================================
-- Migration: make Channel.Unit_ID the authoritative unit holder;
--            drop Unit_ID from Parameter
-- Version:   v3.0.0 patch
-- Rationale: The Channel — not the Parameter — is the authoritative holder
--            of the unit for a measurement stream.  A Parameter describes
--            *what* is measured; the Channel describes *how* (port, provenance,
--            processing degree) and *in what unit*.  This allows different
--            instruments measuring the same parameter to record in different
--            natural units without a schema conflict.
--
-- Note: Channel.Unit_ID already exists (inherited when MetaData was renamed to
--       Channel in v1.0.0→v3.0.0).  This migration repurposes it, adds a FK
--       constraint if absent, backfills from Parameter.Unit_ID, then drops
--       Parameter.Unit_ID.
-- ============================================================

-- Step 1: Add FK on Channel.Unit_ID if it does not already exist
DECLARE @fkExists INT;
SELECT @fkExists = COUNT(*)
FROM   sys.foreign_keys        fk
JOIN   sys.foreign_key_columns fkc ON fk.[object_id] = fkc.[constraint_object_id]
WHERE  fk.[parent_object_id]  = OBJECT_ID(N'dbo.Channel')
  AND  COL_NAME(fkc.[parent_object_id], fkc.[parent_column_id]) = N'Unit_ID';

IF @fkExists = 0
BEGIN
    ALTER TABLE [dbo].[Channel]
        ADD CONSTRAINT [FK_Channel_Unit]
        FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);
END
GO

-- Step 2: Backfill Channel.Unit_ID from Parameter.Unit_ID for channels that
--         have a Parameter but no Unit yet.
UPDATE c
SET    c.[Unit_ID] = p.[Unit_ID]
FROM   [dbo].[Channel]   c
JOIN   [dbo].[Parameter] p ON p.[Parameter_ID] = c.[Parameter_ID]
WHERE  c.[Parameter_ID] IS NOT NULL
  AND  c.[Unit_ID]      IS NULL;
GO

-- Step 3: Drop the FK on Parameter.Unit_ID (constraint name discovered dynamically)
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT  @sql = N'ALTER TABLE [dbo].[Parameter] DROP CONSTRAINT [' + fk.[name] + N'];'
FROM    sys.foreign_keys        fk
JOIN    sys.foreign_key_columns fkc ON fk.[object_id] = fkc.[constraint_object_id]
WHERE   fk.[parent_object_id]  = OBJECT_ID(N'dbo.Parameter')
  AND   COL_NAME(fkc.[parent_object_id], fkc.[parent_column_id]) = N'Unit_ID';
IF LEN(@sql) > 0
    EXEC sp_executesql @sql;
GO

-- Step 4: Drop Parameter.Unit_ID column
ALTER TABLE [dbo].[Parameter] DROP COLUMN [Unit_ID];
GO

-- Step 5: Record schema version
INSERT INTO [dbo].[SchemaVersion] ([Version], [Description])
VALUES (N'3.0.1', N'Channel.Unit_ID promoted to authoritative unit; Parameter.Unit_ID dropped');
GO
