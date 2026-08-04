-- Migration: v2.5.0 -> v2.6.0
-- Platform: mssql
-- Generated: 2026-08-04 UTC
-- Rollback: v2.5.0_to_v2.6.0_mssql_rollback.sql
--
-- Process unit vocabulary rebuilt on two axes:
--   device — ProcessUnitKind gains a Category (Structural / Treatment /
--            Conveyance) and the named treatment nouns it lacked.
--   stage  — TreatmentStage becomes its own vocabulary, referenced by
--            ProcessUnit, so a clarifier is primary or secondary by the role it
--            holds in one plant's train rather than by being two device kinds.
-- Plus OperationKind.Reconstruction and Person.IsActive.
--
-- IDs 1-11 of ProcessUnitKind keep their numbers and their rows: nothing is
-- renumbered, retired or remapped, so no ProcessUnit row changes meaning.
--
-- Every step is guarded, so re-running on an already-migrated database is a
-- no-op.

-- ---------------------------------------------------------------------------
-- 1. ProcessUnitKind.Category
-- ---------------------------------------------------------------------------

IF COL_LENGTH('dbo.ProcessUnitKind', 'Category') IS NULL
BEGIN
    ALTER TABLE [dbo].[ProcessUnitKind] ADD [Category] NVARCHAR(20) NULL;
END
GO

IF OBJECT_ID('dbo.CK_ProcessUnitKind_Category', 'C') IS NULL
BEGIN
    ALTER TABLE [dbo].[ProcessUnitKind] ADD CONSTRAINT [CK_ProcessUnitKind_Category]
        CHECK ([Category] IS NULL OR [Category] IN ('Structural', 'Treatment', 'Conveyance'));
END
GO

-- ---------------------------------------------------------------------------
-- 2. Categorise and re-describe the pre-existing terms (IDs 1-11).
--    Descriptions are rewritten to state design intent and to point the generic
--    vessel terms at the specific ones — the distinction users could not see.
-- ---------------------------------------------------------------------------

UPDATE [dbo].[ProcessUnitKind] SET [Category] = N'Structural',
    [Description] = N'Broad spatial zone grouping other units (e.g. biological treatment area)'
    WHERE [ProcessUnitKind_ID] = 1;
UPDATE [dbo].[ProcessUnitKind] SET [Category] = N'Structural',
    [Description] = N'Defined functional sub-zone within a process area'
    WHERE [ProcessUnitKind_ID] = 2;
UPDATE [dbo].[ProcessUnitKind] SET [Category] = N'Structural',
    [Description] = N'Generic enclosed vessel — prefer a Treatment term where one describes what the tank is for'
    WHERE [ProcessUnitKind_ID] = 3;
UPDATE [dbo].[ProcessUnitKind] SET [Category] = N'Treatment',
    [Description] = N'Generic vessel for controlled biological or chemical reaction — prefer a specific reactor term where one applies'
    WHERE [ProcessUnitKind_ID] = 4;
UPDATE [dbo].[ProcessUnitKind] SET [Category] = N'Conveyance',
    [Description] = N'Conduit transporting liquid between process units'
    WHERE [ProcessUnitKind_ID] = 5;
UPDATE [dbo].[ProcessUnitKind] SET [Category] = N'Conveyance',
    [Description] = N'Mechanical device for moving liquid'
    WHERE [ProcessUnitKind_ID] = 6;
UPDATE [dbo].[ProcessUnitKind] SET [Category] = N'Conveyance',
    [Description] = N'Flow control device regulating liquid passage'
    WHERE [ProcessUnitKind_ID] = 7;
UPDATE [dbo].[ProcessUnitKind] SET [Category] = N'Treatment',
    [Description] = N'Gravity settling vessel separating solids from liquid. Whether it is primary or secondary is recorded as the unit''s treatment stage, not as its kind'
    WHERE [ProcessUnitKind_ID] = 8;
UPDATE [dbo].[ProcessUnitKind] SET [Category] = N'Structural',
    [Description] = N'Generic open or partially open containment structure — prefer a Treatment term where one applies'
    WHERE [ProcessUnitKind_ID] = 9;
UPDATE [dbo].[ProcessUnitKind] SET [Category] = N'Conveyance',
    [Description] = N'Mechanical device for supplying air or gas'
    WHERE [ProcessUnitKind_ID] = 10;
-- ID 11 'Other' stays uncategorised by design.
GO

-- ---------------------------------------------------------------------------
-- 3. New ProcessUnitKind terms (IDs 12-31), appended.
--    Drinking-water-only devices are deliberately absent.
-- ---------------------------------------------------------------------------

SET IDENTITY_INSERT [dbo].[ProcessUnitKind] ON;

INSERT INTO [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID], [Category], [Name], [Description])
SELECT [ProcessUnitKind_ID], [Category], [Name], [Description]
FROM (VALUES
    (12, N'Structural', N'Train',              N'One parallel process line through a plant, grouping the units that treat a shared share of the flow'),
    (13, N'Structural', N'Storage tank',       N'Vessel holding liquid for later use or discharge, with no treatment intended'),
    (14, N'Structural', N'Equalization basin', N'Basin buffering flow or load variation so downstream units see a steadier feed'),
    (15, N'Treatment',  N'Aerated activated sludge reactor',   N'Activated sludge reactor designed to be aerated, holding a suspended culture in contact with oxygen. Design intent — the oxygen actually present is a measurement'),
    (16, N'Treatment',  N'Anoxic activated sludge reactor',    N'Activated sludge reactor designed to run without aeration on nitrate as electron acceptor, typically for denitrification'),
    (17, N'Treatment',  N'Anaerobic activated sludge reactor', N'Activated sludge reactor designed to run free of both oxygen and nitrate, typically for biological phosphorus release'),
    (18, N'Treatment',  N'Sequencing batch reactor',           N'Single vessel cycling fill, react, settle and decant in time rather than separating them in space'),
    (19, N'Treatment',  N'Membrane bioreactor',                N'Activated sludge reactor whose biomass is retained by a membrane instead of by a settling stage'),
    (20, N'Treatment',  N'Digester',                           N'Vessel stabilising sludge by microbial degradation of its biodegradable organic content, anaerobically producing biogas or aerobically consuming oxygen'),
    (21, N'Treatment',  N'Thermal hydrolysis unit',            N'Unit conditioning sludge under heat and pressure to improve its digestibility and dewaterability (e.g. a Cambi installation)'),
    (22, N'Treatment',  N'Screen',                             N'Bar rack or perforated surface retaining solids too large to pass, cleared by raking or brushing'),
    (23, N'Treatment',  N'Grit chamber',                       N'Chamber settling dense inorganic particles at a controlled velocity that keeps lighter organic solids in suspension'),
    (24, N'Treatment',  N'Dissolved-air flotation unit',       N'Unit separating solids by attaching fine air bubbles so they rise and are skimmed off'),
    (25, N'Treatment',  N'Membrane module',                    N'Unit separating a feed into permeate and retentate across a semi-permeable barrier'),
    (26, N'Treatment',  N'UV reactor',                         N'Unit inactivating pathogens by exposing a stream to ultraviolet irradiation at a design dose'),
    (27, N'Treatment',  N'Contact basin',                      N'Basin holding a stream in contact with a dosed disinfectant for a design detention time'),
    (28, N'Treatment',  N'Thickener',                          N'Unit concentrating sludge solids ahead of digestion or dewatering'),
    (29, N'Treatment',  N'Dewatering unit',                    N'Unit removing water from sludge mechanically (centrifuge, belt or filter press, screw press)'),
    (30, N'Conveyance', N'Weir',                               N'Overflow structure setting a level or measuring a flow'),
    (31, N'Conveyance', N'Splitter box',                       N'Structure dividing one flow between two or more downstream units')
) AS v ([ProcessUnitKind_ID], [Category], [Name], [Description])
WHERE NOT EXISTS (
    SELECT 1 FROM [dbo].[ProcessUnitKind] p
    WHERE p.[ProcessUnitKind_ID] = v.[ProcessUnitKind_ID] OR p.[Name] = v.[Name]
);

SET IDENTITY_INSERT [dbo].[ProcessUnitKind] OFF;
GO

-- ---------------------------------------------------------------------------
-- 4. TreatmentStage
-- ---------------------------------------------------------------------------

IF OBJECT_ID('dbo.TreatmentStage', 'U') IS NULL
BEGIN
    CREATE TABLE [dbo].[TreatmentStage] (
        [TreatmentStage_ID] INT IDENTITY(1,1) NOT NULL,
        [Name] NVARCHAR(100) NOT NULL,
        [SortOrder] INT NOT NULL,
        [Description] NVARCHAR(300),
        CONSTRAINT [PK_TreatmentStage] PRIMARY KEY ([TreatmentStage_ID]),
        CONSTRAINT [UQ_TreatmentStage_Name] UNIQUE ([Name])
    );
END
GO

IF NOT EXISTS (SELECT 1 FROM [dbo].[TreatmentStage])
BEGIN
    SET IDENTITY_INSERT [dbo].[TreatmentStage] ON;
    INSERT INTO [dbo].[TreatmentStage] ([TreatmentStage_ID], [SortOrder], [Name], [Description]) VALUES
        (1, 1, N'Preliminary', N'Removes the gross solids, rags and grit that would damage or foul the units downstream'),
        (2, 2, N'Primary',     N'Removes settleable and floatable material from a raw stream by physical means, ahead of any biological step'),
        (3, 3, N'Secondary',   N'Removes dissolved and colloidal organic matter biologically, together with the separation of the biomass this produces'),
        (4, 4, N'Tertiary',    N'Polishes a secondary effluent — residual solids, nutrients, micropollutants or pathogens — beyond what the secondary stage achieves'),
        (5, 5, N'Sludge line', N'Treats the solids drawn off the water line rather than the water itself');
    SET IDENTITY_INSERT [dbo].[TreatmentStage] OFF;
END
GO

-- ---------------------------------------------------------------------------
-- 5. ProcessUnit.TreatmentStage_ID
-- ---------------------------------------------------------------------------

IF COL_LENGTH('dbo.ProcessUnit', 'TreatmentStage_ID') IS NULL
BEGIN
    ALTER TABLE [dbo].[ProcessUnit] ADD [TreatmentStage_ID] INT NULL;
END
GO

IF OBJECT_ID('dbo.FK_ProcessUnit_TreatmentStage_ID', 'F') IS NULL
BEGIN
    ALTER TABLE [dbo].[ProcessUnit] ADD CONSTRAINT [FK_ProcessUnit_TreatmentStage_ID]
        FOREIGN KEY ([TreatmentStage_ID]) REFERENCES [dbo].[TreatmentStage] ([TreatmentStage_ID]);
END
GO

-- ---------------------------------------------------------------------------
-- 6. OperationKind: Interpolation / Reconstruction split.
--    Split on whether bracketing observations existed, not on gap size — ID 6
--    keeps its number, so no ProcessingStep row changes meaning; steps that
--    actually reconstructed are not reclassified here because the database
--    cannot tell which those were. Reclassify by hand where it matters.
-- ---------------------------------------------------------------------------

UPDATE [dbo].[OperationKind]
    SET [Description] = N'Missing values filled from observations bracketing the gap on both sides'
    WHERE [OperationKind_ID] = 6;
GO

IF NOT EXISTS (SELECT 1 FROM [dbo].[OperationKind] WHERE [OperationKind_ID] = 7)
BEGIN
    INSERT INTO [dbo].[OperationKind] ([OperationKind_ID], [Name], [Description]) VALUES
        (7, N'Reconstruction', N'Values generated where no bracketing observation existed — from a model, a correlated channel or a seasonal profile');
END
GO

-- ---------------------------------------------------------------------------
-- 7. Person.IsActive — existing people default to active, the safe direction:
--    wrongly hiding a real person would blank out pickers.
-- ---------------------------------------------------------------------------

IF COL_LENGTH('dbo.Person', 'IsActive') IS NULL
BEGIN
    ALTER TABLE [dbo].[Person] ADD [IsActive] BIT NOT NULL DEFAULT 1;
END
GO

-- ---------------------------------------------------------------------------
-- 8. Version stamp
-- ---------------------------------------------------------------------------

IF NOT EXISTS (SELECT 1 FROM [dbo].[SchemaVersion] WHERE [Version] = N'2.6.0')
BEGIN
    INSERT INTO [dbo].[SchemaVersion] ([Version], [Description]) VALUES
        (N'2.6.0', N'Process unit vocabulary rebuilt on the device and stage axes: ProcessUnitKind Category plus named treatment nouns, TreatmentStage referenced by ProcessUnit. Also OperationKind.Reconstruction and Person.IsActive.');
END
GO
