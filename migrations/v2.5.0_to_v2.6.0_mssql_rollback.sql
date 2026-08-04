-- Migration: v2.6.0 -> v2.5.0 (ROLLBACK)
-- Platform: mssql
-- Generated: 2026-08-04 UTC
--
-- Drops Person.IsActive, OperationKind 7, ProcessUnit.TreatmentStage_ID, the
-- TreatmentStage vocabulary and ProcessUnitKind.Category, and removes the
-- ProcessUnitKind terms added at 2.6.0.
--
-- ProcessUnitKind IDs 12-31 are only removed where nothing references them: a
-- unit already classified as, say, a membrane bioreactor is left alone rather
-- than silently re-pointed at a term that means something else. Rows kept this
-- way are reported. The 2.5.0 descriptions of IDs 1-10 are restored verbatim.
--
-- Every step is guarded, so re-running is a no-op.

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'2.6.0';
GO

-- ---------------------------------------------------------------------------
-- 1. Person.IsActive
-- ---------------------------------------------------------------------------

IF COL_LENGTH('dbo.Person', 'IsActive') IS NOT NULL
BEGIN
    DECLARE @df SYSNAME;
    SELECT @df = dc.name FROM sys.default_constraints dc
    JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.Person') AND c.name = 'IsActive';
    IF @df IS NOT NULL EXEC('ALTER TABLE [dbo].[Person] DROP CONSTRAINT [' + @df + ']');
    ALTER TABLE [dbo].[Person] DROP COLUMN [IsActive];
END
GO

-- ---------------------------------------------------------------------------
-- 2. OperationKind 'Reconstruction'
-- ---------------------------------------------------------------------------

IF EXISTS (SELECT 1 FROM [dbo].[ProcessingStep] WHERE [OperationKind_ID] = 7)
BEGIN
    RAISERROR ('Rollback: ProcessingStep rows reference OperationKind 7 (Reconstruction). Reclassify them before rolling back; leaving the term in place.', 10, 1) WITH NOWAIT;
END
ELSE
BEGIN
    DELETE FROM [dbo].[OperationKind] WHERE [OperationKind_ID] = 7;
END
GO

UPDATE [dbo].[OperationKind]
    SET [Description] = N'Missing values filled by interpolation or reconstruction'
    WHERE [OperationKind_ID] = 6;
GO

-- ---------------------------------------------------------------------------
-- 3. ProcessUnit.TreatmentStage_ID + TreatmentStage
-- ---------------------------------------------------------------------------

IF OBJECT_ID('dbo.FK_ProcessUnit_TreatmentStage_ID', 'F') IS NOT NULL
BEGIN
    ALTER TABLE [dbo].[ProcessUnit] DROP CONSTRAINT [FK_ProcessUnit_TreatmentStage_ID];
END
GO

IF COL_LENGTH('dbo.ProcessUnit', 'TreatmentStage_ID') IS NOT NULL
BEGIN
    ALTER TABLE [dbo].[ProcessUnit] DROP COLUMN [TreatmentStage_ID];
END
GO

IF OBJECT_ID('dbo.TreatmentStage', 'U') IS NOT NULL
BEGIN
    DROP TABLE [dbo].[TreatmentStage];
END
GO

-- ---------------------------------------------------------------------------
-- 4. ProcessUnitKind terms added at 2.6.0, where unreferenced
-- ---------------------------------------------------------------------------

IF EXISTS (
    SELECT 1 FROM [dbo].[ProcessUnit]
    WHERE [ProcessUnitKind_ID] BETWEEN 12 AND 31
)
BEGIN
    RAISERROR ('Rollback: ProcessUnit rows still use ProcessUnitKind terms added at 2.6.0. Those terms are kept; reclassify the units and re-run to remove them.', 10, 1) WITH NOWAIT;
END
GO

DELETE FROM [dbo].[ProcessUnitKind]
WHERE [ProcessUnitKind_ID] BETWEEN 12 AND 31
  AND NOT EXISTS (
      SELECT 1 FROM [dbo].[ProcessUnit] pu
      WHERE pu.[ProcessUnitKind_ID] = [dbo].[ProcessUnitKind].[ProcessUnitKind_ID]
  );
GO

-- ---------------------------------------------------------------------------
-- 5. ProcessUnitKind.Category + the 2.5.0 descriptions
-- ---------------------------------------------------------------------------

IF OBJECT_ID('dbo.CK_ProcessUnitKind_Category', 'C') IS NOT NULL
BEGIN
    ALTER TABLE [dbo].[ProcessUnitKind] DROP CONSTRAINT [CK_ProcessUnitKind_Category];
END
GO

IF COL_LENGTH('dbo.ProcessUnitKind', 'Category') IS NOT NULL
BEGIN
    ALTER TABLE [dbo].[ProcessUnitKind] DROP COLUMN [Category];
END
GO

UPDATE [dbo].[ProcessUnitKind] SET [Description] = N'Broad spatial zone (e.g. biological treatment area)'      WHERE [ProcessUnitKind_ID] = 1;
UPDATE [dbo].[ProcessUnitKind] SET [Description] = N'Defined functional sub-zone within a process area'         WHERE [ProcessUnitKind_ID] = 2;
UPDATE [dbo].[ProcessUnitKind] SET [Description] = N'Enclosed vessel for liquid storage or treatment'           WHERE [ProcessUnitKind_ID] = 3;
UPDATE [dbo].[ProcessUnitKind] SET [Description] = N'Vessel designed for controlled biological or chemical reactions' WHERE [ProcessUnitKind_ID] = 4;
UPDATE [dbo].[ProcessUnitKind] SET [Description] = N'Conduit transporting liquid between process units'         WHERE [ProcessUnitKind_ID] = 5;
UPDATE [dbo].[ProcessUnitKind] SET [Description] = N'Mechanical device for moving liquid'                       WHERE [ProcessUnitKind_ID] = 6;
UPDATE [dbo].[ProcessUnitKind] SET [Description] = N'Flow control device regulating liquid passage'             WHERE [ProcessUnitKind_ID] = 7;
UPDATE [dbo].[ProcessUnitKind] SET [Description] = N'Gravity settling vessel separating solids from liquid'     WHERE [ProcessUnitKind_ID] = 8;
UPDATE [dbo].[ProcessUnitKind] SET [Description] = N'Open or partially open liquid containment structure'       WHERE [ProcessUnitKind_ID] = 9;
UPDATE [dbo].[ProcessUnitKind] SET [Description] = N'Mechanical device for supplying air or gas'                WHERE [ProcessUnitKind_ID] = 10;
GO
