-- Migration: v2.2.0 -> v2.3.0
-- Platform: mssql
-- Generated: 2026-07-14 20:55:44 UTC
-- Rollback: v2.2.0_to_v2.3.0_mssql_rollback.sql
--
-- Retires the six cause-named AnnotationKinds (ADR-0007). Existing annotations
-- citing them are remapped onto a surviving verdict first — the DELETE would
-- otherwise fail on FK_Annotation_AnnotationKind_ID. The retired kind's name is
-- prefixed into the Comment so no wording is lost; the surviving IDs are not
-- renumbered, so 1/2/3/5/6/11 stay burned.

UPDATE a
SET a.[AnnotationKind_ID] = m.[NewKind],
    a.[Comment] = N'[' + m.[OldName] + N'] ' + ISNULL(a.[Comment], N'')
FROM [dbo].[Annotation] a
JOIN (VALUES
    (1,  7, N'Fault'),               -- -> Data Quality; the fault itself is an Event
    (2,  7, N'Maintenance'),         -- -> Data Quality; the maintenance is an Event
    (3,  7, N'Calibration Period'),  -- -> Data Quality; the calibration is an Event
    (5,  8, N'Experiment'),          -- -> Note; provenance, not a verdict
    (6,  8, N'Process Event'),       -- -> Note; the process event is an Event
    (11, 8, N'Equipment Relocation') -- -> Note; the move is EquipmentLocationHistory
) AS m([OldKind], [NewKind], [OldName])
    ON a.[AnnotationKind_ID] = m.[OldKind];

DELETE FROM [dbo].[AnnotationKind] WHERE [AnnotationKind_ID] IN (1, 2, 3, 5, 6, 11);

-- Surviving verdicts: descriptions rewritten so Anomaly visibly absorbs the
-- "something happened here I can't explain" case and Data Quality points at the
-- Event link for the why. Colors are unchanged — the five are distinguishable.
UPDATE [dbo].[AnnotationKind]
SET [Description] = N'Unexplained behaviour — something happened here that no known event accounts for'
WHERE [AnnotationKind_ID] = 4;

UPDATE [dbo].[AnnotationKind]
SET [Description] = N'Suspect data quality (drift, fouling); cite the Event that caused it if known'
WHERE [AnnotationKind_ID] = 7;

INSERT INTO [dbo].[SchemaVersion] ([Version], [Description]) VALUES (N'2.3.0', N'Retires the six cause-named AnnotationKinds (Fault, Maintenance, Calibration Period, Experiment, Process Event, Equipment Relocation), leaving five verdicts about the data: Anomaly, Data Quality, Note, Exclusion, Confirmed. Causes belong in EventKind; an annotation names what is wrong with the data, never why. See ADR-0007 and migrations/v2.2.0_to_v2.3.0_mssql.sql, which remaps existing rows onto a survivor before deleting the retired kinds.');
