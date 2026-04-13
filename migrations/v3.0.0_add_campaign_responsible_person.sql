-- Migration: add ResponsiblePerson_ID nullable FK column to Campaign
ALTER TABLE [dbo].[Campaign]
    ADD [ResponsiblePerson_ID] INT NULL;

GO

ALTER TABLE [dbo].[Campaign]
    ADD CONSTRAINT [FK_Campaign_Person]
    FOREIGN KEY ([ResponsiblePerson_ID])
    REFERENCES [dbo].[Person] ([Person_ID]);

GO
