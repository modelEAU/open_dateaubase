-- Migration: v2.1.1 → v2.1.2
-- Adds AuditLog table for tracking user actions.
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID('dbo.AuditLog') IS NOT NULL
    RAISERROR('AuditLog table already exists.', 16, 1);
GO

BEGIN TRANSACTION;
GO

CREATE TABLE [dbo].[AuditLog] (
    [AuditLog_ID]    BIGINT        IDENTITY(1,1) NOT NULL,
    [UserAccount_ID] INT           NULL,
    [Action]         NVARCHAR(50)  NOT NULL,   -- CREATE | UPDATE | DELETE | LOGIN | SIGNUP
    [ResourceType]   NVARCHAR(100) NOT NULL,   -- e.g. UserAccount, Site, Campaign …
    [ResourceID]     NVARCHAR(255) NULL,        -- PK of the affected row (as string)
    [Details]        NVARCHAR(MAX) NULL,        -- JSON snapshot / diff
    [Timestamp]      DATETIME2(7)  NOT NULL
        CONSTRAINT [DF_AuditLog_Timestamp] DEFAULT SYSUTCDATETIME(),
    CONSTRAINT [PK_AuditLog]            PRIMARY KEY ([AuditLog_ID]),
    CONSTRAINT [FK_AuditLog_UserAccount] FOREIGN KEY ([UserAccount_ID])
        REFERENCES [dbo].[UserAccount] ([UserAccount_ID])
);
GO

CREATE INDEX [IX_AuditLog_UserAccount_ID] ON [dbo].[AuditLog] ([UserAccount_ID]);
CREATE INDEX [IX_AuditLog_Timestamp]      ON [dbo].[AuditLog] ([Timestamp] DESC);
CREATE INDEX [IX_AuditLog_ResourceType]   ON [dbo].[AuditLog] ([ResourceType]);
GO

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedDateTime], [Description], [MigrationScript])
VALUES (
    '2.1.2',
    SYSUTCDATETIME(),
    'Add AuditLog table for CRUD activity tracking',
    'v2.1.1_to_v2.1.2_audit_mssql.sql'
);
GO

COMMIT TRANSACTION;
GO

PRINT 'Migration to v2.1.2 completed successfully.';
