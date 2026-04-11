-- ============================================================
-- Importer test fixtures (seed_importer_fixtures.sql)
-- Equipment, parameters, and equipment models required by the
-- docker/import-test-data.yaml configuration so that
-- `docker compose run --rm importer` succeeds on a fresh DB.
-- ============================================================

SET NOCOUNT ON;

-- Units (appended after the 9 in seed_v2.2.0.sql)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'AU');   -- Absorbance units (UV-Vis spectrophotometry)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'-');    -- Dimensionless (images and other unitless channels)

-- Equipment models (IDs 4-6, appended after the 3 in seed_v2.2.0.sql)
INSERT INTO [dbo].[EquipmentModel] ([EquipmentModel], [Method], [Functions], [Manufacturer], [ManualLocation])
VALUES (N'Rodtox R300', N'Respirometry', N'Biological toxicity test via DO consumption rate', N'LAR Process Analysers', NULL);  -- ID 4

INSERT INTO [dbo].[EquipmentModel] ([EquipmentModel], [Method], [Functions], [Manufacturer], [ManualLocation])
VALUES (N'TurbR300 Basestation', N'Optical nephelometry', N'Continuous online turbidity monitoring', N'LAR Process Analysers', NULL);  -- ID 5

INSERT INTO [dbo].[EquipmentModel] ([EquipmentModel], [Method], [Functions], [Manufacturer], [ManualLocation])
VALUES (N'Felinoscope 2000', N'Image capture', N'Inline turbidity/sediment camera', N'Unknown', NULL);  -- ID 6

-- Parameters (IDs 8-11, appended after 7 in seed_v2.2.0.sql)
-- Unit_ID is no longer on Parameter — it lives on Channel instead.
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Dissolved oxygen', N'Dissolved oxygen concentration in water');  -- ID 8

INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Turbidity', N'Water turbidity measured by nephelometry');  -- ID 9

INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'absorbance', N'UV-Vis spectral absorbance (per-wavelength vector)');  -- ID 10

INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'turbidity_image', N'Inline turbidity image from felinoscope camera');  -- ID 11

-- Equipment (auto IDs; resolved by Identifier name in the importer)
INSERT INTO [dbo].[Equipment] ([EquipmentModel_ID], [Identifier], [SerialNumber], [Owner], [StorageLocation], [PurchaseDate])
VALUES (4, N'Rodtox-001', N'SN-R300-2023-001', N'modelEAU Lab', NULL, '2023-01-01');

INSERT INTO [dbo].[Equipment] ([EquipmentModel_ID], [Identifier], [SerialNumber], [Owner], [StorageLocation], [PurchaseDate])
VALUES (5, N'Basestation-Turb', N'SN-BSTURB-2024-001', N'modelEAU Lab', NULL, '2024-09-01');

INSERT INTO [dbo].[Equipment] ([EquipmentModel_ID], [Identifier], [SerialNumber], [Owner], [StorageLocation], [PurchaseDate])
VALUES (6, N'felinoscope_2000', N'SN-FELI-2000-001', N'modelEAU Lab', NULL, '2020-01-01');

PRINT 'Importer test fixtures loaded.';
