-- =============================================================================
-- 03_verify_backup_jobs.sql
-- Run after 02_install_backup_jobs.sql to confirm jobs are installed,
-- and again after manual test runs to confirm they succeeded.
--
-- run_status values: 0=Failed, 1=Succeeded, 2=Retry, 3=Cancelled
-- =============================================================================

USE msdb;
GO

-- -----------------------------------------------------------------------------
-- 1. Job existence and enabled state
-- -----------------------------------------------------------------------------
PRINT '--- Job status ---';

SELECT
    j.name                              AS job_name,
    CASE j.enabled WHEN 1 THEN 'YES' ELSE 'NO' END AS enabled,
    CASE j.notify_level_eventlog
        WHEN 0 THEN 'Never'
        WHEN 1 THEN 'On success'
        WHEN 2 THEN 'On failure'
        WHEN 3 THEN 'Always'
    END                                 AS log_on
FROM msdb.dbo.sysjobs j
WHERE j.name LIKE 'open_dateaubase%'
ORDER BY j.name;

-- -----------------------------------------------------------------------------
-- 2. Last run outcome for each job (most recent execution only)
-- -----------------------------------------------------------------------------
PRINT '--- Last run outcome ---';

SELECT
    j.name                              AS job_name,
    h.run_date,                         -- YYYYMMDD
    h.run_time,                         -- HHMMSS
    CASE h.run_status
        WHEN 0 THEN 'FAILED'
        WHEN 1 THEN 'Succeeded'
        WHEN 2 THEN 'Retry'
        WHEN 3 THEN 'Cancelled'
    END                                 AS outcome,
    h.run_duration,                     -- HHMMSS
    LEFT(h.message, 200)                AS message
FROM msdb.dbo.sysjobs j
LEFT JOIN msdb.dbo.sysjobhistory h
    ON  j.job_id   = h.job_id
    AND h.step_id  = 0  -- step 0 = overall job outcome (not individual steps)
    AND h.instance_id = (
        SELECT MAX(h2.instance_id)
        FROM msdb.dbo.sysjobhistory h2
        WHERE h2.job_id = j.job_id AND h2.step_id = 0
    )
WHERE j.name LIKE 'open_dateaubase%'
ORDER BY j.name;

-- -----------------------------------------------------------------------------
-- 3. Upcoming scheduled run times
-- -----------------------------------------------------------------------------
PRINT '--- Next scheduled runs ---';

SELECT
    j.name                              AS job_name,
    CONVERT(NVARCHAR(10), ja.next_run_date) AS next_run_date,
    ja.next_run_time
FROM msdb.dbo.sysjobs j
JOIN msdb.dbo.sysjobactivity ja ON j.job_id = ja.job_id
WHERE j.name LIKE 'open_dateaubase%'
  AND ja.session_id = (SELECT MAX(session_id) FROM msdb.dbo.sysjobactivity)
ORDER BY j.name;

-- -----------------------------------------------------------------------------
-- 4. Recent backup history (confirms actual backups landed on disk)
-- -----------------------------------------------------------------------------
PRINT '--- Recent backup history (last 7 days) ---';

SELECT TOP 20
    b.database_name,
    CASE b.type
        WHEN 'D' THEN 'Full'
        WHEN 'I' THEN 'Differential'
        WHEN 'L' THEN 'Log'
    END                                 AS backup_type,
    b.backup_start_date,
    b.backup_finish_date,
    CAST(b.backup_size / 1048576.0 AS DECIMAL(10,1)) AS size_mb,
    bmf.physical_device_name           AS backup_file
FROM msdb.dbo.backupset b
JOIN msdb.dbo.backupmediafamily bmf ON b.media_set_id = bmf.media_set_id
WHERE b.database_name = 'open_dateaubase'
  AND b.backup_start_date >= DATEADD(day, -7, GETDATE())
ORDER BY b.backup_start_date DESC;
