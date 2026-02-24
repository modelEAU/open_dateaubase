-- Data Migration: Backfill Sensor Status MetaData for existing sensor channels
-- Schema version: >= 1.8.0
--
-- PURPOSE
--   Phase 5b introduced per-channel and per-device status time series stored
--   as regular MetaData / Value rows.  This script creates a companion
--   "Sensor Status" MetaData entry for every existing measurement MetaData
--   row that originates from a physical sensor (Equipment_ID IS NOT NULL) and
--   does not yet have a companion status channel.
--
--   For each new status MetaData entry an initial Value of 1 (Operational)
--   is inserted at the earliest known timestamp for that measurement series,
--   or '2000-01-01' if the series has no values yet.
--
--   An IngestionRoute entry is also created for each new status channel so
--   that the ingestion pipeline can route incoming status values automatically.
--
-- WHY THIS MATTERS
--   Without this backfill existing sensors are invisible to the
--   vw_ChannelStatus view.  Running this script once puts all pre-v1.8.0
--   channels into a known "Operational" baseline state from which future
--   status transitions can be recorded.
--
-- IDEMPOTENCY
--   Safe to run multiple times.  The outer NOT EXISTS guard checks whether
--   a companion status MetaData entry already exists for each source channel.
--
-- VALIDITY WINDOW
--   ValidFrom on the new IngestionRoute is set to the same timestamp used for
--   the initial Operational value — the earliest known data point, or
--   '2000-01-01' as a sentinel when no values exist.
--
-- RUN ORDER
--   1. Apply v1.7.0_to_v1.8.0_mssql.sql  (creates SensorStatusCode,
--      adds StatusOfMetaDataID / StatusOfEquipmentID columns,
--      seeds dbo.Parameter with 'Sensor Status', seeds dbo.Unit with
--      'Status Code').
--   2. Run this script.

SET NOCOUNT ON;

-- ============================================================
-- Look up seeded IDs (inserted by the v1.8.0 migration)
-- ============================================================

DECLARE @sensor_status_param_id INT =
    (SELECT [Parameter_ID] FROM [dbo].[Parameter] WHERE [Parameter] = N'Sensor Status');

DECLARE @status_code_unit_id    INT =
    (SELECT [Unit_ID]      FROM [dbo].[Unit]      WHERE [Unit]      = N'Status Code');

DECLARE @sensor_provenance_id   INT =
    (SELECT [DataProvenance_ID] FROM [dbo].[DataProvenance] WHERE [DataProvenance_Name] = N'Sensor');

IF @sensor_status_param_id IS NULL
    RAISERROR('Parameter "Sensor Status" not found. Apply v1.7.0_to_v1.8.0_mssql.sql first.', 16, 1);
IF @status_code_unit_id IS NULL
    RAISERROR('Unit "Status Code" not found. Apply v1.7.0_to_v1.8.0_mssql.sql first.', 16, 1);

DECLARE @md_inserted INT = 0;
DECLARE @v_inserted  INT = 0;
DECLARE @ir_inserted INT = 0;

-- ============================================================
-- Step 1: Create companion status MetaData for each sensor channel
--         that does not already have one
-- ============================================================

INSERT INTO [dbo].[MetaData] (
    [Equipment_ID],
    [Parameter_ID],
    [Unit_ID],
    [Sampling_point_ID],
    [ValueType_ID],
    [DataProvenance_ID],
    [ProcessingDegree],
    [StatusOfMetaDataID]
)
SELECT
    m.[Equipment_ID],
    @sensor_status_param_id,
    @status_code_unit_id,
    m.[Sampling_point_ID],
    1,                           -- Scalar (ValueType_ID = 1)
    @sensor_provenance_id,
    N'Raw',
    m.[Metadata_ID]              -- this is a status channel for m
FROM [dbo].[MetaData] m
WHERE m.[Equipment_ID]        IS NOT NULL    -- sensor-sourced
  AND m.[StatusOfMetaDataID]  IS NULL        -- not itself a status channel
  AND m.[StatusOfEquipmentID] IS NULL        -- not a device-level status channel
  AND NOT EXISTS (
      SELECT 1
      FROM [dbo].[MetaData] s
      WHERE s.[StatusOfMetaDataID] = m.[Metadata_ID]
  );

SET @md_inserted = @@ROWCOUNT;

-- ============================================================
-- Step 2: Insert an initial Operational status value (code = 1)
--         for every newly created status channel
-- ============================================================

INSERT INTO [dbo].[Value] ([Metadata_ID], [Value], [Timestamp])
SELECT
    sm.[Metadata_ID],
    1.0,    -- StatusCodeID 1 = Operational
    COALESCE(
        (SELECT MIN(v.[Timestamp])
         FROM   [dbo].[Value] v
         WHERE  v.[Metadata_ID] = sm.[StatusOfMetaDataID]),
        CAST('2000-01-01T00:00:00' AS DATETIME2(7))
    )
FROM [dbo].[MetaData] sm
WHERE sm.[StatusOfMetaDataID] IS NOT NULL
  AND sm.[Parameter_ID]       = @sensor_status_param_id
  AND NOT EXISTS (
      SELECT 1
      FROM [dbo].[Value] v
      WHERE v.[Metadata_ID] = sm.[Metadata_ID]
  );

SET @v_inserted = @@ROWCOUNT;

-- ============================================================
-- Step 3: Create IngestionRoute entries for the new status channels
--         (mirrors what backfill_ingestion_routes.sql does for regular
--          channels, but scoped to the status parameter)
-- ============================================================

INSERT INTO [dbo].[IngestionRoute] (
    [Equipment_ID],
    [Parameter_ID],
    [DataProvenance_ID],
    [ProcessingDegree],
    [ValidFrom],
    [ValidTo],
    [Metadata_ID],
    [Notes]
)
SELECT
    sm.[Equipment_ID],
    sm.[Parameter_ID],
    @sensor_provenance_id,
    N'Raw',
    -- ValidFrom = same sentinel used for the initial status value
    COALESCE(
        (SELECT MIN(v.[Timestamp])
         FROM   [dbo].[Value] v
         WHERE  v.[Metadata_ID] = sm.[StatusOfMetaDataID]),
        CAST('2000-01-01T00:00:00' AS DATETIME2(7))
    ),
    NULL,   -- ValidTo = NULL = still active
    sm.[Metadata_ID],
    N'Backfilled by migrations/data/backfill_sensor_status.sql'
FROM [dbo].[MetaData] sm
WHERE sm.[StatusOfMetaDataID] IS NOT NULL
  AND sm.[Parameter_ID]       = @sensor_status_param_id
  AND sm.[Equipment_ID]       IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM [dbo].[IngestionRoute] r
      WHERE r.[Metadata_ID]       = sm.[Metadata_ID]
        AND r.[Equipment_ID]      = sm.[Equipment_ID]
        AND r.[Parameter_ID]      = sm.[Parameter_ID]
        AND r.[DataProvenance_ID] = @sensor_provenance_id
        AND r.[ProcessingDegree]  = N'Raw'
  );

SET @ir_inserted = @@ROWCOUNT;

-- ============================================================
-- Report
-- ============================================================

DECLARE @existing_sensor_md INT =
    (SELECT COUNT(*)
     FROM   [dbo].[MetaData]
     WHERE  [Equipment_ID]        IS NOT NULL
       AND  [StatusOfMetaDataID]  IS NULL
       AND  [StatusOfEquipmentID] IS NULL);

DECLARE @already_had_status INT =
    (SELECT COUNT(*)
     FROM   [dbo].[MetaData] m
     WHERE  m.[Equipment_ID]       IS NOT NULL
       AND  m.[StatusOfMetaDataID] IS NULL
       AND  EXISTS (
           SELECT 1
           FROM   [dbo].[MetaData] s
           WHERE  s.[StatusOfMetaDataID] = m.[Metadata_ID]
       ));

SELECT
    @existing_sensor_md  AS sensor_channels_in_database,
    @already_had_status  AS channels_already_had_status,
    @md_inserted         AS status_metadata_created,
    @v_inserted          AS initial_status_values_inserted,
    @ir_inserted         AS ingestion_routes_created;
GO
