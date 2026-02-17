-- Seed data for schema v1.1.0
-- Generalized binned value types: vectors (spectra, PSDs), matrices (joint distributions), images
-- All timestamps are UTC by convention. Original measurements were in EDT (UTC-4); converted here.

-- =============================================================================
-- New Unit rows for axis coordinates
-- (5 existing units assumed from seed_v1.0.0; new axis units added here)
-- =============================================================================

INSERT INTO [dbo].[Unit] ([Unit]) VALUES ('nm');    -- ID 6: nanometres (UV-Vis wavelength axis)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'µm');   -- ID 7: micrometres (particle size axis)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES ('m/s');   -- ID 8: metres per second (velocity axis)

-- =============================================================================
-- ValueBinningAxis: named physical axes
-- =============================================================================

-- UV-Vis wavelength axis (256-channel spectrometer, 7 representative bins shown)
INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID])
VALUES ('S::CAN spectro::lyser UV-Vis',
        'UV-Vis absorption spectrometer 200-750 nm, 7 representative bins',
        7, 6);   -- ID 1, Unit=nm

-- Particle size axis (LISST-200X style, 4 fractions by equivalent spherical diameter)
INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID])
VALUES ('LISST-200X particle size',
        'Volume-equivalent spherical diameter fractionation, 4 size classes',
        4, 7);   -- ID 2, Unit=µm

-- Particle velocity axis (FlowCam style, 2 settling velocity fractions)
INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID])
VALUES ('FlowCam particle velocity',
        'Settling velocity fractionation for joint size-velocity distribution',
        2, 8);   -- ID 3, Unit=m/s

-- =============================================================================
-- ValueBin: bin definitions [LowerBound inclusive, UpperBound exclusive)
-- =============================================================================

-- UV-Vis bins (ValueBinningAxis_ID=1): 7 representative channels across 200-750 nm
-- BinIndex matches the 0-based channel index in the 256-channel spectrometer
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (1, 0,   197.5, 202.5);   -- ID 1,  centre ~200.0 nm
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (1, 10,  219.1, 224.1);   -- ID 2,  centre ~221.6 nm
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (1, 50,  305.3, 310.3);   -- ID 3,  centre ~307.8 nm
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (1, 100, 413.2, 418.2);   -- ID 4,  centre ~415.7 nm
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (1, 150, 521.0, 526.0);   -- ID 5,  centre ~523.5 nm
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (1, 200, 628.9, 633.9);   -- ID 6,  centre ~631.4 nm
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (1, 255, 747.5, 752.5);   -- ID 7,  centre ~750.0 nm

-- Particle size bins (ValueBinningAxis_ID=2): 4 size fractions
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (2, 0, 0.0,    63.0);     -- ID 8,  <63 µm
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (2, 1, 63.0,   125.0);    -- ID 9,  63-125 µm
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (2, 2, 125.0,  250.0);    -- ID 10, 125-250 µm
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (2, 3, 250.0,  10000.0);  -- ID 11, >250 µm

-- Velocity bins (ValueBinningAxis_ID=3): 2 settling velocity fractions
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (3, 0, 0.0, 0.5);         -- ID 12, slow (0.0-0.5 m/s)
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [LowerBound], [UpperBound])
VALUES (3, 1, 0.5, 2.0);         -- ID 13, fast (0.5-2.0 m/s)

-- =============================================================================
-- MetaData rows for new value types
-- (IDs 1-6 exist from previous seeds; continue from ID 7)
-- =============================================================================

-- Vector: UV-Vis absorbance at WWTP inlet (ValueType=2=Vector, no measured value unit)
INSERT INTO [dbo].[MetaData] ([Project_ID], [Contact_ID], [Equipment_ID], [Parameter_ID], [Procedure_ID], [Unit_ID], [Purpose_ID], [Sampling_point_ID], [Condition_ID], [ValueType_ID])
VALUES (1, 1, NULL, NULL, 3, NULL, 1, 1, 1, 2);  -- ID 7

-- Image: camera at CSO outfall (ValueType=4=Image)
INSERT INTO [dbo].[MetaData] ([Project_ID], [Contact_ID], [Equipment_ID], [Parameter_ID], [Procedure_ID], [Unit_ID], [Purpose_ID], [Sampling_point_ID], [Condition_ID], [ValueType_ID])
VALUES (2, 2, NULL, NULL, 3, NULL, 2, 3, 2, 4);  -- ID 8

-- Vector: particle size distribution at WWTP inlet (ValueType=2=Vector, Unit=mg/L)
INSERT INTO [dbo].[MetaData] ([Project_ID], [Contact_ID], [Equipment_ID], [Parameter_ID], [Procedure_ID], [Unit_ID], [Purpose_ID], [Sampling_point_ID], [Condition_ID], [ValueType_ID])
VALUES (1, 2, NULL, NULL, 1, 1, 1, 1, 1, 2);  -- ID 9

-- Matrix: particle size-velocity joint distribution at WWTP inlet (ValueType=3=Matrix)
INSERT INTO [dbo].[MetaData] ([Project_ID], [Contact_ID], [Equipment_ID], [Parameter_ID], [Procedure_ID], [Unit_ID], [Purpose_ID], [Sampling_point_ID], [Condition_ID], [ValueType_ID])
VALUES (1, 2, NULL, NULL, 1, NULL, 1, 1, 1, 3);  -- ID 10

-- =============================================================================
-- MetaDataAxis: link MetaData series to their binning axes
-- =============================================================================

-- UV-Vis spectrum (ID 7): 1D Vector, single wavelength axis
INSERT INTO [dbo].[MetaDataAxis] ([Metadata_ID], [AxisRole], [ValueBinningAxis_ID])
VALUES (7, 0, 1);

-- PSD (ID 9): 1D Vector, single particle-size axis
INSERT INTO [dbo].[MetaDataAxis] ([Metadata_ID], [AxisRole], [ValueBinningAxis_ID])
VALUES (9, 0, 2);

-- Size-velocity distribution (ID 10): 2D Matrix, two axes
INSERT INTO [dbo].[MetaDataAxis] ([Metadata_ID], [AxisRole], [ValueBinningAxis_ID])
VALUES (10, 0, 2);   -- row axis = particle size
INSERT INTO [dbo].[MetaDataAxis] ([Metadata_ID], [AxisRole], [ValueBinningAxis_ID])
VALUES (10, 1, 3);   -- col axis = velocity

-- =============================================================================
-- ValueVector: UV-Vis spectrum (MetaData ID=7)
-- 7 bins at timestamp 1; 3 bins at timestamp 2 (partial scan, one flagged)
-- =============================================================================

-- Timestamp 1: 2025-09-10T14:00:00 UTC (10:00 EDT)
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (7, '2025-09-10T14:00:00.0000000', 1, 2.85, NULL);
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (7, '2025-09-10T14:00:00.0000000', 2, 2.42, NULL);
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (7, '2025-09-10T14:00:00.0000000', 3, 1.15, NULL);
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (7, '2025-09-10T14:00:00.0000000', 4, 0.45, NULL);
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (7, '2025-09-10T14:00:00.0000000', 5, 0.12, NULL);
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (7, '2025-09-10T14:00:00.0000000', 6, 0.05, NULL);
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (7, '2025-09-10T14:00:00.0000000', 7, 0.02, NULL);

-- Timestamp 2: 2025-09-10T18:00:00 UTC (14:00 EDT) (partial, bin 3 flagged QualityCode=1)
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (7, '2025-09-10T18:00:00.0000000', 1, 3.10, NULL);
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (7, '2025-09-10T18:00:00.0000000', 2, 2.68, NULL);
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (7, '2025-09-10T18:00:00.0000000', 3, 1.35, 1);

-- =============================================================================
-- ValueVector: particle size distribution (MetaData ID=9)
-- 4 size fractions (mg/L) at two timestamps
-- =============================================================================

-- Timestamp 1: 2025-09-10T13:00:00 UTC (09:00 EDT)
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (9, '2025-09-10T13:00:00.0000000', 8,  45.2, NULL);   -- <63 µm
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (9, '2025-09-10T13:00:00.0000000', 9,  28.1, NULL);   -- 63-125 µm
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (9, '2025-09-10T13:00:00.0000000', 10, 12.5, NULL);   -- 125-250 µm
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (9, '2025-09-10T13:00:00.0000000', 11,  5.8, NULL);   -- >250 µm

-- Timestamp 2: 2025-09-10T17:00:00 UTC (13:00 EDT)
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (9, '2025-09-10T17:00:00.0000000', 8,  52.0, NULL);
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (9, '2025-09-10T17:00:00.0000000', 9,  33.4, NULL);
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (9, '2025-09-10T17:00:00.0000000', 10, 15.1, NULL);
INSERT INTO [dbo].[ValueVector] ([Metadata_ID], [Timestamp], [ValueBin_ID], [Value], [QualityCode])
VALUES (9, '2025-09-10T17:00:00.0000000', 11,  7.2, NULL);

-- =============================================================================
-- ValueImage: camera captures at CSO outfall (MetaData ID=8)
-- =============================================================================

INSERT INTO [dbo].[ValueImage] ([Metadata_ID], [Timestamp], [ImageWidth], [ImageHeight], [NumberOfChannels], [ImageFormat], [FileSizeBytes], [StorageBackend], [StoragePath], [Thumbnail], [QualityCode])
VALUES (8, '2025-09-10T16:00:00.0000000', 1920, 1080, 3, 'JPEG', 245760, 'FileSystem', '/images/cso12/2025-09-10_120000.jpg', NULL, NULL);

INSERT INTO [dbo].[ValueImage] ([Metadata_ID], [Timestamp], [ImageWidth], [ImageHeight], [NumberOfChannels], [ImageFormat], [FileSizeBytes], [StorageBackend], [StoragePath], [Thumbnail], [QualityCode])
VALUES (8, '2025-09-10T16:15:00.0000000', 1920, 1080, 3, 'JPEG', 251904, 'FileSystem', '/images/cso12/2025-09-10_121500.jpg', NULL, NULL);

-- =============================================================================
-- ValueMatrix: particle size-velocity joint distribution (MetaData ID=10)
-- 3 size bins (IDs 8-10) x 2 velocity bins (IDs 12-13) at one timestamp
-- Values are particle number concentrations (counts/mL)
-- =============================================================================

INSERT INTO [dbo].[ValueMatrix] ([Metadata_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value], [QualityCode])
VALUES (10, '2025-09-10T13:00:00.0000000', 8,  12, 22.1, NULL);   -- <63 µm,     slow
INSERT INTO [dbo].[ValueMatrix] ([Metadata_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value], [QualityCode])
VALUES (10, '2025-09-10T13:00:00.0000000', 8,  13, 23.1, NULL);   -- <63 µm,     fast
INSERT INTO [dbo].[ValueMatrix] ([Metadata_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value], [QualityCode])
VALUES (10, '2025-09-10T13:00:00.0000000', 9,  12, 15.0, NULL);   -- 63-125 µm,  slow
INSERT INTO [dbo].[ValueMatrix] ([Metadata_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value], [QualityCode])
VALUES (10, '2025-09-10T13:00:00.0000000', 9,  13, 13.1, NULL);   -- 63-125 µm,  fast
INSERT INTO [dbo].[ValueMatrix] ([Metadata_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value], [QualityCode])
VALUES (10, '2025-09-10T13:00:00.0000000', 10, 12,  6.3, NULL);   -- 125-250 µm, slow
INSERT INTO [dbo].[ValueMatrix] ([Metadata_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID], [Value], [QualityCode])
VALUES (10, '2025-09-10T13:00:00.0000000', 10, 13,  6.2, NULL);   -- 125-250 µm, fast
