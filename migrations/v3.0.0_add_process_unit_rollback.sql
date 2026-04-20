-- Rollback: remove ProcessUnit hierarchy and ProcessUnitType lookup

ALTER TABLE [dbo].[SamplingPoint] DROP CONSTRAINT [FK_SamplingPoint_ProcessUnit];

GO

ALTER TABLE [dbo].[SamplingPoint] DROP COLUMN [ProcessUnit_ID];

GO

DROP TABLE [dbo].[ProcessUnit];

GO

DROP TABLE [dbo].[ProcessUnitType];

GO
