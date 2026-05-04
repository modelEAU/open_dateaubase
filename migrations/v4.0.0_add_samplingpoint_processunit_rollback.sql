-- Rollback: remove ProcessUnit_ID from SamplingPoint

USE open_dateaubase;
GO

ALTER TABLE [dbo].[SamplingPoint]
    DROP CONSTRAINT [FK_SamplingPoint_ProcessUnit];
GO

ALTER TABLE [dbo].[SamplingPoint]
    DROP COLUMN [ProcessUnit_ID];
GO

PRINT 'Rollback applied: SamplingPoint.ProcessUnit_ID removed.';
