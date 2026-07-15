-- Migration: v2.3.0 -> v2.2.0 (ROLLBACK)
-- Platform: mssql
-- Generated: 2026-07-14 20:55:44 UTC
--
-- Restores the six retired AnnotationKind rows and the two rewritten
-- descriptions. It does NOT re-point remapped annotations: the forward
-- migration prefixed the retired kind's name into the Comment, so the original
-- kind is recoverable by hand, but rows are left on their survivor kind.

DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'2.3.0';

-- AnnotationKind
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (1, N'Fault', N'Sensor or process fault', N'#FF4444');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (2, N'Maintenance', N'Sensor under maintenance', N'#FFA500');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (3, N'Calibration Period', N'Data during calibration — may be invalid', N'#FFD700');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (5, N'Experiment', N'Data collected for a specific experiment', N'#4488FF');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (6, N'Process Event', N'Known process event (storm, dosing, etc.)', N'#44BB44');
INSERT INTO [dbo].[AnnotationKind] ([AnnotationKind_ID], [Name], [Description], [Color]) VALUES (11, N'Equipment Relocation', N'Equipment was physically moved to a new location', N'#8888FF');

UPDATE [dbo].[AnnotationKind]
SET [Description] = N'Unexpected behavior, needs investigation'
WHERE [AnnotationKind_ID] = 4;

UPDATE [dbo].[AnnotationKind]
SET [Description] = N'Suspect data quality (drift, fouling)'
WHERE [AnnotationKind_ID] = 7;
