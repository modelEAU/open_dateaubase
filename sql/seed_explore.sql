-- ============================================================
-- Explore page demonstration data (seed_explore.sql)
-- Scenario: Multi-type Feb 2026 monitoring data for the
--           Explore page (11_Explore.py) feature demonstration.
--
-- Date range:  2026-02-01T06:00:00 – 2026-02-28T22:00:00 UTC
--
-- Channels added:
--   CH-12  ISCO-001 Conductivity (scalar)
--   CH-13  HACH-001 Conductivity (vector, UV-Vis + LISST axes)
--   CH-14  ldo345   pH           (matrix, FlowCam × FlowCam)   [Equipment_ID=4]
--   CH-15  YSI-001  Conductivity (image)
--   CH-16  HACH-001 TSS          (scalar, 2 657 rows @ 15 min)
--   CH-17  HACH-001 COD          (vector, 27 895 rows @ 10 min × 7 bins)
--   CH-18  ldo345   TSS          (matrix,  5 320 rows @ 60 min × 4×2 bins)
--
-- NOTE: ValueImage rows reference filesystem paths that do not
-- exist in a fresh container; the Image tab gallery will display
-- metadata but image fetch will return 404 until files are seeded.
-- ============================================================

SET NOCOUNT ON;

-- ============================================================
-- Equipment: ldo345 (Hach 2100Q turbidimeter, serial 2222) → auto ID 4
-- ============================================================
INSERT INTO [dbo].[Equipment] (
    [EquipmentModel_ID], [Identifier],
    [SerialNumber], [Owner], [StorageLocation], [PurchaseDate]
) VALUES (3, N'ldo345', N'2222', N'modelEAU Lab', NULL, '2026-03-18');

-- ============================================================
-- Channels 12-18  (forced IDs to match live DB)
-- ============================================================
SET IDENTITY_INSERT [dbo].[Channel] ON;

-- CH-12: ISCO-001 Conductivity scalar (test channel)
INSERT INTO [dbo].[Channel] (
    [Channel_ID],[Equipment_ID],[Parameter_ID],[DataProvenance_ID],[ProcessingDegree_ID],[ValueType_ID]
) VALUES (12, 1, 5, 1, 1, 1);

-- CH-13: HACH-001 Conductivity vector (test channel)
INSERT INTO [dbo].[Channel] (
    [Channel_ID],[Equipment_ID],[Parameter_ID],[DataProvenance_ID],[ProcessingDegree_ID],[ValueType_ID]
) VALUES (13, 3, 5, 1, 1, 2);

-- CH-14: ldo345 pH matrix (test channel)
INSERT INTO [dbo].[Channel] (
    [Channel_ID],[Equipment_ID],[Parameter_ID],[DataProvenance_ID],[ProcessingDegree_ID],[ValueType_ID]
) VALUES (14, 4, 3, 1, 1, 3);

-- CH-15: YSI-001 Conductivity image (test channel)
INSERT INTO [dbo].[Channel] (
    [Channel_ID],[Equipment_ID],[Parameter_ID],[DataProvenance_ID],[ProcessingDegree_ID],[ValueType_ID]
) VALUES (15, 2, 5, 1, 1, 4);

-- CH-16: HACH-001 TSS scalar — primary Feb 2026 scalar demo
INSERT INTO [dbo].[Channel] (
    [Channel_ID],[Equipment_ID],[Parameter_ID],[DataProvenance_ID],[ProcessingDegree_ID],[ValueType_ID]
) VALUES (16, 3, 1, 1, 1, 1);

-- CH-17: HACH-001 COD vector (UV-Vis) — primary Feb 2026 vector demo
INSERT INTO [dbo].[Channel] (
    [Channel_ID],[Equipment_ID],[Parameter_ID],[DataProvenance_ID],[ProcessingDegree_ID],[ValueType_ID]
) VALUES (17, 3, 2, 1, 1, 2);

-- CH-18: ldo345 TSS matrix (LISST × FlowCam) — primary Feb 2026 matrix demo
INSERT INTO [dbo].[Channel] (
    [Channel_ID],[Equipment_ID],[Parameter_ID],[DataProvenance_ID],[ProcessingDegree_ID],[ValueType_ID]
) VALUES (18, 4, 1, 1, 1, 3);

SET IDENTITY_INSERT [dbo].[Channel] OFF;

-- ============================================================
-- ChannelAxis bindings for vector / matrix channels
-- (Axis IDs: 1=UV-Vis 7-bin, 2=LISST 4-bin, 3=FlowCam 2-bin)
-- ============================================================
-- CH-13 test vector: UV-Vis (role 0) + LISST (role 1)
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID],[AxisRole],[ValueBinningAxis_ID]) VALUES (13, 0, 1);
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID],[AxisRole],[ValueBinningAxis_ID]) VALUES (13, 1, 2);
-- CH-14 test matrix: FlowCam both axes (role 0 and 1)
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID],[AxisRole],[ValueBinningAxis_ID]) VALUES (14, 0, 3);
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID],[AxisRole],[ValueBinningAxis_ID]) VALUES (14, 1, 3);
-- CH-17 vector: UV-Vis axis (role 0)
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID],[AxisRole],[ValueBinningAxis_ID]) VALUES (17, 0, 1);
-- CH-18 matrix: LISST row (role 0) + FlowCam col (role 1)
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID],[AxisRole],[ValueBinningAxis_ID]) VALUES (18, 0, 2);
INSERT INTO [dbo].[ChannelAxis] ([Channel_ID],[AxisRole],[ValueBinningAxis_ID]) VALUES (18, 1, 3);

-- ============================================================
-- Scalar: Channel 16 — HACH-001 TSS, 15-min intervals
-- 2026-02-01T06:00 → 2026-02-28T22:00  (2 657 rows)
-- Value formula: 155 + 30·sin(i·0.05) + 12·sin(i·0.003) + 5·sin(i·0.5)
-- ============================================================
WITH n AS (
    SELECT 0 AS i
    UNION ALL
    SELECT i + 1 FROM n WHERE i < 2656
)
INSERT INTO [dbo].[Value] ([Channel_ID],[Value],[Timestamp])
SELECT
    16,
    155.0
        + 30.0 * SIN(CAST(i AS FLOAT) * 0.05)
        + 12.0 * SIN(CAST(i AS FLOAT) * 0.003)
        +  5.0 * SIN(CAST(i AS FLOAT) * 0.5),
    DATEADD(MINUTE, i * 15, CAST('2026-02-01T06:00:00' AS DATETIME2))
FROM n
OPTION (MAXRECURSION 0);

-- ============================================================
-- Scalar: Channel 2 — ISCO-001 COD, 30-min intervals
-- 2026-02-01T06:00 → 2026-02-28T22:00  (1 329 rows)
-- Value formula: 450 + 80·sin(i·0.04) + 25·sin(i·0.008)
-- ============================================================
WITH n AS (
    SELECT 0 AS i
    UNION ALL
    SELECT i + 1 FROM n WHERE i < 1328
)
INSERT INTO [dbo].[Value] ([Channel_ID],[Value],[Timestamp])
SELECT
    2,
    450.0
        + 80.0 * SIN(CAST(i AS FLOAT) * 0.04)
        + 25.0 * SIN(CAST(i AS FLOAT) * 0.008),
    DATEADD(MINUTE, i * 30, CAST('2026-02-01T06:00:00' AS DATETIME2))
FROM n
OPTION (MAXRECURSION 0);

-- ============================================================
-- Vector: Channel 17 — HACH-001 COD UV-Vis, 10-min intervals
-- 2026-02-01T06:00 → 2026-02-28T22:00 (3 985 timestamps × 7 bins = 27 895 rows)
-- Bin IDs 1–7 (UV-Vis axis); absorbance decreases with wavelength.
-- Value formula: (3.5 - (b-1)·0.45) + 0.5·sin(i·0.05) + 0.1·sin(i·0.3+b)
-- ============================================================
WITH ts AS (
    SELECT 0 AS i
    UNION ALL
    SELECT i + 1 FROM ts WHERE i < 3984
),
bins AS (
    SELECT 1 AS b UNION ALL SELECT 2 UNION ALL SELECT 3
    UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7
)
INSERT INTO [dbo].[ValueVector] ([Channel_ID],[Timestamp],[ValueBin_ID],[Value],[QualityCode])
SELECT
    17,
    DATEADD(MINUTE, i * 10, CAST('2026-02-01T06:00:00' AS DATETIME2)),
    b,
    (3.5 - CAST(b - 1 AS FLOAT) * 0.45)
        + 0.5 * SIN(CAST(i AS FLOAT) * 0.05)
        + 0.1 * SIN(CAST(i AS FLOAT) * 0.3 + CAST(b AS FLOAT)),
    NULL
FROM ts
CROSS JOIN bins
OPTION (MAXRECURSION 0);

-- ============================================================
-- Matrix: Channel 18 — ldo345 TSS LISST×FlowCam, 60-min intervals
-- 2026-02-01T06:00 → 2026-02-28T22:00 (665 timestamps × 8 cells = 5 320 rows)
-- Row bins: 8,9,10,11 (LISST particle size, Axis 2)
-- Col bins: 12,13     (FlowCam velocity,    Axis 3)
-- Value formula: (30 - (rb-8)·5 + (cb-12)·8) + 10·sin(i·0.03) + 5·sin(i·0.2 + (rb-8))
-- ============================================================
WITH ts AS (
    SELECT 0 AS i
    UNION ALL
    SELECT i + 1 FROM ts WHERE i < 664
),
row_bins AS (
    SELECT 8 AS rb UNION ALL SELECT 9 UNION ALL SELECT 10 UNION ALL SELECT 11
),
col_bins AS (
    SELECT 12 AS cb UNION ALL SELECT 13
)
INSERT INTO [dbo].[ValueMatrix] ([Channel_ID],[Timestamp],[RowValueBin_ID],[ColValueBin_ID],[Value])
SELECT
    18,
    DATEADD(MINUTE, i * 60, CAST('2026-02-01T06:00:00' AS DATETIME2)),
    rb,
    cb,
    (30.0 - CAST(rb - 8 AS FLOAT) * 5.0 + CAST(cb - 12 AS FLOAT) * 8.0)
        + 10.0 * SIN(CAST(i AS FLOAT) * 0.03)
        +  5.0 * SIN(CAST(i AS FLOAT) * 0.2 + CAST(rb - 8 AS FLOAT))
FROM ts
CROSS JOIN row_bins
CROSS JOIN col_bins
OPTION (MAXRECURSION 0);

-- ============================================================
-- Images: Channel 1 (ISCO-001 TSS image stream)
-- 12 PNG frames, every ~2 days, Feb 1–23 2026
-- Thumbnail column is NULL; storage files are not included in
-- the Docker image — fetch will return 404 until files are added.
-- ============================================================
INSERT INTO [dbo].[ValueImage] (
    [Channel_ID],[Timestamp],[ImageWidth],[ImageHeight],[NumberOfChannels],
    [ImageFormat],[FileSizeBytes],[StorageBackend],[StoragePath]
) VALUES
    (1, '2026-02-01T14:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-01T14-00-00.png'),
    (1, '2026-02-03T13:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-03T13-00-00.png'),
    (1, '2026-02-05T15:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-05T15-00-00.png'),
    (1, '2026-02-07T13:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-07T13-00-00.png'),
    (1, '2026-02-09T13:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-09T13-00-00.png'),
    (1, '2026-02-11T13:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-11T13-00-00.png'),
    (1, '2026-02-13T15:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-13T15-00-00.png'),
    (1, '2026-02-15T15:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-15T15-00-00.png'),
    (1, '2026-02-17T15:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-17T15-00-00.png'),
    (1, '2026-02-19T13:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-19T13-00-00.png'),
    (1, '2026-02-21T13:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-21T13-00-00.png'),
    (1, '2026-02-23T15:00:00', 640, 480, 3, N'PNG', 12288, N'FileSystem', N'uploads/images/1/2026-02-23T15-00-00.png');

-- ============================================================
-- Annotations on CH-16 (HACH-001 TSS) and CH-2 (ISCO-001 COD)
-- AnnotationType IDs (seeded in migration):
--   2=Maintenance, 5=Experiment, 7=Data Quality, 9=Exclusion
-- ============================================================
INSERT INTO [dbo].[Annotation] (
    [Channel_ID],[AnnotationType_ID],[StartTime],[EndTime],[AuthorPerson_ID],[Title],[Comment]
) VALUES
    -- CH-16: maintenance window (sensor cleaning)
    (16, 2, '2026-02-08T08:00:00', '2026-02-08T16:00:00', 1,
     N'Sensor cleaning', N'Routine in-situ cleaning; data in this interval may be unreliable.'),
    -- CH-16: data quality flag (suspected fouling)
    (16, 7, '2026-02-15T13:00:00', '2026-02-15T18:30:00', 1,
     N'Suspected fouling', N'Gradual positive drift observed; possible biofouling.'),
    -- CH-2:  experiment (carbon dosing trial)
    (2,  5, '2026-02-20T09:00:00', '2026-02-21T18:00:00', 1,
     N'Dosing trial', N'External carbon source added to inlet; elevated COD expected.'),
    -- CH-16: exclusion (sensor offline)
    (16, 9, '2026-02-22T00:00:00', '2026-02-22T06:00:00', 1,
     N'Sensor offline', N'Power interruption; no valid data recorded.'),
    -- CH-2:  experiment (same dosing trial, explicit label)
    (2,  5, '2026-02-20T09:00:00', '2026-02-21T18:00:00', 1,
     N'Carbon dosing trial', N'Carbon dosing experiment — see lab notes for dosing rate.');

PRINT 'Explore seed data loaded: equipment 5, channels 12-18, Feb 2026 time-series, annotations.';
