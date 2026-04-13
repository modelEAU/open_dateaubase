-- Rollback: remove ResponsiblePerson_ID from Campaign
ALTER TABLE [dbo].[Campaign]
    DROP CONSTRAINT [FK_Campaign_Person];

GO

ALTER TABLE [dbo].[Campaign]
    DROP COLUMN [ResponsiblePerson_ID];

GO
