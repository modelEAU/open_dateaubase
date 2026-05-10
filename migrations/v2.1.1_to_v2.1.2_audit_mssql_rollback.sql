-- Migration rollback: v2.1.2 → v2.1.1
-- Drops AuditLog table added in v2.1.2.
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET QUOTED_IDENTIFIER ON;
GO

BEGIN TRANSACTION;

IF OBJECT_ID('dbo.AuditLog', 'U') IS NOT NULL
    DROP TABLE dbo.AuditLog;
GO

COMMIT TRANSACTION;
GO

PRINT 'Rollback of v2.1.2 (audit) completed successfully.';
