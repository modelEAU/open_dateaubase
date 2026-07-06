-- ============================================================
-- Demo/fixture seed (seed_demo.sql)
--
-- Realistic TEST_-prefixed data for a small pilot WWTP site.
-- Enables end-to-end testing of:
--   - Site / ProcessUnit / SamplingPoint browsing
--   - Campaign management
--   - Lab ingest workflow + LabPanel selection
--
-- Depends on (already loaded):
--   - v4.x.x_seed_mssql.sql — vocabulary tables
--
-- ID anchors used (must not change):
--   Unit:          mg/L=1  NTU=2  pH units=3  °C=4
--   Parameter:     TSS=1  COD=2  pH=3  Temp=4  DO=8  Turb=9  NH4-N=11  NO3-N=12  CODf=13
--   ValueKind:     Scalar=1  Vector=2  Image=4
--   StreamKind:    Sensor=1  Lab=2 (AnalysisSeries is the Lab subtype of Stream)
--   SiteKind:      Experimental WWTP=12
--   CampaignKind:  Experiment=1  Operations=2
--   ProcessUnitKind: Area=1  Zone=2  Basin=9  Clarifier=8
-- ============================================================

SET NOCOUNT ON;

-- ============================================================
-- Watershed + hydrological context (TEST_ row)
-- ============================================================
DECLARE @WatershedID INT,
        @LaboratoryID INT;

INSERT INTO [dbo].[Watershed] ([Name], [Description], [SurfaceArea], [ConcentrationTime], [ImperviousSurface])
VALUES (N'TEST_Rivière Saint-Charles', N'TEST watershed — Quebec City urban catchment', 550.0, 180, 35.5);
SET @WatershedID = SCOPE_IDENTITY();

INSERT INTO [dbo].[HydrologicalCharacteristics] ([Watershed_ID], [UrbanArea], [Forest], [Wetlands], [Cropland], [Meadow], [Grassland])
VALUES (@WatershedID, 35.5, 25.0, 5.0, 10.0, 12.5, 12.0);

INSERT INTO [dbo].[LandUse] ([Watershed_ID], [Commercial], [GreenSpaces], [Industrial], [Institutional], [Residential], [Agricultural], [Recreational])
VALUES (@WatershedID, 15.0, 8.0, 12.0, 5.0, 45.0, 5.0, 10.0);

-- ============================================================
-- Laboratory (TEST_ row)
-- ============================================================
INSERT INTO [dbo].[Laboratory] ([Name], [Site_ID], [Description])
VALUES (N'TEST_modelEAU Water Quality Lab', NULL, N'TEST lab — in-house water quality analysis at Université Laval');
SET @LaboratoryID = SCOPE_IDENTITY();

-- ============================================================
-- Persons (3 rows)
-- ============================================================
DECLARE @PersonProfID  INT,
        @PersonPhDID   INT,
        @PersonTechID  INT;

INSERT INTO [dbo].[Person] ([LastName], [FirstName], [Company], [Role], [Email])
VALUES (N'Vigneron', N'Jean', N'Université Laval — modelEAU', N'Professor', N'jean.vigneron@test.modeleau.ca');
SET @PersonProfID = SCOPE_IDENTITY();

INSERT INTO [dbo].[Person] ([LastName], [FirstName], [Company], [Role], [Email])
VALUES (N'Tremblay', N'Marie', N'Université Laval — modelEAU', N'PhD', N'marie.tremblay@test.modeleau.ca');
SET @PersonPhDID = SCOPE_IDENTITY();

INSERT INTO [dbo].[Person] ([LastName], [FirstName], [Company], [Role], [Email])
VALUES (N'Bergeron', N'Simon', N'Université Laval — modelEAU', N'Technician', N'simon.bergeron@test.modeleau.ca');
SET @PersonTechID = SCOPE_IDENTITY();

-- ============================================================
-- Site (1 row — pilot WWTP linked to TEST_ watershed)
-- ============================================================
DECLARE @SiteID INT;

INSERT INTO [dbo].[Site] (
    [Watershed_ID], [Name], [SiteKind_ID], [Description],
    [LatitudeWGS84], [LongitudeWGS84],
    [City], [Province], [Country]
)
VALUES (
    @WatershedID,
    N'TEST_pilEAUte WWTP',
    12,                                       -- Experimental Wastewater Treatment Plant
    N'TEST site — small-scale pilot wastewater treatment plant at Université Laval',
    46.7817, -71.2747,
    N'Québec City', N'Québec', N'Canada'
);
SET @SiteID = SCOPE_IDENTITY();

-- ============================================================
-- ProcessUnit hierarchy (5 units)
--
--   B-100  Primary basin      (Basin,     no parent)
--   BIO-200 Bio treatment area (Area,      no parent)
--   AN-210  Anoxic zone        (Zone,      parent BIO-200)
--   AX-220  Aerobic zone       (Zone,      parent BIO-200)
--   C-300  Secondary clarifier (Clarifier, no parent)
-- ============================================================
DECLARE @PU_B100   INT,
        @PU_BIO200 INT,
        @PU_AN210  INT,
        @PU_AX220  INT,
        @PU_C300   INT,
        @PU_BR4    INT;

INSERT INTO [dbo].[ProcessUnit] ([Site_ID], [Tag], [Name], [ProcessUnitKind_ID], [Parent_ID])
VALUES (@SiteID, N'B-100', N'TEST_ Primary settling basin', 9, NULL);
SET @PU_B100 = SCOPE_IDENTITY();

INSERT INTO [dbo].[ProcessUnit] ([Site_ID], [Tag], [Name], [ProcessUnitKind_ID], [Parent_ID])
VALUES (@SiteID, N'BIO-200', N'TEST_ Biological treatment area', 1, NULL);
SET @PU_BIO200 = SCOPE_IDENTITY();

INSERT INTO [dbo].[ProcessUnit] ([Site_ID], [Tag], [Name], [Description], [ProcessUnitKind_ID], [Parent_ID])
VALUES (@SiteID, N'AN-210', N'TEST_ Anoxic zone', N'Pre-anoxic zone for denitrification', 2, @PU_BIO200);
SET @PU_AN210 = SCOPE_IDENTITY();

INSERT INTO [dbo].[ProcessUnit] ([Site_ID], [Tag], [Name], [Description], [ProcessUnitKind_ID], [Parent_ID])
VALUES (@SiteID, N'AX-220', N'TEST_ Aerobic zone', N'Aerated zone for nitrification and BOD removal', 2, @PU_BIO200);
SET @PU_AX220 = SCOPE_IDENTITY();

INSERT INTO [dbo].[ProcessUnit] ([Site_ID], [Tag], [Name], [ProcessUnitKind_ID], [Parent_ID])
VALUES (@SiteID, N'C-300', N'TEST_ Secondary clarifier', 8, NULL);
SET @PU_C300 = SCOPE_IDENTITY();

INSERT INTO [dbo].[ProcessUnit] ([Site_ID], [Tag], [Name], [Description], [ProcessUnitKind_ID], [Parent_ID])
VALUES (@SiteID, N'BR-400', N'TEST_ Bioreactor 4', N'Sequencing batch reactor used for bioaugmentation experiments', 4, NULL);
SET @PU_BR4 = SCOPE_IDENTITY();

-- ============================================================
-- SamplingPoints (5 rows)
-- ============================================================
DECLARE @SP_Influent    INT,
        @SP_PrimEff     INT,
        @SP_AnoxicOut   INT,
        @SP_AerobicOut  INT,
        @SP_FinalEff    INT,
        @SP_BR4         INT;

INSERT INTO [dbo].[SamplingPoint] ([Site_ID], [SamplingPoint], [Description])
VALUES (@SiteID, N'TEST_ Influent', N'Raw influent before primary treatment');
SET @SP_Influent = SCOPE_IDENTITY();

INSERT INTO [dbo].[SamplingPoint] ([Site_ID], [SamplingPoint], [Description], [ProcessUnit_ID])
VALUES (@SiteID, N'TEST_ Primary effluent', N'Effluent after primary settling basin', @PU_B100);
SET @SP_PrimEff = SCOPE_IDENTITY();

INSERT INTO [dbo].[SamplingPoint] ([Site_ID], [SamplingPoint], [Description], [ProcessUnit_ID])
VALUES (@SiteID, N'TEST_ Anoxic zone outlet', N'Outlet of the pre-anoxic zone', @PU_AN210);
SET @SP_AnoxicOut = SCOPE_IDENTITY();

INSERT INTO [dbo].[SamplingPoint] ([Site_ID], [SamplingPoint], [Description], [ProcessUnit_ID])
VALUES (@SiteID, N'TEST_ Aerobic zone outlet', N'Outlet of the aerobic nitrification zone', @PU_AX220);
SET @SP_AerobicOut = SCOPE_IDENTITY();

INSERT INTO [dbo].[SamplingPoint] ([Site_ID], [SamplingPoint], [Description], [ProcessUnit_ID])
VALUES (@SiteID, N'TEST_ Final effluent', N'Treated effluent after secondary clarification', @PU_C300);
SET @SP_FinalEff = SCOPE_IDENTITY();

INSERT INTO [dbo].[SamplingPoint] ([Site_ID], [SamplingPoint], [Description], [ProcessUnit_ID])
VALUES (@SiteID, N'TEST_ Bioreactor 4', N'Mixed liquor sampling point inside Bioreactor 4 (SBR)', @PU_BR4);
SET @SP_BR4 = SCOPE_IDENTITY();

-- ============================================================
-- Campaigns (2 rows)
-- ============================================================
DECLARE @CampOpsID INT, @CampExpID INT;

INSERT INTO [dbo].[Campaign] (
    [CampaignKind_ID], [Name], [Description],
    [CampaignStartDateTime], [ResponsiblePerson_ID]
)
VALUES (
    2,      -- Operations
    N'TEST_ Routine Operations 2026',
    N'TEST campaign — ongoing routine monitoring of the pilot WWTP',
    '2026-01-01T00:00:00',
    @PersonTechID
);
SET @CampOpsID = SCOPE_IDENTITY();

INSERT INTO [dbo].[Campaign] (
    [CampaignKind_ID], [Name], [Description],
    [CampaignStartDateTime], [CampaignEndDateTime], [ResponsiblePerson_ID]
)
VALUES (
    1,      -- Experiment
    N'TEST_ Bioaugmentation Experiment Spring 2026',
    N'TEST campaign — evaluating the effect of bioaugmentation on nitrogen removal',
    '2026-04-01T00:00:00',
    '2026-06-30T00:00:00',
    @PersonPhDID
);
SET @CampExpID = SCOPE_IDENTITY();

-- ============================================================
-- CampaignSamplingLocation
--   Ops campaign covers influent + final effluent
--   Experiment campaign covers all 5 points
-- ============================================================
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [SamplingPoint_ID], [Role])
VALUES (@CampOpsID, @SP_Influent,   N'Inlet');
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [SamplingPoint_ID], [Role])
VALUES (@CampOpsID, @SP_FinalEff,   N'Outlet');

INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [SamplingPoint_ID], [Role])
VALUES (@CampExpID, @SP_Influent,   N'Inlet');
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [SamplingPoint_ID], [Role])
VALUES (@CampExpID, @SP_PrimEff,    N'After primary treatment');
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [SamplingPoint_ID], [Role])
VALUES (@CampExpID, @SP_AnoxicOut,  N'Anoxic zone');
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [SamplingPoint_ID], [Role])
VALUES (@CampExpID, @SP_AerobicOut, N'Aerobic zone');
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [SamplingPoint_ID], [Role])
VALUES (@CampExpID, @SP_FinalEff,   N'Outlet');
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [SamplingPoint_ID], [Role])
VALUES (@CampExpID, @SP_BR4,        N'Bioreactor');

-- ============================================================
-- AnalysisSeries (15 rows — lab-analysable parameters only)
--
-- AnalysisSeries is the Lab subtype of Stream (table-per-type): each series
-- first mints a Stream row (StreamKind_ID=2 Lab) whose Stream_ID becomes the
-- series PK. The @AS_* vars hold that Stream_ID for LabPanelSeries / LabAnalysis.
-- All Scalar (ValueKind_ID=1) unless noted. Processing now lives in ProcessingStep,
-- not on the series.
-- ============================================================
DECLARE @AS_TSS_Inf    INT, @AS_COD_Inf    INT, @AS_CODf_Inf   INT, @AS_NH4_Inf   INT,
        @AS_TSS_Eff    INT, @AS_COD_Eff    INT, @AS_CODf_Eff   INT,
        @AS_NH4_Eff    INT, @AS_NO3_Eff    INT,
        @StreamID      INT;

-- Ops campaign: routine inlet + outlet monitoring (4 influent + 5 effluent)
INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_TSS_Inf = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_TSS_Inf, N'TEST_ TSS at Influent', 1, @SP_Influent, 1, 1, @CampOpsID);       -- TSS, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_COD_Inf = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_COD_Inf, N'TEST_ COD at Influent', 2, @SP_Influent, 1, 1, @CampOpsID);       -- COD, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_CODf_Inf = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_CODf_Inf, N'TEST_ CODf at Influent', 13, @SP_Influent, 1, 1, @CampOpsID);     -- COD filtered, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_NH4_Inf = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_NH4_Inf, N'TEST_ NH4-N at Influent', 11, @SP_Influent, 1, 1, @CampOpsID);    -- NH4-N, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_TSS_Eff = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_TSS_Eff, N'TEST_ TSS at Final effluent', 1, @SP_FinalEff, 1, 1, @CampOpsID); -- TSS, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_COD_Eff = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_COD_Eff, N'TEST_ COD at Final effluent', 2, @SP_FinalEff, 1, 1, @CampOpsID); -- COD, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_CODf_Eff = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_CODf_Eff, N'TEST_ CODf at Final effluent', 13, @SP_FinalEff, 1, 1, @CampOpsID); -- COD filtered, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_NH4_Eff = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_NH4_Eff, N'TEST_ NH4-N at Final effluent', 11, @SP_FinalEff, 1, 1, @CampOpsID); -- NH4-N, mg/L

-- Experiment campaign: effluent NO3-N + intermediate points (4 extra series)
INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_NO3_Eff = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_NO3_Eff, N'TEST_ NO3-N at Final effluent', 12, @SP_FinalEff, 1, 1, @CampExpID); -- NO3-N, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @StreamID = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@StreamID, N'TEST_ TSS at Primary effluent', 1, @SP_PrimEff, 1, 1, @CampExpID);   -- TSS, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @StreamID = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@StreamID, N'TEST_ NH4-N at Anoxic zone outlet', 11, @SP_AnoxicOut, 1, 1, @CampExpID); -- NH4-N, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @StreamID = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@StreamID, N'TEST_ NO3-N at Anoxic zone outlet', 12, @SP_AnoxicOut, 1, 1, @CampExpID); -- NO3-N, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @StreamID = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@StreamID, N'TEST_ NH4-N at Aerobic zone outlet', 11, @SP_AerobicOut, 1, 1, @CampExpID); -- NH4-N, mg/L

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @StreamID = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@StreamID, N'TEST_ Sludge microscopy at Bioreactor 4', 16, @SP_BR4, 4, 11, @CampExpID); -- floc_morphology, Image, dimensionless

-- ============================================================
-- LabPanel (1 row)
-- ============================================================
DECLARE @LabPanelID INT;

INSERT INTO [dbo].[LabPanel] ([Name], [Description], [CreatedByPerson_ID])
VALUES (
    N'TEST_ WWTP Weekly Panel',
    N'TEST panel — standard weekly grab-sample analysis for the pilot WWTP: TSS, COD, CODf, NH4-N (influent + effluent) and NO3-N (effluent)',
    @PersonProfID
);
SET @LabPanelID = SCOPE_IDENTITY();

-- ============================================================
-- LabPanelSeries — link all 9 series to the panel
-- ============================================================
INSERT INTO [dbo].[LabPanelSeries] ([LabPanel_ID], [AnalysisSeries_ID]) VALUES (@LabPanelID, @AS_TSS_Inf);
INSERT INTO [dbo].[LabPanelSeries] ([LabPanel_ID], [AnalysisSeries_ID]) VALUES (@LabPanelID, @AS_COD_Inf);
INSERT INTO [dbo].[LabPanelSeries] ([LabPanel_ID], [AnalysisSeries_ID]) VALUES (@LabPanelID, @AS_CODf_Inf);
INSERT INTO [dbo].[LabPanelSeries] ([LabPanel_ID], [AnalysisSeries_ID]) VALUES (@LabPanelID, @AS_NH4_Inf);
INSERT INTO [dbo].[LabPanelSeries] ([LabPanel_ID], [AnalysisSeries_ID]) VALUES (@LabPanelID, @AS_TSS_Eff);
INSERT INTO [dbo].[LabPanelSeries] ([LabPanel_ID], [AnalysisSeries_ID]) VALUES (@LabPanelID, @AS_COD_Eff);
INSERT INTO [dbo].[LabPanelSeries] ([LabPanel_ID], [AnalysisSeries_ID]) VALUES (@LabPanelID, @AS_CODf_Eff);
INSERT INTO [dbo].[LabPanelSeries] ([LabPanel_ID], [AnalysisSeries_ID]) VALUES (@LabPanelID, @AS_NH4_Eff);
INSERT INTO [dbo].[LabPanelSeries] ([LabPanel_ID], [AnalysisSeries_ID]) VALUES (@LabPanelID, @AS_NO3_Eff);

-- ============================================================
-- Lab measurements (scalar COD + vector absorbance)
--
-- Gives the Explore page real lab data to plot. Each measurement is a chain:
--   Sample -> LabAnalysis -> Observation (Channel_ID NULL) -> Value/ValueVector.
-- Observation.Timestamp is the SAMPLE COLLECTION time (ADR 0002), NOT the
-- analysis time, so lab Traces line up on the time axis with the sensor data
-- the importer loads (COD sensor @ Feb 2024, UV-Vis @ Feb 2026) for an overlay.
-- seed_demo runs before the importer, so the vector series brings its own
-- binning axis rather than reusing a sensor channel's.
-- ============================================================
DECLARE @ExpCOD INT, @SmpID INT, @LaID INT, @ObsID INT;

-- --- Scalar: COD grab samples at Final effluent (overlap COD sensor window) ---
INSERT INTO [dbo].[LabExperiment] ([Name], [Campaign_ID], [ExperimentDateTime], [Description], [CreatedByPerson_ID])
VALUES (N'TEST_ COD effluent grab series', @CampOpsID, '2024-02-06T09:00:00', N'Weekly grab COD at final effluent', @PersonProfID);
SET @ExpCOD = SCOPE_IDENTITY();

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampOpsID, '2024-02-04T16:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpCOD, @AS_COD_Eff, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2024-02-06T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2024-02-04T16:00:00', 1); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode]) VALUES (@ObsID, 46.0, 1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampOpsID, '2024-02-04T22:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpCOD, @AS_COD_Eff, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2024-02-06T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2024-02-04T22:00:00', 1); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode]) VALUES (@ObsID, 53.0, 1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampOpsID, '2024-02-05T04:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpCOD, @AS_COD_Eff, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2024-02-06T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2024-02-05T04:00:00', 1); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode]) VALUES (@ObsID, 39.0, 1);

-- last grab carries two replicates at the same collection time (plotted as two points)
INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampOpsID, '2024-02-05T10:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpCOD, @AS_COD_Eff, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2024-02-06T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2024-02-05T10:00:00', 1); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode]) VALUES (@ObsID, 61.0, 1);
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpCOD, @AS_COD_Eff, @SmpID, 2, 1, @LaboratoryID, @PersonTechID, '2024-02-06T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2024-02-05T10:00:00', 1); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode]) VALUES (@ObsID, 58.0, 1);

-- --- Vector: lab UV-Vis absorbance spectra (self-contained 6-bin axis) ---
DECLARE @LabUVAxis INT, @AS_AbsVec INT, @ExpAbs INT;

INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID], [BinKind_ID])
VALUES (N'TEST_ Lab UV-Vis wavelengths', N'6-point UV-Vis wavelength grid for the lab absorbance demo', 6, 6, 3); -- nm, nominal
SET @LabUVAxis = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [NominalValue]) VALUES
    (@LabUVAxis, 0, 220), (@LabUVAxis, 1, 254), (@LabUVAxis, 2, 300),
    (@LabUVAxis, 3, 360), (@LabUVAxis, 4, 440), (@LabUVAxis, 5, 550);

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_AbsVec = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_AbsVec, N'TEST_ Lab absorbance spectrum at Final effluent', 10, @SP_FinalEff, 2, 10, @CampExpID); -- absorbance, AU, Vector
INSERT INTO [dbo].[AnalysisSeriesAxis] ([AnalysisSeries_ID], [AxisRole], [ValueBinningAxis_ID]) VALUES (@AS_AbsVec, 0, @LabUVAxis);

INSERT INTO [dbo].[LabExperiment] ([Name], [Campaign_ID], [ExperimentDateTime], [Description], [CreatedByPerson_ID])
VALUES (N'TEST_ Lab UV-Vis spectra', @CampExpID, '2026-02-18T09:00:00', N'Bench UV-Vis scans of final-effluent grabs', @PersonProfID);
SET @ExpAbs = SCOPE_IDENTITY();

-- 3 spectra at sample-collection times in the UV-Vis sensor window; the peak
-- bin shifts per sample. ValueVector rows are generated set-based from the axis.
INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampExpID, '2026-02-16T23:50:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpAbs, @AS_AbsVec, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2026-02-18T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2026-02-16T23:50:00', 2); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueVector] ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
SELECT @ObsID, vb.[ValueBin_ID], ROUND(EXP(-POWER(CAST(vb.[BinIndex] AS FLOAT) - 1.0, 2) / 2.0), 4), 1
FROM [dbo].[ValueBin] vb WHERE vb.[ValueBinningAxis_ID] = @LabUVAxis;

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampExpID, '2026-02-17T01:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpAbs, @AS_AbsVec, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2026-02-18T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2026-02-17T01:00:00', 2); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueVector] ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
SELECT @ObsID, vb.[ValueBin_ID], ROUND(EXP(-POWER(CAST(vb.[BinIndex] AS FLOAT) - 2.5, 2) / 2.0), 4), 1
FROM [dbo].[ValueBin] vb WHERE vb.[ValueBinningAxis_ID] = @LabUVAxis;

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampExpID, '2026-02-17T02:30:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpAbs, @AS_AbsVec, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2026-02-18T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2026-02-17T02:30:00', 2); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueVector] ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
SELECT @ObsID, vb.[ValueBin_ID], ROUND(EXP(-POWER(CAST(vb.[BinIndex] AS FLOAT) - 4.0, 2) / 2.0), 4), 1
FROM [dbo].[ValueBin] vb WHERE vb.[ValueBinningAxis_ID] = @LabUVAxis;

-- --- Vector: ViCAs settling-velocity distributions (real data, SOP-018) ---
-- ViCAs (Vitesse de Chute en Assainissement) measures the mass fraction of TSS
-- per settling-velocity class — a 1-D distribution over a single velocity axis,
-- so it is genuinely VECTOR data (like the UV-Vis spectrum above). Numbers are
-- the measured TSS fractions (as %) from elutriation_analysis.xlsx, 3 campaigns.
-- Bins run fast (index 0) to slow (index 6); nominal = representative m/h.
DECLARE @ViCAsAxis INT, @AS_ViCAs INT, @ExpViCAs INT;
DECLARE @U_mh INT = (SELECT [Unit_ID] FROM [dbo].[Unit] WHERE [Unit] = N'm/h');
DECLARE @U_pct INT = (SELECT [Unit_ID] FROM [dbo].[Unit] WHERE [Unit] = N'%');
DECLARE @P_vicas INT = (SELECT [Parameter_ID] FROM [dbo].[Parameter] WHERE [Parameter] = N'TSS mass fraction');

INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID], [BinKind_ID])
VALUES (N'TEST_ ViCAs settling velocity', N'7-class settling-velocity grid for the ViCAs distribution demo', 7, @U_mh, 3); -- m/h, nominal
SET @ViCAsAxis = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [NominalValue]) VALUES
    (@ViCAsAxis, 0, 55.0), (@ViCAsAxis, 1, 38.2), (@ViCAsAxis, 2, 20.3),
    (@ViCAsAxis, 3, 8.0),  (@ViCAsAxis, 4, 3.8),  (@ViCAsAxis, 5, 2.0), (@ViCAsAxis, 6, 0.7);

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_ViCAs = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_ViCAs, N'TEST_ ViCAs TSS settling-velocity distribution at Influent', @P_vicas, @SP_FinalEff, 2, @U_pct, @CampExpID); -- % mass fraction, Vector
INSERT INTO [dbo].[AnalysisSeriesAxis] ([AnalysisSeries_ID], [AxisRole], [ValueBinningAxis_ID]) VALUES (@AS_ViCAs, 0, @ViCAsAxis);

INSERT INTO [dbo].[LabExperiment] ([Name], [Campaign_ID], [ExperimentDateTime], [Description], [CreatedByPerson_ID])
VALUES (N'TEST_ ViCAs elutriation campaigns 2023', @CampExpID, '2023-08-07T09:00:00', N'ViCAs settling-column tests (SOP-018) on WRRF influent grabs', @PersonProfID);
SET @ExpViCAs = SCOPE_IDENTITY();

-- 3 experiment dates; each a vector observation, values are measured TSS fractions (%).
INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampExpID, '2023-08-07T08:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpViCAs, @AS_ViCAs, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2023-08-07T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2023-08-07T08:00:00', 2); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueVector] ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
SELECT @ObsID, vb.[ValueBin_ID], v.frac, 1 FROM [dbo].[ValueBin] vb
JOIN (VALUES (0,2.00),(1,3.40),(2,31.62),(3,25.97),(4,8.20),(5,6.81),(6,22.02)) AS v(idx, frac) ON v.idx = vb.[BinIndex]
WHERE vb.[ValueBinningAxis_ID] = @ViCAsAxis;

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampExpID, '2023-08-21T08:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpViCAs, @AS_ViCAs, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2023-08-21T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2023-08-21T08:00:00', 2); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueVector] ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
SELECT @ObsID, vb.[ValueBin_ID], v.frac, 1 FROM [dbo].[ValueBin] vb
JOIN (VALUES (0,4.23),(1,11.80),(2,23.50),(3,24.13),(4,7.65),(5,5.92),(6,22.78)) AS v(idx, frac) ON v.idx = vb.[BinIndex]
WHERE vb.[ValueBinningAxis_ID] = @ViCAsAxis;

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampExpID, '2023-10-30T08:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpViCAs, @AS_ViCAs, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2023-10-30T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2023-10-30T08:00:00', 2); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueVector] ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
SELECT @ObsID, vb.[ValueBin_ID], v.frac, 1 FROM [dbo].[ValueBin] vb
JOIN (VALUES (0,8.02),(1,4.59),(2,17.44),(3,20.66),(4,7.93),(5,5.98),(6,35.38)) AS v(idx, frac) ON v.idx = vb.[BinIndex]
WHERE vb.[ValueBinningAxis_ID] = @ViCAsAxis;

-- --- Matrix: fluorescence excitation-emission matrices (EEM) ---
-- Genuinely 2-axis binned data (excitation-nm × emission-nm × intensity-RU): the
-- one shape ViCAs cannot provide. Synthesised as two DOM fluorophore peaks —
-- protein-like (Ex 275 / Em 340) and humic-like (Ex 340 / Em 440) — over a
-- 5×7 wavelength grid, at 2 sample times. Values from a 2-D Gaussian mixture.
DECLARE @EEMExAxis INT, @EEMEmAxis INT, @AS_EEM INT, @ExpEEM INT;
DECLARE @U_nm INT = (SELECT [Unit_ID] FROM [dbo].[Unit] WHERE [Unit] = N'nm');
DECLARE @U_RU INT = (SELECT [Unit_ID] FROM [dbo].[Unit] WHERE [Unit] = N'RU');
DECLARE @P_fluor INT = (SELECT [Parameter_ID] FROM [dbo].[Parameter] WHERE [Parameter] = N'Fluorescence');

INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID], [BinKind_ID])
VALUES (N'TEST_ EEM excitation wavelength', N'5-point excitation grid for the fluorescence EEM demo', 5, @U_nm, 3);
SET @EEMExAxis = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [NominalValue]) VALUES
    (@EEMExAxis, 0, 250), (@EEMExAxis, 1, 275), (@EEMExAxis, 2, 300), (@EEMExAxis, 3, 340), (@EEMExAxis, 4, 380);

INSERT INTO [dbo].[ValueBinningAxis] ([Name], [Description], [NumberOfBins], [Unit_ID], [BinKind_ID])
VALUES (N'TEST_ EEM emission wavelength', N'7-point emission grid for the fluorescence EEM demo', 7, @U_nm, 3);
SET @EEMEmAxis = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueBin] ([ValueBinningAxis_ID], [BinIndex], [NominalValue]) VALUES
    (@EEMEmAxis, 0, 300), (@EEMEmAxis, 1, 340), (@EEMEmAxis, 2, 380), (@EEMEmAxis, 3, 420),
    (@EEMEmAxis, 4, 460), (@EEMEmAxis, 5, 500), (@EEMEmAxis, 6, 540);

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_EEM = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID], [Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [Campaign_ID])
VALUES (@AS_EEM, N'TEST_ Fluorescence EEM at Final effluent', @P_fluor, @SP_FinalEff, 3, @U_RU, @CampExpID); -- RU, Matrix
INSERT INTO [dbo].[AnalysisSeriesAxis] ([AnalysisSeries_ID], [AxisRole], [ValueBinningAxis_ID]) VALUES (@AS_EEM, 0, @EEMExAxis); -- row = excitation
INSERT INTO [dbo].[AnalysisSeriesAxis] ([AnalysisSeries_ID], [AxisRole], [ValueBinningAxis_ID]) VALUES (@AS_EEM, 1, @EEMEmAxis); -- col = emission

INSERT INTO [dbo].[LabExperiment] ([Name], [Campaign_ID], [ExperimentDateTime], [Description], [CreatedByPerson_ID])
VALUES (N'TEST_ Fluorescence EEM scans', @CampExpID, '2026-02-18T10:00:00', N'Bench spectrofluorometer EEM scans of final-effluent grabs', @PersonProfID);
SET @ExpEEM = SCOPE_IDENTITY();

-- Two EEM observations; the second ages the humic peak up (×1.4) to give the
-- time-slice selector visible variation. Values are a 2-D Gaussian mixture.
INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampExpID, '2026-02-16T23:50:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpEEM, @AS_EEM, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2026-02-18T10:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2026-02-16T23:50:00', 3); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueMatrix] ([Observation_ID], [RowValueBin_ID], [ColValueBin_ID], [Value], [QualityCode])
SELECT @ObsID, rb.[ValueBin_ID], cb.[ValueBin_ID],
  ROUND(100.0*EXP(-(POWER(rb.[NominalValue]-275,2)/800.0 + POWER(cb.[NominalValue]-340,2)/1800.0))
      +  60.0*EXP(-(POWER(rb.[NominalValue]-340,2)/1250.0 + POWER(cb.[NominalValue]-440,2)/3200.0)), 3), 1
FROM [dbo].[ValueBin] rb CROSS JOIN [dbo].[ValueBin] cb
WHERE rb.[ValueBinningAxis_ID] = @EEMExAxis AND cb.[ValueBinningAxis_ID] = @EEMEmAxis;

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampExpID, '2026-02-17T02:30:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpEEM, @AS_EEM, @SmpID, 1, 1, @LaboratoryID, @PersonTechID, '2026-02-18T10:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2026-02-17T02:30:00', 3); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueMatrix] ([Observation_ID], [RowValueBin_ID], [ColValueBin_ID], [Value], [QualityCode])
SELECT @ObsID, rb.[ValueBin_ID], cb.[ValueBin_ID],
  ROUND(100.0*EXP(-(POWER(rb.[NominalValue]-275,2)/800.0 + POWER(cb.[NominalValue]-340,2)/1800.0))
      +  84.0*EXP(-(POWER(rb.[NominalValue]-340,2)/1250.0 + POWER(cb.[NominalValue]-440,2)/3200.0)), 3), 1
FROM [dbo].[ValueBin] rb CROSS JOIN [dbo].[ValueBin] cb
WHERE rb.[ValueBinningAxis_ID] = @EEMExAxis AND cb.[ValueBinningAxis_ID] = @EEMEmAxis;

-- ============================================================
-- Sensor deployment chain
-- One Turbidity sensor (SOLITAX sc) wired to a monEAU basestation,
-- deployed at the Aerobic zone outlet under the Ops campaign.
-- ============================================================
DECLARE @DAS_ID INT, @SI_ID INT, @EM_Turb INT, @EQ_Turb INT, @CH_Turb INT;

INSERT INTO [dbo].[DataAcquisitionSystem] ([Name])
VALUES (N'TEST_ pilEAUte basestation');
SET @DAS_ID = SCOPE_IDENTITY();

INSERT INTO [dbo].[SignalInterface] ([DataAcquisitionSystem_ID], [Name], [Manufacturer])
VALUES (@DAS_ID, N'TEST_ basestation-SI-01', N'monEAU');
SET @SI_ID = SCOPE_IDENTITY();

INSERT INTO [dbo].[EquipmentModel] ([EquipmentModel], [Manufacturer], [Method])
VALUES (N'SOLITAX sc', N'Hach', N'Scattered light 90° + back-scatter');
SET @EM_Turb = SCOPE_IDENTITY();

INSERT INTO [dbo].[Equipment] ([EquipmentModel_ID], [Identifier], [SerialNumber], [Owner])
VALUES (@EM_Turb, N'TEST_Turb-001', N'T001-2026', N'modelEAU Lab');
SET @EQ_Turb = SCOPE_IDENTITY();

-- Channel: Turbidity, Scalar (ValueKind=1), NTU (Unit=2), Sensor (DataProvenanceKind=1)
-- Channel is the Sensor subtype of Stream (table-per-type): mint a Stream row
-- (StreamKind_ID=1 Sensor) whose Stream_ID becomes the Channel PK.
INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (1); SET @CH_Turb = SCOPE_IDENTITY();
INSERT INTO [dbo].[Channel] ([Stream_ID], [SignalInterface_ID], [TagName], [Parameter_ID], [DataProvenanceKind_ID], [ValueKind_ID], [Unit_ID])
VALUES (@CH_Turb, @SI_ID, N'TEST_Turb-001/Turbidity', 9, 1, 1, 2);

INSERT INTO [dbo].[EquipmentWiringHistory] ([Equipment_ID], [SignalInterface_ID], [ValidFrom])
VALUES (@EQ_Turb, @SI_ID, '2026-01-01T00:00:00');

INSERT INTO [dbo].[EquipmentLocationHistory] ([Equipment_ID], [SamplingPoint_ID], [ValidFrom], [Campaign_ID])
VALUES (@EQ_Turb, @SP_AerobicOut, '2026-01-01T00:00:00', @CampOpsID);

-- ============================================================
-- Turbidity observations: hourly, 2026-04-01 → 2026-06-10
-- Value: 5 + 3·sin(h·0.15) + 1.5·sin(h·0.05) + 0.5·sin(h·0.5)  NTU
-- 1 680 rows (70 days × 24 h)
-- ============================================================
CREATE TABLE #turb_ts (i INT, ts DATETIME2(7));

WITH n AS (SELECT 0 AS i UNION ALL SELECT i+1 FROM n WHERE i < 1679)
INSERT INTO #turb_ts (i, ts)
SELECT i, DATEADD(HOUR, i, '2026-04-01T00:00:00') FROM n OPTION (MAXRECURSION 0);

DECLARE @TurbObs TABLE (obs_id INT, ts DATETIME2(7));

INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID])
OUTPUT INSERTED.[Observation_ID], INSERTED.[Timestamp] INTO @TurbObs (obs_id, ts)
SELECT @CH_Turb, NULL, ts, 1 FROM #turb_ts ORDER BY i;

INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode])
SELECT
    obs_id,
    5.0
        + 3.0 * SIN(CAST(DATEDIFF(HOUR, '2026-04-01T00:00:00', ts) AS FLOAT) * 0.15)
        + 1.5 * SIN(CAST(DATEDIFF(HOUR, '2026-04-01T00:00:00', ts) AS FLOAT) * 0.05)
        + 0.5 * SIN(CAST(DATEDIFF(HOUR, '2026-04-01T00:00:00', ts) AS FLOAT) * 0.50),
    1
FROM @TurbObs;

DROP TABLE #turb_ts;

-- ============================================================
-- Lab COD at Influent: 10 weekly grab samples, 2026-04-07 → 2026-06-09
-- Weeks 7-10 (2026-05-19 → 2026-06-09) fall within the default
-- "last 30 days" explore window alongside the Turbidity data.
-- ============================================================
DECLARE @ExpCOD_Inf INT;

INSERT INTO [dbo].[LabExperiment] ([Name], [Campaign_ID], [ExperimentDateTime], [Description], [CreatedByPerson_ID])
VALUES (N'TEST_ COD influent weekly series', @CampOpsID, '2026-06-09T09:00:00', N'Weekly influent COD grab samples', @PersonProfID);
SET @ExpCOD_Inf = SCOPE_IDENTITY();

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID],[SampledByPerson_ID],[Campaign_ID],[SampleDateTimeStart]) VALUES (@SP_Influent,@PersonTechID,@CampOpsID,'2026-04-07T08:00:00'); SET @SmpID=SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID],[AnalysisSeries_ID],[Sample_ID],[Replicate],[QualityCode_ID],[Laboratory_ID],[AnalystPerson_ID],[AnalysisDateTime]) VALUES (@ExpCOD_Inf,@AS_COD_Inf,@SmpID,1,1,1,@PersonTechID,'2026-04-08T09:00:00'); SET @LaID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID]) VALUES (NULL,@LaID,'2026-04-07T08:00:00',1); SET @ObsID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode]) VALUES (@ObsID,312.0,1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID],[SampledByPerson_ID],[Campaign_ID],[SampleDateTimeStart]) VALUES (@SP_Influent,@PersonTechID,@CampOpsID,'2026-04-14T08:00:00'); SET @SmpID=SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID],[AnalysisSeries_ID],[Sample_ID],[Replicate],[QualityCode_ID],[Laboratory_ID],[AnalystPerson_ID],[AnalysisDateTime]) VALUES (@ExpCOD_Inf,@AS_COD_Inf,@SmpID,1,1,1,@PersonTechID,'2026-04-15T09:00:00'); SET @LaID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID]) VALUES (NULL,@LaID,'2026-04-14T08:00:00',1); SET @ObsID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode]) VALUES (@ObsID,285.0,1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID],[SampledByPerson_ID],[Campaign_ID],[SampleDateTimeStart]) VALUES (@SP_Influent,@PersonTechID,@CampOpsID,'2026-04-21T08:00:00'); SET @SmpID=SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID],[AnalysisSeries_ID],[Sample_ID],[Replicate],[QualityCode_ID],[Laboratory_ID],[AnalystPerson_ID],[AnalysisDateTime]) VALUES (@ExpCOD_Inf,@AS_COD_Inf,@SmpID,1,1,1,@PersonTechID,'2026-04-22T09:00:00'); SET @LaID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID]) VALUES (NULL,@LaID,'2026-04-21T08:00:00',1); SET @ObsID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode]) VALUES (@ObsID,340.0,1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID],[SampledByPerson_ID],[Campaign_ID],[SampleDateTimeStart]) VALUES (@SP_Influent,@PersonTechID,@CampOpsID,'2026-04-28T08:00:00'); SET @SmpID=SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID],[AnalysisSeries_ID],[Sample_ID],[Replicate],[QualityCode_ID],[Laboratory_ID],[AnalystPerson_ID],[AnalysisDateTime]) VALUES (@ExpCOD_Inf,@AS_COD_Inf,@SmpID,1,1,1,@PersonTechID,'2026-04-29T09:00:00'); SET @LaID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID]) VALUES (NULL,@LaID,'2026-04-28T08:00:00',1); SET @ObsID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode]) VALUES (@ObsID,298.0,1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID],[SampledByPerson_ID],[Campaign_ID],[SampleDateTimeStart]) VALUES (@SP_Influent,@PersonTechID,@CampOpsID,'2026-05-05T08:00:00'); SET @SmpID=SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID],[AnalysisSeries_ID],[Sample_ID],[Replicate],[QualityCode_ID],[Laboratory_ID],[AnalystPerson_ID],[AnalysisDateTime]) VALUES (@ExpCOD_Inf,@AS_COD_Inf,@SmpID,1,1,1,@PersonTechID,'2026-05-06T09:00:00'); SET @LaID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID]) VALUES (NULL,@LaID,'2026-05-05T08:00:00',1); SET @ObsID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode]) VALUES (@ObsID,325.0,1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID],[SampledByPerson_ID],[Campaign_ID],[SampleDateTimeStart]) VALUES (@SP_Influent,@PersonTechID,@CampOpsID,'2026-05-12T08:00:00'); SET @SmpID=SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID],[AnalysisSeries_ID],[Sample_ID],[Replicate],[QualityCode_ID],[Laboratory_ID],[AnalystPerson_ID],[AnalysisDateTime]) VALUES (@ExpCOD_Inf,@AS_COD_Inf,@SmpID,1,1,1,@PersonTechID,'2026-05-13T09:00:00'); SET @LaID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID]) VALUES (NULL,@LaID,'2026-05-12T08:00:00',1); SET @ObsID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode]) VALUES (@ObsID,278.0,1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID],[SampledByPerson_ID],[Campaign_ID],[SampleDateTimeStart]) VALUES (@SP_Influent,@PersonTechID,@CampOpsID,'2026-05-19T08:00:00'); SET @SmpID=SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID],[AnalysisSeries_ID],[Sample_ID],[Replicate],[QualityCode_ID],[Laboratory_ID],[AnalystPerson_ID],[AnalysisDateTime]) VALUES (@ExpCOD_Inf,@AS_COD_Inf,@SmpID,1,1,1,@PersonTechID,'2026-05-20T09:00:00'); SET @LaID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID]) VALUES (NULL,@LaID,'2026-05-19T08:00:00',1); SET @ObsID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode]) VALUES (@ObsID,350.0,1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID],[SampledByPerson_ID],[Campaign_ID],[SampleDateTimeStart]) VALUES (@SP_Influent,@PersonTechID,@CampOpsID,'2026-05-26T08:00:00'); SET @SmpID=SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID],[AnalysisSeries_ID],[Sample_ID],[Replicate],[QualityCode_ID],[Laboratory_ID],[AnalystPerson_ID],[AnalysisDateTime]) VALUES (@ExpCOD_Inf,@AS_COD_Inf,@SmpID,1,1,1,@PersonTechID,'2026-05-27T09:00:00'); SET @LaID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID]) VALUES (NULL,@LaID,'2026-05-26T08:00:00',1); SET @ObsID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode]) VALUES (@ObsID,301.0,1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID],[SampledByPerson_ID],[Campaign_ID],[SampleDateTimeStart]) VALUES (@SP_Influent,@PersonTechID,@CampOpsID,'2026-06-02T08:00:00'); SET @SmpID=SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID],[AnalysisSeries_ID],[Sample_ID],[Replicate],[QualityCode_ID],[Laboratory_ID],[AnalystPerson_ID],[AnalysisDateTime]) VALUES (@ExpCOD_Inf,@AS_COD_Inf,@SmpID,1,1,1,@PersonTechID,'2026-06-03T09:00:00'); SET @LaID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID]) VALUES (NULL,@LaID,'2026-06-02T08:00:00',1); SET @ObsID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode]) VALUES (@ObsID,315.0,1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID],[SampledByPerson_ID],[Campaign_ID],[SampleDateTimeStart]) VALUES (@SP_Influent,@PersonTechID,@CampOpsID,'2026-06-09T08:00:00'); SET @SmpID=SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID],[AnalysisSeries_ID],[Sample_ID],[Replicate],[QualityCode_ID],[Laboratory_ID],[AnalystPerson_ID],[AnalysisDateTime]) VALUES (@ExpCOD_Inf,@AS_COD_Inf,@SmpID,1,1,1,@PersonTechID,'2026-06-10T09:00:00'); SET @LaID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID]) VALUES (NULL,@LaID,'2026-06-09T08:00:00',1); SET @ObsID=SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode]) VALUES (@ObsID,289.0,1);

-- ============================================================
-- Provenance showcase DAG (Data Explorer "Provenance" panel)
-- Builds a processing chain off the raw Turbidity sensor channel (@CH_Turb):
--   raw  --(S1 OutlierRemoval)-->  outlier-free  --(S2 Smoothing)-->  smoothed
--   smoothed + lab Turbidity grabs  --(S3 Interpolation gap-fill)-->  reconstructed
-- Exercises: derived channels (SignalInterface NULL, ProducedByStep set), the
-- accumulated ChannelTrait set, a multi-input step fusing a sensor + a lab series,
-- and forward/backward lineage. Each derived channel carries its own observations
-- (projected from the raw series) so it can be overlaid on the plot.
-- OperationKind IDs: 1 Unprocessed, 2 OutlierRemoval, 5 Smoothing, 6 Interpolation.
-- ============================================================
DECLARE @S1 INT, @S2 INT, @S3 INT;
DECLARE @CH_Clean INT, @CH_Smooth INT, @CH_Recon INT, @AS_TurbLab INT;

-- Raw sensor channel carries the single Unprocessed trait (ADR 0005).
INSERT INTO [dbo].[ChannelTrait] ([Stream_ID], [OperationKind_ID]) VALUES (@CH_Turb, 1);

-- --- Step S1: outlier removal -> outlier-free channel ---------------------
INSERT INTO [dbo].[ProcessingStep] ([Name],[Description],[MethodName],[MethodVersion],[OperationKind_ID],[MethodParameters],[ExecutedDateTime],[ExecutedByPerson_ID])
VALUES (N'TEST_ Turbidity outlier removal', N'MAD-based spike removal on raw turbidity', N'mad_outlier_removal', N'meteaudata 0.5.1', 2, N'{"window": 24, "threshold": 3.5}', '2026-05-02T14:03:00', @PersonProfID);
SET @S1 = SCOPE_IDENTITY();

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (1); SET @CH_Clean = SCOPE_IDENTITY();
INSERT INTO [dbo].[Channel] ([Stream_ID],[SignalInterface_ID],[TagName],[Parameter_ID],[DataProvenanceKind_ID],[ProducedByStep_ID],[ParentChannel_ID],[ValueKind_ID],[Unit_ID])
VALUES (@CH_Clean, NULL, N'TEST_Turb-001/Turbidity::outlier_free', 9, 7, @S1, @CH_Turb, 1, 2);
INSERT INTO [dbo].[ProcessingLineage] ([ProcessingStep_ID],[Stream_ID]) VALUES (@S1, @CH_Turb);
INSERT INTO [dbo].[ChannelTrait] ([Stream_ID],[OperationKind_ID]) VALUES (@CH_Clean, 2);

-- --- Step S2: smoothing -> smoothed channel ------------------------------
INSERT INTO [dbo].[ProcessingStep] ([Name],[Description],[MethodName],[MethodVersion],[OperationKind_ID],[MethodParameters],[ExecutedDateTime],[ExecutedByPerson_ID])
VALUES (N'TEST_ Turbidity smoothing', N'Centred moving-average smoothing', N'moving_average', N'meteaudata 0.5.1', 5, N'{"window": 6}', '2026-05-02T14:05:00', NULL);
SET @S2 = SCOPE_IDENTITY();

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (1); SET @CH_Smooth = SCOPE_IDENTITY();
INSERT INTO [dbo].[Channel] ([Stream_ID],[SignalInterface_ID],[TagName],[Parameter_ID],[DataProvenanceKind_ID],[ProducedByStep_ID],[ParentChannel_ID],[ValueKind_ID],[Unit_ID])
VALUES (@CH_Smooth, NULL, N'TEST_Turb-001/Turbidity::smoothed', 9, 7, @S2, @CH_Clean, 1, 2);
INSERT INTO [dbo].[ProcessingLineage] ([ProcessingStep_ID],[Stream_ID]) VALUES (@S2, @CH_Clean);
INSERT INTO [dbo].[ChannelTrait] ([Stream_ID],[OperationKind_ID]) VALUES (@CH_Smooth, 2), (@CH_Smooth, 5);

-- --- Lab Turbidity grab series at the Aerobic outlet (fusion anchor) ------
INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (2); SET @AS_TurbLab = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeries] ([Stream_ID],[Name],[Parameter_ID],[SamplingPoint_ID],[ValueKind_ID],[Unit_ID],[Campaign_ID])
VALUES (@AS_TurbLab, N'TEST_ Turbidity grab at Aerobic outlet', 9, @SP_AerobicOut, 1, 2, @CampOpsID);

DECLARE @ExpTurbLab INT;
INSERT INTO [dbo].[LabExperiment] ([Name],[Campaign_ID],[ExperimentDateTime],[Description],[CreatedByPerson_ID])
VALUES (N'TEST_ Turbidity grab series', @CampOpsID, '2026-06-09T09:00:00', N'Weekly turbidity grab samples for sensor reconciliation', @PersonProfID);
SET @ExpTurbLab = SCOPE_IDENTITY();

DECLARE @i INT = 0;
WHILE @i < 6
BEGIN
    DECLARE @gts DATETIME2(7) = DATEADD(DAY, 7 * @i, '2026-05-05T08:00:00');
    DECLARE @gval FLOAT = 5.0 + 0.8 * SIN(@i * 0.9);  -- ~4.2..5.8 NTU
    INSERT INTO [dbo].[Sample] ([SamplingPoint_ID],[SampledByPerson_ID],[Campaign_ID],[SampleDateTimeStart]) VALUES (@SP_AerobicOut,@PersonTechID,@CampOpsID,@gts); SET @SmpID=SCOPE_IDENTITY();
    INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID],[AnalysisSeries_ID],[Sample_ID],[Replicate],[QualityCode_ID],[Laboratory_ID],[AnalystPerson_ID],[AnalysisDateTime]) VALUES (@ExpTurbLab,@AS_TurbLab,@SmpID,1,1,1,@PersonTechID,DATEADD(DAY,1,@gts)); SET @LaID=SCOPE_IDENTITY();
    INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID]) VALUES (NULL,@LaID,@gts,1); SET @ObsID=SCOPE_IDENTITY();
    INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode]) VALUES (@ObsID,@gval,1);
    SET @i = @i + 1;
END

-- --- Step S3: lab-anchored gap-fill (multi-input) -> reconstructed channel
INSERT INTO [dbo].[ProcessingStep] ([Name],[Description],[MethodName],[MethodVersion],[OperationKind_ID],[MethodParameters],[ExecutedDateTime],[ExecutedByPerson_ID])
VALUES (N'TEST_ Turbidity lab-anchored gap-fill', N'Gap-fill smoothed sensor data anchored on lab grabs', N'lab_anchored_gapfill', N'meteaudata 0.6.0', 6, N'{"max_gap_h": 12}', '2026-05-03T09:20:00', @PersonProfID);
SET @S3 = SCOPE_IDENTITY();

INSERT INTO [dbo].[Stream] ([StreamKind_ID]) VALUES (1); SET @CH_Recon = SCOPE_IDENTITY();
INSERT INTO [dbo].[Channel] ([Stream_ID],[SignalInterface_ID],[TagName],[Parameter_ID],[DataProvenanceKind_ID],[ProducedByStep_ID],[ParentChannel_ID],[ValueKind_ID],[Unit_ID])
VALUES (@CH_Recon, NULL, N'TEST_Turb-001/Turbidity::reconstructed', 9, 7, @S3, @CH_Smooth, 1, 2);
INSERT INTO [dbo].[ProcessingLineage] ([ProcessingStep_ID],[Stream_ID]) VALUES (@S3, @CH_Smooth), (@S3, @AS_TurbLab);
INSERT INTO [dbo].[ChannelTrait] ([Stream_ID],[OperationKind_ID]) VALUES (@CH_Recon, 2), (@CH_Recon, 5), (@CH_Recon, 6);

-- --- Derived observations: project the raw turbidity series onto each channel
SELECT
    o.[Timestamp] AS ts,
    v.[Value]     AS raw_val,
    AVG(v.[Value]) OVER (ORDER BY o.[Timestamp] ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING) AS smooth_val
INTO #turb_deriv
FROM [dbo].[Observation] o
JOIN [dbo].[Value] v ON v.[Observation_ID] = o.[Observation_ID]
WHERE o.[Channel_ID] = @CH_Turb;

-- outlier-free: copy raw values
DECLARE @CleanObs TABLE (obs_id INT, ts DATETIME2(7));
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID])
OUTPUT INSERTED.[Observation_ID], INSERTED.[Timestamp] INTO @CleanObs (obs_id, ts)
SELECT @CH_Clean, NULL, ts, 1 FROM #turb_deriv;
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode])
SELECT c.obs_id, d.raw_val, 1 FROM @CleanObs c JOIN #turb_deriv d ON d.ts = c.ts;

-- smoothed: centred moving average
DECLARE @SmoothObs TABLE (obs_id INT, ts DATETIME2(7));
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID])
OUTPUT INSERTED.[Observation_ID], INSERTED.[Timestamp] INTO @SmoothObs (obs_id, ts)
SELECT @CH_Smooth, NULL, ts, 1 FROM #turb_deriv;
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode])
SELECT s.obs_id, d.smooth_val, 1 FROM @SmoothObs s JOIN #turb_deriv d ON d.ts = s.ts;

-- reconstructed: smoothed values (lab-anchored gap-fill leaves dense regions intact)
DECLARE @ReconObs TABLE (obs_id INT, ts DATETIME2(7));
INSERT INTO [dbo].[Observation] ([Channel_ID],[LabAnalysis_ID],[Timestamp],[ValueKind_ID])
OUTPUT INSERTED.[Observation_ID], INSERTED.[Timestamp] INTO @ReconObs (obs_id, ts)
SELECT @CH_Recon, NULL, ts, 1 FROM #turb_deriv;
INSERT INTO [dbo].[Value] ([Observation_ID],[Value],[QualityCode])
SELECT r.obs_id, d.smooth_val, 1 FROM @ReconObs r JOIN #turb_deriv d ON d.ts = r.ts;

DROP TABLE #turb_deriv;

PRINT 'Demo seed loaded: 3 persons, 1 site, 6 process units, 6 sampling points, 2 campaigns, 17 analysis series, 1 lab panel, scalar COD (final eff + influent) + vector UV-Vis + vector ViCAs settling-velocity + matrix fluorescence-EEM lab data + 1 Turbidity sensor chain (1 680 hourly obs, Apr-Jun 2026) + 10 COD influent grab samples + provenance showcase DAG (3 derived Turbidity channels + lab grab series across 3 processing steps).';
