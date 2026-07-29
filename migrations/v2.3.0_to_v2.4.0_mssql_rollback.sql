-- Migration: v2.4.0 -> v2.3.0 (ROLLBACK)
-- Platform: mssql
-- Generated: 2026-07-29 UTC
--
-- Drops UQ_Sample_Identity and Sample.Replicate, and narrows
-- UQ_AnalysisSeries_Identity back to (Parameter_ID, SamplingPoint_ID,
-- ValueKind_ID) before dropping AnalysisSeries.Laboratory_ID.
--
-- LOSSY, and it can fail on purpose: if two series differ only by laboratory,
-- the narrowed constraint cannot be recreated. Merge or delete one of them
-- first — this script will not guess which.
--
-- Every step is guarded, so re-running is a no-op.

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'2.4.0';
GO

IF EXISTS (SELECT 1 FROM sys.objects
           WHERE [name] = 'UQ_AnalysisSeries_Identity' AND [type] = 'UQ')
BEGIN
    ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [UQ_AnalysisSeries_Identity];
END
GO

IF EXISTS (
    SELECT 1 FROM [dbo].[AnalysisSeries]
    GROUP BY [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID]
    HAVING COUNT(*) > 1
)
BEGIN
    PRINT 'Series differing only by laboratory exist — the v2.3.0 constraint cannot be restored:';
    SELECT [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], COUNT(*) AS [Rows]
    FROM [dbo].[AnalysisSeries]
    GROUP BY [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID]
    HAVING COUNT(*) > 1;
END
GO

ALTER TABLE [dbo].[AnalysisSeries]
    ADD CONSTRAINT [UQ_AnalysisSeries_Identity] UNIQUE
        ([Parameter_ID], [SamplingPoint_ID], [ValueKind_ID]);
GO

IF EXISTS (SELECT 1 FROM sys.foreign_keys
           WHERE [name] = 'FK_AnalysisSeries_Laboratory_ID')
BEGIN
    ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [FK_AnalysisSeries_Laboratory_ID];
END
GO

IF COL_LENGTH('dbo.AnalysisSeries', 'Laboratory_ID') IS NOT NULL
BEGIN
    ALTER TABLE [dbo].[AnalysisSeries] DROP COLUMN [Laboratory_ID];
END
GO

IF EXISTS (SELECT 1 FROM sys.objects
           WHERE [name] = 'UQ_Sample_Identity' AND [type] = 'UQ')
BEGIN
    ALTER TABLE [dbo].[Sample] DROP CONSTRAINT [UQ_Sample_Identity];
END
GO

-- The DEFAULT is named DF_Sample_Replicate when created by the forward
-- migration, but auto-named on a database built from the v2.4.0 create script.
-- Look it up rather than assuming.
DECLARE @df SYSNAME = (
    SELECT dc.[name]
    FROM sys.default_constraints dc
    JOIN sys.columns c
        ON c.[object_id] = dc.[parent_object_id]
       AND c.[column_id] = dc.[parent_column_id]
    WHERE dc.[parent_object_id] = OBJECT_ID('dbo.Sample')
      AND c.[name] = 'Replicate'
);
IF @df IS NOT NULL
    EXEC('ALTER TABLE [dbo].[Sample] DROP CONSTRAINT [' + @df + ']');
GO

IF COL_LENGTH('dbo.Sample', 'Replicate') IS NOT NULL
BEGIN
    ALTER TABLE [dbo].[Sample] DROP COLUMN [Replicate];
END
GO
