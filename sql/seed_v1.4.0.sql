-- Seed data for schema v1.4.0
-- Phase 2c: Sensor Lifecycle Tracking
--
-- Prerequisites: seed_v1.3.0.sql must have been applied.
-- References: Equipment_ID=1, Sampling_point_ID=1, Person records,
--             Campaign_ID=1, MetaData entries from earlier seeds.
--
-- We record a calibration event for Equipment_ID=1 and link it to
-- both a sensor MetaData series and a lab MetaData series via EquipmentEventMetaData.

-- Calibration event
INSERT INTO [dbo].[EquipmentEvent] (
    [Equipment_ID], [EquipmentEventType_ID], [EventDateTimeStart], [EventDateTimeEnd],
    [Campaign_ID], [Notes]
)
VALUES (
    1,   -- Equipment_ID (sensor installed at sampling point)
    1,   -- EquipmentEventType_ID = Calibration
    '2025-03-15T08:00:00',
    '2025-03-15T09:00:00',
    1,   -- Campaign_ID (Ongoing Operations 2025)
    'Routine TSS calibration using derived standard'
);
GO

-- Installation record: sensor deployed at sampling point 1
INSERT INTO [dbo].[EquipmentInstallation] (
    [Equipment_ID], [Sampling_point_ID], [InstalledDate], [Campaign_ID], [Notes]
)
VALUES (
    1,
    1,
    '2025-01-10T07:30:00',
    1,
    'Initial deployment for 2025 operations campaign'
);
GO
