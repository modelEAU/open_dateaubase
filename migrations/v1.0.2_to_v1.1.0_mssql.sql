-- Migration: v1.0.2 -> v1.1.0
-- Platform: mssql
-- Generated: 2026-02-17
-- Rollback: v1.0.2_to_v1.1.0_mssql_rollback.sql

-- ValueType: lookup for measurement shape (Scalar, Vector, Matrix, Image)
CREATE TABLE [dbo].[ValueType] (
    [ValueType_ID] INT IDENTITY(1,1) NOT NULL,
    [ValueType_Name] NVARCHAR(50) NOT NULL,
    CONSTRAINT [PK_ValueType] PRIMARY KEY ([ValueType_ID])
);

-- Seed ValueType lookup data
SET IDENTITY_INSERT [dbo].[ValueType] ON;
INSERT INTO [dbo].[ValueType] ([ValueType_ID], [ValueType_Name]) VALUES (1, 'Scalar');
INSERT INTO [dbo].[ValueType] ([ValueType_ID], [ValueType_Name]) VALUES (2, 'Vector');
INSERT INTO [dbo].[ValueType] ([ValueType_ID], [ValueType_Name]) VALUES (3, 'Matrix');
INSERT INTO [dbo].[ValueType] ([ValueType_ID], [ValueType_Name]) VALUES (4, 'Image');
SET IDENTITY_INSERT [dbo].[ValueType] OFF;

-- ValueBinningAxis: a named measurement axis with a physical unit (e.g. wavelength, particle size, velocity)
CREATE TABLE [dbo].[ValueBinningAxis] (
    [ValueBinningAxis_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Description] NVARCHAR(500),
    [NumberOfBins] INT NOT NULL,
    [Unit_ID] INT NOT NULL,
    CONSTRAINT [PK_ValueBinningAxis] PRIMARY KEY ([ValueBinningAxis_ID])
);

-- ValueBin: individual bin on an axis, defined by a half-open interval [LowerBound, UpperBound)
CREATE TABLE [dbo].[ValueBin] (
    [ValueBin_ID] INT IDENTITY(1,1) NOT NULL,
    [ValueBinningAxis_ID] INT NOT NULL,
    [BinIndex] INT NOT NULL,
    [LowerBound] FLOAT NOT NULL,
    [UpperBound] FLOAT NOT NULL,
    CONSTRAINT [PK_ValueBin] PRIMARY KEY ([ValueBin_ID]),
    CONSTRAINT [UQ_ValueBin_AxisIndex] UNIQUE ([ValueBinningAxis_ID], [BinIndex]),
    CONSTRAINT [CK_ValueBin_Bounds] CHECK ([UpperBound] > [LowerBound])
);

-- MetaDataAxis: junction linking a MetaData series to its binning axis (or axes for 2D)
-- AxisRole 0 = row axis (or single axis for Vector); AxisRole 1 = column axis (Matrix only)
CREATE TABLE [dbo].[MetaDataAxis] (
    [Metadata_ID] INT NOT NULL,
    [AxisRole] INT NOT NULL,
    [ValueBinningAxis_ID] INT NOT NULL,
    CONSTRAINT [PK_MetaDataAxis] PRIMARY KEY ([Metadata_ID], [AxisRole]),
    CONSTRAINT [CK_MetaDataAxis_AxisRole] CHECK ([AxisRole] IN (0, 1))
);

-- ValueVector: 1D binned measurements (spectra, PSDs, any 1D distribution)
CREATE TABLE [dbo].[ValueVector] (
    [Metadata_ID] INT NOT NULL,
    [Timestamp] DATETIME2(7) NOT NULL,
    [ValueBin_ID] INT NOT NULL,
    [Value] FLOAT,
    [QualityCode] INT,
    CONSTRAINT [PK_ValueVector] PRIMARY KEY ([Metadata_ID], [Timestamp], [ValueBin_ID])
);

-- ValueMatrix: 2D binned measurements (joint distributions, e.g. particle size x velocity)
CREATE TABLE [dbo].[ValueMatrix] (
    [Metadata_ID] INT NOT NULL,
    [Timestamp] DATETIME2(7) NOT NULL,
    [RowValueBin_ID] INT NOT NULL,
    [ColValueBin_ID] INT NOT NULL,
    [Value] FLOAT,
    [QualityCode] INT,
    CONSTRAINT [PK_ValueMatrix] PRIMARY KEY ([Metadata_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID])
);

-- ValueImage: image reference metadata (file path, dimensions, format)
CREATE TABLE [dbo].[ValueImage] (
    [ValueImage_ID] BIGINT IDENTITY(1,1) NOT NULL,
    [Metadata_ID] INT NOT NULL,
    [Timestamp] DATETIME2(7) NOT NULL,
    [ImageWidth] INT NOT NULL,
    [ImageHeight] INT NOT NULL,
    [NumberOfChannels] INT NOT NULL DEFAULT 3,
    [ImageFormat] NVARCHAR(20) NOT NULL,
    [FileSizeBytes] BIGINT,
    [StorageBackend] NVARCHAR(50) NOT NULL DEFAULT 'FileSystem',
    [StoragePath] NVARCHAR(1000) NOT NULL,
    [Thumbnail] VARBINARY(MAX),
    [QualityCode] INT,
    CONSTRAINT [PK_ValueImage] PRIMARY KEY ([ValueImage_ID]),
    CONSTRAINT [UQ_ValueImage_MetaTimestamp] UNIQUE ([Metadata_ID], [Timestamp])
);

-- Add ValueType_ID to MetaData (default 1=Scalar for backward compatibility)
ALTER TABLE [dbo].[MetaData] ADD [ValueType_ID] INT NOT NULL DEFAULT 1;

CREATE INDEX [IX_ValueImage_MetaTimestamp] ON [dbo].[ValueImage] ([Metadata_ID], [Timestamp]);

-- Foreign keys: MetaData
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_ValueType]
    FOREIGN KEY ([ValueType_ID]) REFERENCES [dbo].[ValueType] ([ValueType_ID]);

-- Foreign keys: ValueBinningAxis
ALTER TABLE [dbo].[ValueBinningAxis] ADD CONSTRAINT [FK_ValueBinningAxis_Unit]
    FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);

-- Foreign keys: ValueBin
ALTER TABLE [dbo].[ValueBin] ADD CONSTRAINT [FK_ValueBin_ValueBinningAxis]
    FOREIGN KEY ([ValueBinningAxis_ID]) REFERENCES [dbo].[ValueBinningAxis] ([ValueBinningAxis_ID]);

-- Foreign keys: MetaDataAxis
ALTER TABLE [dbo].[MetaDataAxis] ADD CONSTRAINT [FK_MetaDataAxis_MetaData]
    FOREIGN KEY ([Metadata_ID]) REFERENCES [dbo].[MetaData] ([Metadata_ID]);

ALTER TABLE [dbo].[MetaDataAxis] ADD CONSTRAINT [FK_MetaDataAxis_ValueBinningAxis]
    FOREIGN KEY ([ValueBinningAxis_ID]) REFERENCES [dbo].[ValueBinningAxis] ([ValueBinningAxis_ID]);

-- Foreign keys: ValueVector
ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [FK_ValueVector_MetaData]
    FOREIGN KEY ([Metadata_ID]) REFERENCES [dbo].[MetaData] ([Metadata_ID]);

ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [FK_ValueVector_ValueBin]
    FOREIGN KEY ([ValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);

-- Foreign keys: ValueMatrix (two separate FKs to ValueBin with distinct names)
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_MetaData]
    FOREIGN KEY ([Metadata_ID]) REFERENCES [dbo].[MetaData] ([Metadata_ID]);

ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_RowValueBin]
    FOREIGN KEY ([RowValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);

ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_ColValueBin]
    FOREIGN KEY ([ColValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);

-- Foreign keys: ValueImage
ALTER TABLE [dbo].[ValueImage] ADD CONSTRAINT [FK_ValueImage_MetaData]
    FOREIGN KEY ([Metadata_ID]) REFERENCES [dbo].[MetaData] ([Metadata_ID]);

-- Record schema version
INSERT INTO [dbo].[SchemaVersion] ([Version], [Description], [MigrationScript])
VALUES ('1.1.0', 'Phase 1 - Generalized binned value storage (vectors, matrices, images)', 'v1.0.2_to_v1.1.0_mssql.sql');
