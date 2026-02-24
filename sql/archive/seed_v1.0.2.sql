-- Seed data for schema v1.0.2
-- New Value rows using DATETIME2 timestamps (UTC by convention)
-- Original measurements were in local time (EDT/EST); times converted to UTC here.

-- TSS at WWTP inlet (Metadata_ID=1), summer 2025 measurements (EDT = UTC-4, converted to UTC)
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 1, 145.2, 4, '2025-06-15T12:00:00.0000000');   -- ID 19 (08:00 EDT → 12:00 UTC)

INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 1, 160.8, 5, '2025-06-15T18:30:00.0000000');   -- ID 20 (14:30 EDT → 18:30 UTC)

-- COD composite (Metadata_ID=2), already UTC
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 2, 395.0, 3, '2025-06-15T00:00:00.0000000');   -- ID 21

-- pH reading (Metadata_ID=3), winter 2025 (EST = UTC-5, converted to UTC)
INSERT INTO [dbo].[Value] ([Comment_ID], [Metadata_ID], [Value], [Number_of_experiment], [Timestamp])
VALUES (NULL, 3, 7.05, 5, '2025-12-01T15:00:00.0000000');    -- ID 22 (10:00 EST → 15:00 UTC)
