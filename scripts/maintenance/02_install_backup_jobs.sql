-- =============================================================================
-- 02_install_backup_jobs.sql
-- Creates four SQL Server Agent jobs for open_dateaubase backup maintenance.
--
-- Jobs created:
--   1. open_dateaubase - Full Backup        (weekly, Sunday 02:00)
--   2. open_dateaubase - Differential Backup (daily Mon–Sat 02:00)
--   3. open_dateaubase - Log Backup          (every 4 hours)
--   4. open_dateaubase - Backup Cleanup      (daily 03:00, enforces retention)
--
-- Retention policy:
--   - Full backups:  28 days (4 × weekly)
--   - Diff backups:  14 days
--   - Log backups:    7 days
--
-- Prerequisites:
--   - Run 01_set_full_recovery.sql first.
--   - SQL Server Agent service must be running.
--   - C:\Backups\ must exist; this script creates the subdirectories.
--   - Run as sysadmin.
--
-- Idempotent: existing jobs with these names are dropped and recreated.
-- =============================================================================

USE msdb;
GO

-- =============================================================================
-- 0. Create backup directory structure
-- =============================================================================
EXEC master.dbo.xp_create_subdir N'C:\Backups\open_dateaubase\full';
EXEC master.dbo.xp_create_subdir N'C:\Backups\open_dateaubase\diff';
EXEC master.dbo.xp_create_subdir N'C:\Backups\open_dateaubase\log';
PRINT 'Backup directories verified/created.';
GO

-- =============================================================================
-- Helper: drop a job by name if it already exists
-- =============================================================================
IF OBJECT_ID('tempdb..#DropJobIfExists') IS NOT NULL DROP PROCEDURE #DropJobIfExists;
GO
CREATE PROCEDURE #DropJobIfExists @job_name NVARCHAR(128)
AS
BEGIN
    IF EXISTS (SELECT 1 FROM msdb.dbo.sysjobs WHERE name = @job_name)
    BEGIN
        EXEC msdb.dbo.sp_delete_job @job_name = @job_name, @delete_unused_schedule = 1;
        PRINT 'Dropped existing job: ' + @job_name;
    END
END;
GO

-- =============================================================================
-- JOB 1: Weekly Full Backup — every Sunday at 02:00
-- =============================================================================
EXEC #DropJobIfExists N'open_dateaubase - Full Backup';
GO

DECLARE @job_id UNIQUEIDENTIFIER;

EXEC msdb.dbo.sp_add_job
    @job_name        = N'open_dateaubase - Full Backup',
    @enabled         = 1,
    @description     = N'Weekly full backup of open_dateaubase to C:\Backups\open_dateaubase\full\',
    @category_name   = N'[Uncategorized (Local)]',
    @notify_level_eventlog = 2,  -- log on failure
    @job_id          = @job_id OUTPUT;

EXEC msdb.dbo.sp_add_jobstep
    @job_id          = @job_id,
    @step_name       = N'Full Backup',
    @step_id         = 1,
    @subsystem       = N'TSQL',
    @database_name   = N'master',
    @command         = N'
DECLARE @filename NVARCHAR(500) =
    N''C:\Backups\open_dateaubase\full\open_dateaubase_full_''
    + REPLACE(REPLACE(CONVERT(NVARCHAR(20), GETDATE(), 120), '' '', ''_''), '':'', '''')
    + N''.bak'';

BACKUP DATABASE [open_dateaubase]
    TO DISK = @filename
    WITH NOFORMAT, NOINIT,
         NAME = N''open_dateaubase Weekly Full'',
         COMPRESSION,
         STATS = 10;

PRINT ''Full backup written to: '' + @filename;
',
    @on_success_action = 1,  -- quit with success
    @on_fail_action    = 2;  -- quit with failure

EXEC msdb.dbo.sp_add_schedule
    @schedule_name          = N'open_dateaubase Full Backup Schedule',
    @freq_type              = 8,        -- weekly
    @freq_interval          = 1,        -- Sunday (bit 1)
    @freq_recurrence_factor = 1,        -- every week (required for weekly schedules)
    @freq_subday_type       = 1,        -- once
    @active_start_time      = 020000;   -- 02:00:00

EXEC msdb.dbo.sp_attach_schedule
    @job_id        = @job_id,
    @schedule_name = N'open_dateaubase Full Backup Schedule';

EXEC msdb.dbo.sp_add_jobserver
    @job_id      = @job_id,
    @server_name = @@SERVERNAME;

PRINT 'Job created: open_dateaubase - Full Backup';
GO

-- =============================================================================
-- JOB 2: Daily Differential Backup — Mon–Sat at 02:00
-- =============================================================================
EXEC #DropJobIfExists N'open_dateaubase - Differential Backup';
GO

DECLARE @job_id UNIQUEIDENTIFIER;

EXEC msdb.dbo.sp_add_job
    @job_name        = N'open_dateaubase - Differential Backup',
    @enabled         = 1,
    @description     = N'Daily differential backup of open_dateaubase (Mon–Sat) to C:\Backups\open_dateaubase\diff\',
    @category_name   = N'[Uncategorized (Local)]',
    @notify_level_eventlog = 2,
    @job_id          = @job_id OUTPUT;

EXEC msdb.dbo.sp_add_jobstep
    @job_id          = @job_id,
    @step_name       = N'Differential Backup',
    @step_id         = 1,
    @subsystem       = N'TSQL',
    @database_name   = N'master',
    @command         = N'
DECLARE @filename NVARCHAR(500) =
    N''C:\Backups\open_dateaubase\diff\open_dateaubase_diff_''
    + REPLACE(REPLACE(CONVERT(NVARCHAR(20), GETDATE(), 120), '' '', ''_''), '':'', '''')
    + N''.bak'';

BACKUP DATABASE [open_dateaubase]
    TO DISK = @filename
    WITH DIFFERENTIAL, NOFORMAT, NOINIT,
         NAME = N''open_dateaubase Daily Differential'',
         COMPRESSION,
         STATS = 10;

PRINT ''Differential backup written to: '' + @filename;
',
    @on_success_action = 1,
    @on_fail_action    = 2;

-- freq_interval for weekly type: bitmask of days Sun=1, Mon=2, Tue=4, Wed=8, Thu=16, Fri=32, Sat=64
-- Mon–Sat = 2+4+8+16+32+64 = 126
EXEC msdb.dbo.sp_add_schedule
    @schedule_name          = N'open_dateaubase Differential Backup Schedule',
    @freq_type              = 8,        -- weekly
    @freq_interval          = 126,      -- Mon–Sat
    @freq_recurrence_factor = 1,        -- every week (required for weekly schedules)
    @freq_subday_type       = 1,        -- once per day
    @active_start_time      = 020000;   -- 02:00:00

EXEC msdb.dbo.sp_attach_schedule
    @job_id        = @job_id,
    @schedule_name = N'open_dateaubase Differential Backup Schedule';

EXEC msdb.dbo.sp_add_jobserver
    @job_id      = @job_id,
    @server_name = @@SERVERNAME;

PRINT 'Job created: open_dateaubase - Differential Backup';
GO

-- =============================================================================
-- JOB 3: Transaction Log Backup — every 4 hours
--
-- IMPORTANT: With FULL recovery model, transaction logs grow until they are
-- backed up. This job prevents unbounded log file growth and enables
-- point-in-time restore (RPO ≤ 4 hours). Adjust @freq_subday_interval if a
-- shorter RPO window is required.
-- =============================================================================
EXEC #DropJobIfExists N'open_dateaubase - Log Backup';
GO

DECLARE @job_id UNIQUEIDENTIFIER;

EXEC msdb.dbo.sp_add_job
    @job_name        = N'open_dateaubase - Log Backup',
    @enabled         = 1,
    @description     = N'Transaction log backup every 4 hours. Required with FULL recovery to prevent log growth.',
    @category_name   = N'[Uncategorized (Local)]',
    @notify_level_eventlog = 2,
    @job_id          = @job_id OUTPUT;

EXEC msdb.dbo.sp_add_jobstep
    @job_id          = @job_id,
    @step_name       = N'Log Backup',
    @step_id         = 1,
    @subsystem       = N'TSQL',
    @database_name   = N'master',
    @command         = N'
DECLARE @filename NVARCHAR(500) =
    N''C:\Backups\open_dateaubase\log\open_dateaubase_log_''
    + REPLACE(REPLACE(CONVERT(NVARCHAR(20), GETDATE(), 120), '' '', ''_''), '':'', '''')
    + N''.trn'';

BACKUP LOG [open_dateaubase]
    TO DISK = @filename
    WITH NOFORMAT, NOINIT,
         NAME = N''open_dateaubase Log Backup'',
         COMPRESSION,
         STATS = 10;

PRINT ''Log backup written to: '' + @filename;
',
    @on_success_action = 1,
    @on_fail_action    = 2;

EXEC msdb.dbo.sp_add_schedule
    @schedule_name        = N'open_dateaubase Log Backup Schedule',
    @freq_type            = 4,     -- daily
    @freq_interval        = 1,     -- every day (required for daily schedules)
    @freq_subday_type     = 8,     -- hours
    @freq_subday_interval = 4,     -- every 4 hours
    @active_start_time    = 000000; -- starting at midnight

EXEC msdb.dbo.sp_attach_schedule
    @job_id        = @job_id,
    @schedule_name = N'open_dateaubase Log Backup Schedule';

EXEC msdb.dbo.sp_add_jobserver
    @job_id      = @job_id,
    @server_name = @@SERVERNAME;

PRINT 'Job created: open_dateaubase - Log Backup';
GO

-- =============================================================================
-- JOB 4: Backup Cleanup — daily at 03:00
-- Deletes backup files older than the retention thresholds.
-- =============================================================================
EXEC #DropJobIfExists N'open_dateaubase - Backup Cleanup';
GO

DECLARE @job_id UNIQUEIDENTIFIER;

EXEC msdb.dbo.sp_add_job
    @job_name        = N'open_dateaubase - Backup Cleanup',
    @enabled         = 1,
    @description     = N'Deletes old backup files: full >28d, diff >14d, log >7d.',
    @category_name   = N'[Uncategorized (Local)]',
    @notify_level_eventlog = 2,
    @job_id          = @job_id OUTPUT;

EXEC msdb.dbo.sp_add_jobstep
    @job_id          = @job_id,
    @step_name       = N'Delete old backups',
    @step_id         = 1,
    @subsystem       = N'TSQL',
    @database_name   = N'master',
    @command         = N'
-- Full backups: keep 28 days (4 weeklies)
DECLARE @cutoff_full  NVARCHAR(20) = CONVERT(NVARCHAR(20), DATEADD(day, -28, GETDATE()), 120);
DECLARE @cutoff_diff  NVARCHAR(20) = CONVERT(NVARCHAR(20), DATEADD(day, -14, GETDATE()), 120);
DECLARE @cutoff_log   NVARCHAR(20) = CONVERT(NVARCHAR(20), DATEADD(day,  -7, GETDATE()), 120);

EXEC master.sys.xp_delete_file 0, N''C:\Backups\open_dateaubase\full\'', N''bak'', @cutoff_full;
EXEC master.sys.xp_delete_file 0, N''C:\Backups\open_dateaubase\diff\'', N''bak'', @cutoff_diff;
EXEC master.sys.xp_delete_file 0, N''C:\Backups\open_dateaubase\log\'',  N''trn'', @cutoff_log;

-- Also purge old backup history from msdb (keeps the system table lean)
EXEC msdb.dbo.sp_delete_backuphistory @oldest_date = DATEADD(day, -28, GETDATE());

PRINT ''Cleanup complete.'';
',
    @on_success_action = 1,
    @on_fail_action    = 2;

EXEC msdb.dbo.sp_add_schedule
    @schedule_name     = N'open_dateaubase Backup Cleanup Schedule',
    @freq_type         = 4,        -- daily
    @freq_interval     = 1,        -- every day (required for daily schedules)
    @freq_subday_type  = 1,        -- once
    @active_start_time = 030000;   -- 03:00:00

EXEC msdb.dbo.sp_attach_schedule
    @job_id        = @job_id,
    @schedule_name = N'open_dateaubase Backup Cleanup Schedule';

EXEC msdb.dbo.sp_add_jobserver
    @job_id      = @job_id,
    @server_name = @@SERVERNAME;

PRINT 'Job created: open_dateaubase - Backup Cleanup';
GO

-- Cleanup temp procedure
DROP PROCEDURE #DropJobIfExists;
GO

PRINT '';
PRINT '=== All 4 backup jobs installed successfully. ===';
PRINT 'Next step: run 03_verify_backup_jobs.sql, then test each job manually via SSMS.';
