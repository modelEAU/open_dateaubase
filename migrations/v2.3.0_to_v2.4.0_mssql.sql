-- Migration: v2.3.0 -> v2.4.0
-- Platform: mssql
-- Generated: 2026-07-29 UTC
-- Rollback: v2.3.0_to_v2.4.0_mssql_rollback.sql
--
-- PRD 7 slice 1. Two identity changes:
--
--   1. Sample gains a FIELD replicate (distinct from the ANALYTICAL
--      LabAnalysis.Replicate) and a uniqueness constraint over
--      (SamplingPoint_ID, SampleDateTimeStart, SampleKind_ID, Replicate,
--      ParentSample_ID). MSSQL UNIQUE treats NULLs as equal, which is exactly
--      what is wanted: two re-imports of one field sample (both
--      ParentSample_ID NULL) collide, while aliquots of distinct parents,
--      blanks/standards of a different SampleKind, and genuine field
--      replicates all stay legal.
--
--   2. AnalysisSeries gains a nullable Laboratory_ID which joins
--      UQ_AnalysisSeries_Identity, so two laboratories measuring one parameter
--      at one sampling point become two series instead of colliding.
--
-- Every step is guarded, so re-running on an already-migrated database is a
-- no-op.

-- ---------------------------------------------------------------------------
-- 1. Sample.Replicate
-- ---------------------------------------------------------------------------

IF COL_LENGTH('dbo.Sample', 'Replicate') IS NULL
BEGIN
    -- ADD with a DEFAULT backfills every existing row with 1 in one pass.
    ALTER TABLE [dbo].[Sample]
        ADD [Replicate] INT NOT NULL CONSTRAINT [DF_Sample_Replicate] DEFAULT 1;
END
GO

-- Report (do not guess at) samples that the new constraint would reject.
IF NOT EXISTS (SELECT 1 FROM sys.objects
               WHERE [name] = 'UQ_Sample_Identity' AND [type] = 'UQ')
BEGIN
    IF EXISTS (
        SELECT 1 FROM [dbo].[Sample]
        GROUP BY [SamplingPoint_ID], [SampleDateTimeStart], [SampleKind_ID],
                 [Replicate], [ParentSample_ID]
        HAVING COUNT(*) > 1
    )
    BEGIN
        PRINT 'Duplicate Sample identities found — UQ_Sample_Identity cannot be added.';
        PRINT 'Give each duplicate a distinct Replicate, then re-run this migration:';
        SELECT [SamplingPoint_ID], [SampleDateTimeStart], [SampleKind_ID],
               [Replicate], [ParentSample_ID], COUNT(*) AS [Rows]
        FROM [dbo].[Sample]
        GROUP BY [SamplingPoint_ID], [SampleDateTimeStart], [SampleKind_ID],
                 [Replicate], [ParentSample_ID]
        HAVING COUNT(*) > 1;
    END
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.objects
               WHERE [name] = 'UQ_Sample_Identity' AND [type] = 'UQ')
BEGIN
    ALTER TABLE [dbo].[Sample]
        ADD CONSTRAINT [UQ_Sample_Identity] UNIQUE
            ([SamplingPoint_ID], [SampleDateTimeStart], [SampleKind_ID],
             [Replicate], [ParentSample_ID]);
END
GO

-- ---------------------------------------------------------------------------
-- 2. AnalysisSeries.Laboratory_ID
-- ---------------------------------------------------------------------------

IF COL_LENGTH('dbo.AnalysisSeries', 'Laboratory_ID') IS NULL
BEGIN
    ALTER TABLE [dbo].[AnalysisSeries] ADD [Laboratory_ID] INT NULL;
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys
               WHERE [name] = 'FK_AnalysisSeries_Laboratory_ID')
BEGIN
    ALTER TABLE [dbo].[AnalysisSeries]
        ADD CONSTRAINT [FK_AnalysisSeries_Laboratory_ID]
            FOREIGN KEY ([Laboratory_ID])
            REFERENCES [dbo].[Laboratory] ([Laboratory_ID]);
END
GO

-- Backfill from LabAnalysis, but only where the series has exactly one
-- non-NULL laboratory. Ambiguous series are reported below and left NULL —
-- picking one would silently merge two labs' results into one stream.
-- (Expected to be a no-op: the database holds no lab data yet.)
UPDATE a
SET a.[Laboratory_ID] = u.[Laboratory_ID]
FROM [dbo].[AnalysisSeries] a
JOIN (
    SELECT [AnalysisSeries_ID], MIN([Laboratory_ID]) AS [Laboratory_ID]
    FROM [dbo].[LabAnalysis]
    WHERE [Laboratory_ID] IS NOT NULL
    GROUP BY [AnalysisSeries_ID]
    HAVING COUNT(DISTINCT [Laboratory_ID]) = 1
) AS u ON u.[AnalysisSeries_ID] = a.[Stream_ID]
WHERE a.[Laboratory_ID] IS NULL;
GO

IF EXISTS (
    SELECT 1 FROM [dbo].[LabAnalysis]
    WHERE [Laboratory_ID] IS NOT NULL
    GROUP BY [AnalysisSeries_ID]
    HAVING COUNT(DISTINCT [Laboratory_ID]) > 1
)
BEGIN
    PRINT 'Ambiguous AnalysisSeries (more than one laboratory) — left NULL, split these by hand:';
    SELECT [AnalysisSeries_ID], COUNT(DISTINCT [Laboratory_ID]) AS [Laboratories]
    FROM [dbo].[LabAnalysis]
    WHERE [Laboratory_ID] IS NOT NULL
    GROUP BY [AnalysisSeries_ID]
    HAVING COUNT(DISTINCT [Laboratory_ID]) > 1;
END
GO

-- Widen the identity constraint to include the laboratory.
IF EXISTS (SELECT 1 FROM sys.objects
           WHERE [name] = 'UQ_AnalysisSeries_Identity' AND [type] = 'UQ')
BEGIN
    ALTER TABLE [dbo].[AnalysisSeries] DROP CONSTRAINT [UQ_AnalysisSeries_Identity];
END
GO

ALTER TABLE [dbo].[AnalysisSeries]
    ADD CONSTRAINT [UQ_AnalysisSeries_Identity] UNIQUE
        ([Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Laboratory_ID]);
GO

IF NOT EXISTS (SELECT 1 FROM [dbo].[SchemaVersion] WHERE [Version] = N'2.4.0')
BEGIN
    INSERT INTO [dbo].[SchemaVersion] ([Version], [Description])
    VALUES (N'2.4.0', N'PRD 7 slice 1. Sample gains a field Replicate (INT NOT NULL DEFAULT 1, distinct from the analytical LabAnalysis.Replicate) and UQ_Sample_Identity over (SamplingPoint_ID, SampleDateTimeStart, SampleKind_ID, Replicate, ParentSample_ID), so re-imports are rejected while aliquots, blanks, standards and genuine field replicates stay legal. AnalysisSeries gains a nullable Laboratory_ID which joins UQ_AnalysisSeries_Identity, so two laboratories measuring one parameter become two series.');
END
GO
