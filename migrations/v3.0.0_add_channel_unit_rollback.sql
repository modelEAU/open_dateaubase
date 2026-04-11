-- ============================================================
-- Rollback: restore Unit_ID on Parameter; revert Channel.Unit_ID
-- Reverses: v3.0.0_add_channel_unit.sql
--
-- Note: Channel.Unit_ID is NOT dropped (it existed before this migration).
--       We just restore Parameter.Unit_ID and remove the FK from Channel.
-- ============================================================

-- Step 1: Re-add Unit_ID to Parameter as nullable
ALTER TABLE [dbo].[Parameter] ADD [Unit_ID] INT NULL;
GO

-- Step 2: Add FK back on Parameter.Unit_ID
ALTER TABLE [dbo].[Parameter]
    ADD CONSTRAINT [FK_Parameter_Unit]
    FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);
GO

-- Step 3: Backfill Parameter.Unit_ID from Channel.Unit_ID
--         For each parameter, pick the most common non-null unit used across its channels.
UPDATE p
SET    p.[Unit_ID] = (
    SELECT TOP 1 c.[Unit_ID]
    FROM   [dbo].[Channel] c
    WHERE  c.[Parameter_ID] = p.[Parameter_ID]
      AND  c.[Unit_ID] IS NOT NULL
    GROUP BY c.[Unit_ID]
    ORDER BY COUNT(*) DESC
)
FROM   [dbo].[Parameter] p
WHERE  EXISTS (
    SELECT 1 FROM [dbo].[Channel] c2
    WHERE  c2.[Parameter_ID] = p.[Parameter_ID]
      AND  c2.[Unit_ID] IS NOT NULL
);
GO

-- Step 4: Drop FK on Channel.Unit_ID if it was added by this migration
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT  @sql = N'ALTER TABLE [dbo].[Channel] DROP CONSTRAINT [' + fk.[name] + N'];'
FROM    sys.foreign_keys        fk
JOIN    sys.foreign_key_columns fkc ON fk.[object_id] = fkc.[constraint_object_id]
WHERE   fk.[parent_object_id]  = OBJECT_ID(N'dbo.Channel')
  AND   fk.[name]              = N'FK_Channel_Unit';
IF LEN(@sql) > 0
    EXEC sp_executesql @sql;
GO

-- Step 5: Remove schema version record
DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'3.0.1';
GO
