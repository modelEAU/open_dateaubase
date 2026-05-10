-- Migration: v2.1.0 → v2.1.1
-- Adds User and authentication tables for the open_datEAUbase API.
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID('dbo.UserAccount') IS NOT NULL
    RAISERROR('UserAccount table already exists.', 16, 1);
GO

BEGIN TRANSACTION;
GO

CREATE TABLE [dbo].[UserAccount] (
    [UserAccount_ID] INT IDENTITY(1,1) NOT NULL,
    [Email]          NVARCHAR(255) NOT NULL,
    [FullName]       NVARCHAR(255) NOT NULL,
    [PasswordHash]   NVARCHAR(255) NOT NULL,
    [IsActive]       BIT NOT NULL CONSTRAINT [DF_UserAccount_IsActive] DEFAULT 1,
    [IsVerified]     BIT NOT NULL CONSTRAINT [DF_UserAccount_IsVerified] DEFAULT 1,
    [CreatedAt]      DATETIME2(7) NOT NULL CONSTRAINT [DF_UserAccount_CreatedAt] DEFAULT SYSUTCDATETIME(),
    [UpdatedAt]      DATETIME2(7) NOT NULL CONSTRAINT [DF_UserAccount_UpdatedAt] DEFAULT SYSUTCDATETIME(),
    CONSTRAINT [PK_UserAccount] PRIMARY KEY ([UserAccount_ID]),
    CONSTRAINT [UQ_UserAccount_Email] UNIQUE ([Email])
);
GO

CREATE INDEX [IX_UserAccount_Email] ON [dbo].[UserAccount] ([Email]);
GO

INSERT INTO [dbo].[SchemaVersion] ([Version], [AppliedDateTime], [Description], [MigrationScript])
VALUES (
    '2.1.1',
    SYSUTCDATETIME(),
    'Add UserAccount table for application authentication',
    'v2.1.0_to_v2.1.1_auth_mssql.sql'
);
GO

COMMIT TRANSACTION;
GO

PRINT 'Migration to v2.1.1 completed successfully.';
