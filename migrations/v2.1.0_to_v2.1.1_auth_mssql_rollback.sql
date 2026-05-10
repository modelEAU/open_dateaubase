-- Migration rollback: v2.1.1 → v2.1.0
-- Drops User and authentication tables added in v2.1.1.
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET QUOTED_IDENTIFIER ON;
GO

BEGIN TRANSACTION;

IF OBJECT_ID('dbo.[User]', 'U') IS NOT NULL
    DROP TABLE dbo.[User];
GO

COMMIT TRANSACTION;
GO

PRINT 'Rollback of v2.1.1 (auth) completed successfully.';
