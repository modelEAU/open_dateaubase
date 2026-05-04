-- Migration: add ProcessUnit_ID to SamplingPoint
-- Allows a sampling point to be scoped within a specific process unit (tank, zone, etc.)

USE open_dateaubase;
GO

ALTER TABLE [dbo].[SamplingPoint]
    ADD [ProcessUnit_ID] INT NULL;
GO

ALTER TABLE [dbo].[SamplingPoint]
    ADD CONSTRAINT [FK_SamplingPoint_ProcessUnit]
    FOREIGN KEY ([ProcessUnit_ID]) REFERENCES [dbo].[ProcessUnit] ([ProcessUnit_ID]);
GO

PRINT 'Migration applied: SamplingPoint.ProcessUnit_ID added.';

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedDateTime], [Description], [MigrationScript])
VALUES ('4.0.0', SYSUTCDATETIME(), 'Add ProcessUnit_ID to SamplingPoint', 'v4.0.0_add_samplingpoint_processunit.sql');
GO
