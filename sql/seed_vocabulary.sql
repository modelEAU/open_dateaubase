-- ============================================================
-- Vocabulary seed (seed_vocabulary.sql)
-- Replaces seed_v2.2.0.sql + seed_importer_fixtures.sql
--
-- Contains ONLY lookup/vocabulary rows that the importer cannot
-- auto-create: units, parameters, procedures, one TEST_ watershed,
-- and one TEST_ lab.
--
-- No Equipment, EquipmentModel, Site, SamplingPoint, Campaign,
-- Channel, Observation, or Value rows — those are created by the
-- importer on first run, proving the auto-creation logic works.
-- ============================================================

SET NOCOUNT ON;

-- ============================================================
-- Units (13 total)
-- ============================================================
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'mg/L');         -- ID 1
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'NTU');          -- ID 2
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'pH units');     -- ID 3
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'°C');           -- ID 4
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'mS/cm');        -- ID 5
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'nm');           -- ID 6: nanometres (UV-Vis wavelength axis)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'µm');           -- ID 7: micrometres (particle size axis)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'm/s');          -- ID 8: metres per second
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'Status Code');  -- ID 9: integer status codes
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'AU');           -- ID 10: absorbance units (UV-Vis)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'-');            -- ID 11: dimensionless (images)
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'm³/h');         -- ID 12: volumetric flow rate
INSERT INTO [dbo].[Unit] ([Unit]) VALUES (N'm');            -- ID 13: metres (level/depth)

-- ============================================================
-- Parameters (17 total)
-- ============================================================
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'TSS',           N'Total suspended solids');                                            -- ID 1
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'COD',           N'Chemical oxygen demand');                                            -- ID 2
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'pH',            N'Hydrogen ion concentration');                                        -- ID 3
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Temperature',   N'Water temperature');                                                 -- ID 4
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Conductivity',  N'Electrical conductivity');                                           -- ID 5
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Sensor Status', N'Per-channel operational status code');                               -- ID 6
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Device Status', N'Overall equipment health status code');                              -- ID 7
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Dissolved oxygen', N'Dissolved oxygen concentration in water');                        -- ID 8
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Turbidity',     N'Water turbidity measured by nephelometry');                          -- ID 9
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'absorbance',    N'UV-Vis spectral absorbance (per-wavelength vector, unit AU)');       -- ID 10
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Ammonium-N',    N'Ammonium nitrogen concentration (NH4-N)');                           -- ID 11
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Nitrate-N',     N'Nitrate nitrogen concentration as NO3-N equivalent');                -- ID 12
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'COD filtered',  N'Filtered COD (CODf) — soluble fraction of chemical oxygen demand'); -- ID 13
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Flow',          N'Volumetric flow rate');                                              -- ID 14
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Level',         N'Water level / depth');                                               -- ID 15
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'floc_morphology', N'Activated sludge floc morphology image from inline microscope');  -- ID 16
INSERT INTO [dbo].[Parameter] ([Parameter], [Description])
VALUES (N'Potassium',     N'Potassium concentration (K)');                                       -- ID 17

-- ============================================================
-- Procedures (3 standard ones)
-- ============================================================
INSERT INTO [dbo].[Procedures] ([ProcedureName], [ProcedureType], [Description], [ProcedureLocation])
VALUES (N'Grab sampling', N'Sampling', N'Manual grab sample collected at water surface', N'/procedures/grab_sampling.pdf');

INSERT INTO [dbo].[Procedures] ([ProcedureName], [ProcedureType], [Description], [ProcedureLocation])
VALUES (N'24h composite', N'Sampling', N'Time-weighted 24-hour composite sample via autosampler', N'/procedures/composite_24h.pdf');

INSERT INTO [dbo].[Procedures] ([ProcedureName], [ProcedureType], [Description], [ProcedureLocation])
VALUES (N'Online continuous', N'Measurement', N'Continuous in-situ measurement with data logging', N'/procedures/online_continuous.pdf');

-- ============================================================
-- Watershed (1 row, TEST_ prefix)
-- ============================================================
INSERT INTO [dbo].[Watershed] ([Name], [Description], [SurfaceArea], [ConcentrationTime], [ImperviousSurface])
VALUES (N'TEST_Rivière Saint-Charles', N'TEST watershed — Quebec City urban catchment', 550.0, 180, 35.5);

INSERT INTO [dbo].[HydrologicalCharacteristics] ([UrbanArea], [Forest], [Wetlands], [Cropland], [Meadow], [Grassland])
VALUES (35.5, 25.0, 5.0, 10.0, 12.5, 12.0);

INSERT INTO [dbo].[UrbanCharacteristics] ([Commercial], [GreenSpaces], [Industrial], [Institutional], [Residential], [Agricultural], [Recreational])
VALUES (15.0, 8.0, 12.0, 5.0, 45.0, 5.0, 10.0);

-- ============================================================
-- Laboratory (Site_ID is nullable — no dummy site needed)
-- ============================================================
INSERT INTO [dbo].[Laboratory] ([Name], [Site_ID], [Description])
VALUES (N'TEST_modelEAU Water Quality Lab', NULL, N'TEST lab — in-house water quality analysis at Université Laval');

PRINT 'Vocabulary seed loaded: 13 units, 17 parameters, 3 procedures, 1 watershed, 1 lab.';
