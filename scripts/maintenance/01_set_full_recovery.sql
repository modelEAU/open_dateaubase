-- =============================================================================
-- 01_set_full_recovery.sql
-- Run ONCE on the production SQL Server instance before installing backup jobs.
--
-- What this does:
--   1. Switches open_dateaubase to FULL recovery model.
--   2. Takes an immediate full backup to seed the log chain.
--      (With FULL recovery, log backups cannot protect you until at least
--       one full backup exists after the model change.)
--
-- Prerequisites:
--   - C:\Backups\open_dateaubase\full\ must exist on the server.
--   - Run as sysadmin (SA or equivalent).
--
-- After this script:
--   - Run 02_install_backup_jobs.sql to create the scheduled Agent jobs.
-- =============================================================================

USE master;
GO

-- Switch to FULL recovery
ALTER DATABASE [open_dateaubase] SET RECOVERY FULL;
GO

PRINT 'Recovery model set to FULL.';

-- Seed the log chain with an immediate full backup.
-- INIT overwrites any existing file of the same name (safe for a one-time seed).
BACKUP DATABASE [open_dateaubase]
    TO DISK = N'C:\Backups\open_dateaubase\full\open_dateaubase_initial_full.bak'
    WITH NOFORMAT, INIT,
         NAME = N'open_dateaubase Initial Full (recovery model change)',
         COMPRESSION,
         STATS = 10;
GO

PRINT 'Initial full backup complete. Log chain is now active.';
PRINT 'Proceed to 02_install_backup_jobs.sql.';
