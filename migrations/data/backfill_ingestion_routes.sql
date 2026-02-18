-- Data Migration: Backfill IngestionRoute for existing MetaData rows
-- Phase 2d: Ingestion Routing — Task 2d.3
-- Generated: 2026-02-18
--
-- PURPOSE
--   Creates an IngestionRoute entry for every MetaData row that has both
--   an Equipment_ID and a Parameter_ID (i.e. sensor data). Lab and manual-
--   entry MetaData rows (Equipment_ID IS NULL) are skipped because routing
--   for those is driven by Sample/Laboratory context, not equipment identity.
--
-- IDEMPOTENCY
--   Safe to run multiple times. Uses a NOT EXISTS guard so duplicate routes
--   are never created.
--
-- VALIDITY WINDOW
--   ValidFrom is set to the earliest timestamp found in dbo.Value for each
--   MetaData entry. If no Value rows exist yet, '2000-01-01' is used as a
--   safe sentinel.
--
-- REVIEW BEFORE RUNNING IN PRODUCTION
--   1. Verify that the Equipment_ID + Parameter_ID pairs are unambiguous.
--   2. Confirm that ProcessingDegree = 'Raw' is correct for all existing rows.
--   3. Decide whether DataProvenance_ID = 1 (Sensor) is correct for rows
--      that still have NULL DataProvenance_ID.

SET NOCOUNT ON;

DECLARE @inserted   INT = 0;
DECLARE @skipped    INT = 0;
DECLARE @no_equip   INT = 0;

-- ============================================================
-- Count MetaData rows with no Equipment_ID (lab/manual — expected)
-- ============================================================

SELECT @no_equip = COUNT(*)
FROM [dbo].[MetaData]
WHERE [Equipment_ID] IS NULL OR [Parameter_ID] IS NULL;

-- ============================================================
-- Insert missing routes for equipment-based MetaData rows
-- ============================================================

INSERT INTO [dbo].[IngestionRoute]
    ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree],
     [ValidFrom], [ValidTo], [Metadata_ID], [Notes])
SELECT
    m.[Equipment_ID],
    m.[Parameter_ID],
    COALESCE(m.[DataProvenance_ID], 1),   -- default to Sensor (ID=1) when NULL
    'Raw',
    COALESCE(
        (SELECT MIN(v.[Timestamp]) FROM [dbo].[Value] v WHERE v.[Metadata_ID] = m.[Metadata_ID]),
        CAST('2000-01-01T00:00:00' AS DATETIME2(7))
    ) AS ValidFrom,
    NULL,     -- ValidTo = NULL = still active
    m.[Metadata_ID],
    'Backfilled by migrations/data/backfill_ingestion_routes.sql'
FROM [dbo].[MetaData] m
WHERE m.[Equipment_ID] IS NOT NULL
  AND m.[Parameter_ID] IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM [dbo].[IngestionRoute] r
    WHERE r.[Metadata_ID]       = m.[Metadata_ID]
      AND r.[Equipment_ID]      = m.[Equipment_ID]
      AND r.[Parameter_ID]      = m.[Parameter_ID]
      AND r.[DataProvenance_ID] = COALESCE(m.[DataProvenance_ID], 1)
      AND r.[ProcessingDegree]  = 'Raw'
  );

SET @inserted = @@ROWCOUNT;

SELECT @skipped = COUNT(*)
FROM [dbo].[MetaData] m
WHERE m.[Equipment_ID] IS NOT NULL
  AND m.[Parameter_ID] IS NOT NULL
  AND EXISTS (
    SELECT 1
    FROM [dbo].[IngestionRoute] r
    WHERE r.[Metadata_ID]       = m.[Metadata_ID]
      AND r.[Equipment_ID]      = m.[Equipment_ID]
      AND r.[Parameter_ID]      = m.[Parameter_ID]
      AND r.[DataProvenance_ID] = COALESCE(m.[DataProvenance_ID], 1)
      AND r.[ProcessingDegree]  = 'Raw'
  );

-- ============================================================
-- Report
-- ============================================================

SELECT
    @inserted  AS routes_created,
    @skipped   AS routes_already_existed,
    @no_equip  AS metadata_rows_without_equipment_skipped;
GO
