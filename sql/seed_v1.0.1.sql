-- Seed data for schema v1.0.1
-- Records baseline and current version in the new SchemaVersion table

INSERT INTO [dbo].[SchemaVersion] ([Version], [Description], [MigrationScript])
VALUES ('1.0.0', 'Original baseline schema', NULL);

INSERT INTO [dbo].[SchemaVersion] ([Version], [Description], [MigrationScript])
VALUES ('1.0.1', 'Added SchemaVersion tracking table', 'v1.0.0_to_v1.0.1_mssql.sql');
