-- ============================================================
-- Fixture seed (seed_fixtures.sql)
-- Replaces seed_vocabulary.sql (renamed 2026-05-02)
--
-- Contains ONLY sections that are NOT auto-generated from YAML
-- seed_data fields:
--   1. Unit rows + QUDT IRI UPDATEs + UnitVector UPDATEs
--   2. Parameter rows + ENVO IRI UPDATEs
--   3. Procedures (TEST_ context, 3 rows)
--   4. Watershed + HydrologicalCharacteristics + UrbanCharacteristics
--      (1 TEST_ row each)
--   5. Laboratory (1 TEST_ row)
--
-- All fixed vocabulary tables (ValueKind, ChannelKind,
-- DataProvenanceKind, ProcessingKind, SignalInterfaceKind,
-- SignalInterfacePortKind, QualityCode, AnnotationKind, BinKind,
-- CampaignKind, EquipmentEventKind, ControlLoopPortKind,
-- ProcessUnitKind, SampleKind, SampleCollectionKind) are now
-- seeded by the auto-generated
-- sql_generation_scripts/v4.0.0_seed_mssql.sql.
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
-- Unit ontology (QUDT IRIs + SI dimension vectors)
-- Format: [m, kg, s, A, K, mol, cd]
-- ============================================================
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/MilliGM-PER-L',   [UnitVector]=N'0,1,-3,0,0,0,0' WHERE [Unit]=N'mg/L';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/NTU',              [UnitVector]=N'0,0,0,0,0,0,0'  WHERE [Unit]=N'NTU';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/PH',               [UnitVector]=N'0,0,0,0,0,0,0'  WHERE [Unit]=N'pH units';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/DEG_C',            [UnitVector]=N'0,0,0,0,1,0,0'  WHERE [Unit]=N'°C';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/MilliS-PER-CentiM',[UnitVector]=N'-3,-1,3,2,0,0,0' WHERE [Unit]=N'mS/cm';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/NanoM',            [UnitVector]=N'1,0,0,0,0,0,0'  WHERE [Unit]=N'nm';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/MicroM',           [UnitVector]=N'1,0,0,0,0,0,0'  WHERE [Unit]=N'µm';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/M-PER-SEC',        [UnitVector]=N'1,0,-1,0,0,0,0' WHERE [Unit]=N'm/s';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/ABSORBANCE_UNIT',  [UnitVector]=N'0,0,0,0,0,0,0'  WHERE [Unit]=N'AU';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/UNITLESS',         [UnitVector]=N'0,0,0,0,0,0,0'  WHERE [Unit]=N'-';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/M3-PER-HR',        [UnitVector]=N'3,0,-1,0,0,0,0' WHERE [Unit]=N'm³/h';
UPDATE [dbo].[Unit] SET [QUDT_IRI]=N'https://qudt.org/vocab/unit/M',                [UnitVector]=N'1,0,0,0,0,0,0'  WHERE [Unit]=N'm';

-- ============================================================
-- Parameter ontology (ENVO IRIs)
-- Note: status/image/spectral parameters have no ENVO mapping.
-- ============================================================
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01001502' WHERE [Parameter]=N'TSS';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01000632' WHERE [Parameter]=N'COD';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_09200019' WHERE [Parameter]=N'pH';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01001501' WHERE [Parameter]=N'Temperature';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_09200010' WHERE [Parameter]=N'Conductivity';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01001111' WHERE [Parameter]=N'Dissolved oxygen';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01001573' WHERE [Parameter]=N'Turbidity';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/CHEBI_49786'   WHERE [Parameter]=N'Ammonium-N';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/CHEBI_17632'   WHERE [Parameter]=N'Nitrate-N';
UPDATE [dbo].[Parameter] SET [ENVO_IRI]=N'http://purl.obolibrary.org/obo/ENVO_01001020' WHERE [Parameter]=N'Flow';

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

PRINT 'Fixture seed loaded: 13 units, 17 parameters, 3 procedures, 1 watershed, 1 lab.';
