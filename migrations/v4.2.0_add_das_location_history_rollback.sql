-- Rollback for v4.2.0_add_das_location_history.sql

DROP INDEX IF EXISTS [IX_DASLocationHistory_Site_ValidFrom] ON [dbo].[DASLocationHistory];
DROP INDEX IF EXISTS [UQ_DASLocationHistory_ActivePerDAS]   ON [dbo].[DASLocationHistory];
DROP TABLE IF EXISTS [dbo].[DASLocationHistory];
