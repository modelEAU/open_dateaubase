-- Migration: v1.2.0 -> v1.1.0 (ROLLBACK)
-- Platform: mssql
-- Reverses: v1.1.0_to_v1.2.0_mssql.sql

-- ============================================================
-- Reverse Task 2a.3: Remove new MetaData columns and DataProvenance table
-- ============================================================

ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Campaign];
GO
ALTER TABLE [dbo].[MetaData] DROP COLUMN [Campaign_ID];
GO
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_DataProvenance];
GO
ALTER TABLE [dbo].[MetaData] DROP COLUMN [DataProvenance_ID];
GO
DROP TABLE [dbo].[DataProvenance];
GO

-- ============================================================
-- Reverse Task 2a.2: Drop Campaign and CampaignType tables
-- ============================================================

DROP TABLE [dbo].[Campaign];
GO
DROP TABLE [dbo].[CampaignType];
GO

-- ============================================================
-- Reverse Task 2a.1: Rename Person → Contact, restore columns
-- ============================================================

-- Drop FKs pointing to Person
ALTER TABLE [dbo].[MetaData] DROP CONSTRAINT [FK_MetaData_Person];
GO
ALTER TABLE [dbo].[ProjectHasContact] DROP CONSTRAINT [FK_ProjectHasContact_Person];
GO

-- Drop PK
ALTER TABLE [dbo].[Person] DROP CONSTRAINT [PK_Person];
GO

-- Rename column Person_ID → Contact_ID
EXEC sp_rename 'dbo.Person.Person_ID', 'Contact_ID', 'COLUMN';
GO

-- Rename column Role → Status
EXEC sp_rename 'dbo.Person.Role', 'Status', 'COLUMN';
GO

-- Rename table Person → Contact
EXEC sp_rename 'dbo.Person', 'Contact';
GO

-- Re-add PK
ALTER TABLE [dbo].[Contact]
    ADD CONSTRAINT [PK_Contact] PRIMARY KEY ([Contact_ID]);
GO

-- Re-add dropped columns (NULL — original data is lost, structure only)
ALTER TABLE [dbo].[Contact] ADD [Skype_name] NVARCHAR(100) NULL;
ALTER TABLE [dbo].[Contact] ADD [Street_number] NVARCHAR(100) NULL;
ALTER TABLE [dbo].[Contact] ADD [Street_name] NVARCHAR(100) NULL;
ALTER TABLE [dbo].[Contact] ADD [City] NVARCHAR(255) NULL;
ALTER TABLE [dbo].[Contact] ADD [Zip_code] NVARCHAR(45) NULL;
ALTER TABLE [dbo].[Contact] ADD [Country] NVARCHAR(255) NULL;
ALTER TABLE [dbo].[Contact] ADD [Office_number] NVARCHAR(100) NULL;
GO

-- Re-add FK constraints pointing to Contact.Contact_ID
ALTER TABLE [dbo].[MetaData]
    ADD CONSTRAINT [FK_MetaData_Contact]
    FOREIGN KEY ([Contact_ID]) REFERENCES [dbo].[Contact] ([Contact_ID]);
GO

ALTER TABLE [dbo].[ProjectHasContact]
    ADD CONSTRAINT [FK_ProjectHasContact_Contact]
    FOREIGN KEY ([Contact_ID]) REFERENCES [dbo].[Contact] ([Contact_ID]);
GO

-- ============================================================
-- Update SchemaVersion
-- ============================================================

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = '1.2.0';
GO
