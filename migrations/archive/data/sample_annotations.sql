-- Seed Data: Sample Annotations
-- Schema version: >= 1.7.0
--
-- PURPOSE
--   Creates realistic example annotations on existing time series to
--   demonstrate each annotation type and to provide data for manual
--   testing of the Annotation API.
--   All annotations carry a "[DEMO]" prefix in their Title so they can
--   be identified and removed in production environments.
--
-- STRATEGY
--   The script targets the 3 MetaData series with the most Value rows.
--   For each series it places 5 annotations at positions derived from the
--   actual min/max timestamps of the series:
--     20 %        — point anomaly (suspicious reading)
--     38 – 40 %   — maintenance window
--     62 – 67 %   — sensor fault / power failure
--     67 – 85 %   — data quality concern following the fault
--     90 %        — general observer note
--
-- IDEMPOTENCY
--   Safe to run multiple times.  The final WHERE clause skips any MetaData
--   entry that already has at least one [DEMO] annotation.
--
-- CLEANUP
--   DELETE FROM [dbo].[Annotation] WHERE [Title] LIKE N'[DEMO]%';
--
-- Run this script after applying v1.6.0_to_v1.7.0_mssql.sql.

SET NOCOUNT ON;

DECLARE @before INT = (SELECT COUNT(*) FROM [dbo].[Annotation]);

-- ============================================================
-- Insert sample annotations (single batch, no cursor)
-- ============================================================

; WITH

-- Select the 3 busiest series that have a meaningful time span
top_series AS (
    SELECT TOP 3
        v.[Metadata_ID],
        MIN(v.[Timestamp])  AS t_min,
        MAX(v.[Timestamp])  AS t_max,
        DATEDIFF(SECOND, MIN(v.[Timestamp]), MAX(v.[Timestamp])) AS span_sec
    FROM [dbo].[Value] v
    GROUP BY v.[Metadata_ID]
    HAVING COUNT(*) >= 3
       AND DATEDIFF(SECOND, MIN(v.[Timestamp]), MAX(v.[Timestamp])) > 120
    ORDER BY COUNT(*) DESC
),

-- Pre-compute five anchor timestamps per series
anchors AS (
    SELECT
        [Metadata_ID],
        -- anomaly: 20 %
        DATEADD(SECOND, CAST(span_sec * 0.20 AS INT), t_min)  AS t_anomaly,
        -- maintenance: 38 – 40 %
        DATEADD(SECOND, CAST(span_sec * 0.38 AS INT), t_min)  AS t_maint_start,
        DATEADD(SECOND, CAST(span_sec * 0.40 AS INT), t_min)  AS t_maint_end,
        -- fault: 62 – 67 %
        DATEADD(SECOND, CAST(span_sec * 0.62 AS INT), t_min)  AS t_fault_start,
        DATEADD(SECOND, CAST(span_sec * 0.67 AS INT), t_min)  AS t_fault_end,
        -- data quality concern: 67 – 85 %
        DATEADD(SECOND, CAST(span_sec * 0.67 AS INT), t_min)  AS t_dq_start,
        DATEADD(SECOND, CAST(span_sec * 0.85 AS INT), t_min)  AS t_dq_end,
        -- note: 90 %
        DATEADD(SECOND, CAST(span_sec * 0.90 AS INT), t_min)  AS t_note
    FROM top_series
),

-- Expand each series into 5 annotation rows
annotation_rows AS (

    -- 1. Anomaly — suspicious spike, no known process cause
    SELECT
        [Metadata_ID],
        4       AS [AnnotationType_ID],   -- Anomaly
        t_anomaly  AS [StartTime],
        NULL       AS [EndTime],
        N'[DEMO] Unexpected spike'  AS [Title],
        N'Single-point excursion roughly 3× the rolling mean. No concurrent process event recorded. Possible air bubble or momentary probe displacement. Verify against grab sample if available.' AS [Comment]
    FROM anchors

    UNION ALL

    -- 2. Maintenance — scheduled probe cleaning
    SELECT
        [Metadata_ID],
        2,                                -- Maintenance
        t_maint_start,
        t_maint_end,
        N'[DEMO] Scheduled probe cleaning',
        N'Bi-monthly cleaning of optical window and flow cell. Sensor removed from process stream for ~2% of series duration. Readings during removal are not representative.'
    FROM anchors

    UNION ALL

    -- 3. Fault — power interruption
    SELECT
        [Metadata_ID],
        1,                                -- Fault
        t_fault_start,
        t_fault_end,
        N'[DEMO] Power failure — data gap',
        N'Mains supply interrupted. Logger lost power and stopped recording. Gap filled with NULLs at ingest. Post-restoration values may show a warm-up offset; see accompanying Data Quality annotation.'
    FROM anchors

    UNION ALL

    -- 4. Data Quality — post-fault drift / biofouling
    SELECT
        [Metadata_ID],
        7,                                -- Data Quality
        t_dq_start,
        t_dq_end,
        N'[DEMO] Possible biofouling drift after fault',
        N'Slow upward baseline drift observed from fault recovery through next cleaning event. Lab grab samples taken at the end of this window suggest the sensor was reading ~6 % high. Likely biofilm accumulation during the unmonitored outage period.'
    FROM anchors

    UNION ALL

    -- 5. Note — general observer commentary
    SELECT
        [Metadata_ID],
        8,                                -- Note
        t_note,
        NULL,
        N'[DEMO] Seasonal baseline shift expected',
        N'Water temperature crossing 18 °C from this point forward. Expect downstream effect on dissolved oxygen saturation and biological activity. Normal seasonal behaviour for this site; no corrective action required.'
    FROM anchors
)

INSERT INTO [dbo].[Annotation]
    ([Metadata_ID], [AnnotationType_ID], [StartTime], [EndTime], [Title], [Comment])
SELECT
    ar.[Metadata_ID],
    ar.[AnnotationType_ID],
    ar.[StartTime],
    ar.[EndTime],
    ar.[Title],
    ar.[Comment]
FROM annotation_rows ar
WHERE NOT EXISTS (
    SELECT 1
    FROM [dbo].[Annotation] a
    WHERE a.[Metadata_ID] = ar.[Metadata_ID]
      AND a.[Title] LIKE N'[DEMO]%'
);

-- ============================================================
-- Report
-- ============================================================

DECLARE @after INT = (SELECT COUNT(*) FROM [dbo].[Annotation]);

SELECT
    (SELECT COUNT(*) FROM [dbo].[Value])                           AS total_value_rows,
    (SELECT COUNT(DISTINCT [Metadata_ID]) FROM [dbo].[Value])     AS series_with_data,
    @after - @before                                               AS annotations_created,
    @before                                                        AS annotations_already_existed;
GO
