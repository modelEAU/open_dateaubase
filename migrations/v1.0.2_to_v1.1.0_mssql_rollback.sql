-- Migration: v1.1.0 -> v1.0.2 (ROLLBACK)
-- Platform: mssql
-- Generated: 2026-02-17

-- Remove schema version record
DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = '1.1.0';

-- Drop foreign keys in reverse dependency order

-- ValueImage
ALTER TABLE [dbo].[ValueImage] DROP CONSTRAINT [FK_ValueImage_MetaData];

-- ValueMatrix
ALTER TABLE [dbo].[ValueMatrix] DROP CONSTRAINT [FK_ValueMatrix_ColValueBin];
ALTER TABLE [dbo].[ValueMatrix] DROP CONSTRAINT [FK_ValueMatrix_RowValueBin];
ALTER TABLE [dbo].[ValueMatrix] DROP CONSTRAINT [FK_ValueMatrix_MetaData];

-- ValueVector
ALTER TABLE [dbo].[ValueVector] DROP CONSTRAINT [FK_ValueVector_ValueBin];
ALTER TABLE [dbo].[ValueVector] DROP CONSTRAINT [FK_ValueVector_MetaData];

-- MetaDataAxis
ALTER TABLE [dbo].[MetaDataAxis] DROP CONSTRAINT [FK_MetaDataAxis_ValueBinningAxis];
ALTER TABLE [dbo].[MetaDataAxis] DROP CONSTRAINT [FK_MetaDataAxis_MetaData];

-- ValueBin
ALTER TABLE [dbo].[ValueBin] DROP CONSTRAINT [FK_ValueBin_ValueBinningAxis];

-- ValueBinningAxis
ALTER TABLE [dbo].[ValueBinningAxis] DROP CONSTRAINT [FK_ValueBinningAxis_Unit];

-- MetaData
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_ValueType];

DROP INDEX [IX_ValueImage_MetaTimestamp] ON [dbo].[ValueImage];

-- Drop the default constraint on ValueType_ID before dropping the column
DECLARE @DF_Name NVARCHAR(200);
SELECT @DF_Name = dc.name
FROM sys.default_constraints dc
JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
WHERE OBJECT_NAME(dc.parent_object_id) = 'MetaData' AND c.name = 'ValueType_ID';
IF @DF_Name IS NOT NULL
    EXEC('ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [' + @DF_Name + ']');

ALTER TABLE [dbo].[MetaData] DROP COLUMN [ValueType_ID];

-- Drop tables in reverse FK-safe order
DROP TABLE [dbo].[ValueMatrix];
DROP TABLE [dbo].[ValueVector];
DROP TABLE [dbo].[ValueImage];
DROP TABLE [dbo].[MetaDataAxis];
DROP TABLE [dbo].[ValueBin];
DROP TABLE [dbo].[ValueBinningAxis];
DROP TABLE [dbo].[ValueType];
