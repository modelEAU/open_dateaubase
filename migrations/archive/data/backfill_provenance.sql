-- Data migration: Backfill DataProvenance_ID on existing MetaData rows
-- Schema version: >= 1.2.0
--
-- Strategy:
--   MetaData rows that have an Equipment_ID are classified as Sensor (ID=1).
--   All other rows remain NULL (to be classified manually by data stewards).
--
-- This script is idempotent: re-running it will only update rows that are
-- still NULL and match the classification criteria.
--
-- Run this script after applying v1.1.0_to_v1.2.0_mssql.sql.
-- Review the output statistics before committing to production.

-- ============================================================
-- Step 1: Classify rows with Equipment_ID as Sensor (DataProvenance_ID=1)
-- ============================================================

UPDATE [dbo].[MetaData]
SET [DataProvenance_ID] = 1  -- Sensor
WHERE [Equipment_ID] IS NOT NULL
  AND [DataProvenance_ID] IS NULL;
GO

-- ============================================================
-- Step 2: Report classification statistics
-- ============================================================

SELECT
    CASE
        WHEN [DataProvenance_ID] IS NULL THEN 'Unclassified (NULL)'
        ELSE dp.[DataProvenance_Name]
    END AS [Provenance],
    COUNT(*) AS [RowCount]
FROM [dbo].[MetaData] m
LEFT JOIN [dbo].[DataProvenance] dp ON m.[DataProvenance_ID] = dp.[DataProvenance_ID]
GROUP BY
    CASE
        WHEN [DataProvenance_ID] IS NULL THEN 'Unclassified (NULL)'
        ELSE dp.[DataProvenance_Name]
    END
ORDER BY [Provenance];
GO

-- NOTE: Rows with NULL DataProvenance_ID after this script are MetaData entries
-- without an Equipment_ID (lab data entered manually, external sources, etc.).
-- These must be classified by a domain expert before DataProvenance_ID is
-- made NOT NULL in a future migration.
