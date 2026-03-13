-- ============================================================
-- Importer test fixtures (seed_importer_fixtures.sql)
-- Equipment, parameters, and equipment models required by the
-- docker/import-test-data.yaml configuration so that
-- `docker compose run --rm importer` succeeds on a fresh DB.
-- ============================================================

SET NOCOUNT ON;

-- Equipment models (IDs 4-5, appended after the 3 in seed_v2.1.0.sql)
INSERT INTO [dbo].[EquipmentModel] ([EquipmentModel], [Method], [Functions], [Manufacturer], [ManualLocation])
VALUES (N'Rodtox R300', N'Respirometry', N'Biological toxicity test via DO consumption rate', N'LAR Process Analysers', NULL);  -- ID 4

INSERT INTO [dbo].[EquipmentModel] ([EquipmentModel], [Method], [Functions], [Manufacturer], [ManualLocation])
VALUES (N'TurbR300 Basestation', N'Optical nephelometry', N'Continuous online turbidity monitoring', N'LAR Process Analysers', NULL);  -- ID 5

-- Parameters (IDs 8-9, appended after 7 in seed_v2.1.0.sql)
INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description])
VALUES (1, N'Dissolved oxygen', N'Dissolved oxygen concentration in water');  -- ID 8

INSERT INTO [dbo].[Parameter] ([Unit_ID], [Parameter], [Description])
VALUES (2, N'Turbidity', N'Water turbidity measured by nephelometry');  -- ID 9

-- Equipment (auto IDs 6-7; ID 5 is ldo345 from seed_explore.sql)
-- Resolved by Identifier name in the importer, so IDs do not matter.
INSERT INTO [dbo].[Equipment] ([EquipmentModel_ID], [Identifier], [SerialNumber], [Owner], [StorageLocation], [PurchaseDate])
VALUES (4, N'Rodtox-001', N'SN-R300-2023-001', N'modelEAU Lab', NULL, '2023-01-01');  -- ID 6

INSERT INTO [dbo].[Equipment] ([EquipmentModel_ID], [Identifier], [SerialNumber], [Owner], [StorageLocation], [PurchaseDate])
VALUES (5, N'Basestation-Turb', N'SN-BSTURB-2024-001', N'modelEAU Lab', NULL, '2024-09-01');  -- ID 7

PRINT 'Importer test fixtures loaded.';
