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
--   - seed_fixtures.sql     — Watershed_ID 1, Laboratory_ID 1
--
-- ID anchors used (must not change):
--   Unit:          mg/L=1  NTU=2  pH units=3  °C=4
--   Parameter:     TSS=1  COD=2  pH=3  Temp=4  DO=8  Turb=9  NH4-N=11  NO3-N=12  CODf=13
--   ValueKind:     Scalar=1
--   ProcessingKind: Raw=1
--   SiteKind:      Experimental WWTP=12
--   CampaignKind:  Experiment=1  Operations=2
--   ProcessUnitKind: Area=1  Zone=2  Basin=9  Clarifier=8
-- ============================================================

SET NOCOUNT ON;

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
    1,                                        -- TEST_Rivière Saint-Charles watershed
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
    [CampaignKind_ID], [Site_ID], [Name], [Description],
    [CampaignStartDateTime], [ResponsiblePerson_ID]
)
VALUES (
    2,      -- Operations
    @SiteID,
    N'TEST_ Routine Operations 2026',
    N'TEST campaign — ongoing routine monitoring of the pilot WWTP',
    '2026-01-01T00:00:00',
    @PersonTechID
);
SET @CampOpsID = SCOPE_IDENTITY();

INSERT INTO [dbo].[Campaign] (
    [CampaignKind_ID], [Site_ID], [Name], [Description],
    [CampaignStartDateTime], [CampaignEndDateTime], [ResponsiblePerson_ID]
)
VALUES (
    1,      -- Experiment
    @SiteID,
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
-- AnalysisSeries (9 rows — lab-analysable parameters only)
--
-- All Scalar (ValueKind_ID=1), Raw (ProcessingKind_ID=1)
-- ============================================================
DECLARE @AS_TSS_Inf    INT, @AS_COD_Inf    INT, @AS_CODf_Inf   INT, @AS_NH4_Inf   INT,
        @AS_TSS_Eff    INT, @AS_COD_Eff    INT, @AS_CODf_Eff   INT,
        @AS_NH4_Eff    INT, @AS_NO3_Eff    INT;

-- Ops campaign: routine inlet + outlet monitoring (4 influent + 5 effluent)
INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ TSS at Influent', 1, @SP_Influent, 1, 1, 1, @CampOpsID);       -- TSS, mg/L
SET @AS_TSS_Inf = SCOPE_IDENTITY();

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ COD at Influent', 2, @SP_Influent, 1, 1, 1, @CampOpsID);       -- COD, mg/L
SET @AS_COD_Inf = SCOPE_IDENTITY();

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ CODf at Influent', 13, @SP_Influent, 1, 1, 1, @CampOpsID);     -- COD filtered, mg/L
SET @AS_CODf_Inf = SCOPE_IDENTITY();

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ NH4-N at Influent', 11, @SP_Influent, 1, 1, 1, @CampOpsID);    -- NH4-N, mg/L
SET @AS_NH4_Inf = SCOPE_IDENTITY();

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ TSS at Final effluent', 1, @SP_FinalEff, 1, 1, 1, @CampOpsID); -- TSS, mg/L
SET @AS_TSS_Eff = SCOPE_IDENTITY();

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ COD at Final effluent', 2, @SP_FinalEff, 1, 1, 1, @CampOpsID); -- COD, mg/L
SET @AS_COD_Eff = SCOPE_IDENTITY();

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ CODf at Final effluent', 13, @SP_FinalEff, 1, 1, 1, @CampOpsID); -- COD filtered, mg/L
SET @AS_CODf_Eff = SCOPE_IDENTITY();

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ NH4-N at Final effluent', 11, @SP_FinalEff, 1, 1, 1, @CampOpsID); -- NH4-N, mg/L
SET @AS_NH4_Eff = SCOPE_IDENTITY();

-- Experiment campaign: effluent NO3-N + intermediate points (4 extra series)
INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ NO3-N at Final effluent', 12, @SP_FinalEff, 1, 1, 1, @CampExpID); -- NO3-N, mg/L
SET @AS_NO3_Eff = SCOPE_IDENTITY();

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ TSS at Primary effluent', 1, @SP_PrimEff, 1, 1, 1, @CampExpID);   -- TSS, mg/L

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ NH4-N at Anoxic zone outlet', 11, @SP_AnoxicOut, 1, 1, 1, @CampExpID); -- NH4-N, mg/L

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ NO3-N at Anoxic zone outlet', 12, @SP_AnoxicOut, 1, 1, 1, @CampExpID); -- NO3-N, mg/L

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ NH4-N at Aerobic zone outlet', 11, @SP_AerobicOut, 1, 1, 1, @CampExpID); -- NH4-N, mg/L

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ Sludge microscopy at Bioreactor 4', 16, @SP_BR4, 4, 11, 1, @CampExpID); -- floc_morphology, Image, dimensionless

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
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpCOD, @AS_COD_Eff, @SmpID, 1, 1, 1, @PersonTechID, '2024-02-06T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2024-02-04T16:00:00', 1); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode]) VALUES (@ObsID, 46.0, 1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampOpsID, '2024-02-04T22:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpCOD, @AS_COD_Eff, @SmpID, 1, 1, 1, @PersonTechID, '2024-02-06T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2024-02-04T22:00:00', 1); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode]) VALUES (@ObsID, 53.0, 1);

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampOpsID, '2024-02-05T04:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpCOD, @AS_COD_Eff, @SmpID, 1, 1, 1, @PersonTechID, '2024-02-06T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2024-02-05T04:00:00', 1); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode]) VALUES (@ObsID, 39.0, 1);

-- last grab carries two replicates at the same collection time (plotted as two points)
INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampOpsID, '2024-02-05T10:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpCOD, @AS_COD_Eff, @SmpID, 1, 1, 1, @PersonTechID, '2024-02-06T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2024-02-05T10:00:00', 1); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Value] ([Observation_ID], [Value], [QualityCode]) VALUES (@ObsID, 61.0, 1);
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpCOD, @AS_COD_Eff, @SmpID, 2, 1, 1, @PersonTechID, '2024-02-06T09:00:00'); SET @LaID = SCOPE_IDENTITY();
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

INSERT INTO [dbo].[AnalysisSeries] ([Name], [Parameter_ID], [SamplingPoint_ID], [ValueKind_ID], [Unit_ID], [ProcessingKind_ID], [Campaign_ID])
VALUES (N'TEST_ Lab absorbance spectrum at Final effluent', 10, @SP_FinalEff, 2, 10, 1, @CampExpID); -- absorbance, AU, Vector
SET @AS_AbsVec = SCOPE_IDENTITY();
INSERT INTO [dbo].[AnalysisSeriesAxis] ([AnalysisSeries_ID], [AxisRole], [ValueBinningAxis_ID]) VALUES (@AS_AbsVec, 0, @LabUVAxis);

INSERT INTO [dbo].[LabExperiment] ([Name], [Campaign_ID], [ExperimentDateTime], [Description], [CreatedByPerson_ID])
VALUES (N'TEST_ Lab UV-Vis spectra', @CampExpID, '2026-02-18T09:00:00', N'Bench UV-Vis scans of final-effluent grabs', @PersonProfID);
SET @ExpAbs = SCOPE_IDENTITY();

-- 3 spectra at sample-collection times in the UV-Vis sensor window; the peak
-- bin shifts per sample. ValueVector rows are generated set-based from the axis.
INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampExpID, '2026-02-16T23:50:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpAbs, @AS_AbsVec, @SmpID, 1, 1, 1, @PersonTechID, '2026-02-18T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2026-02-16T23:50:00', 2); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueVector] ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
SELECT @ObsID, vb.[ValueBin_ID], ROUND(EXP(-POWER(CAST(vb.[BinIndex] AS FLOAT) - 1.0, 2) / 2.0), 4), 1
FROM [dbo].[ValueBin] vb WHERE vb.[ValueBinningAxis_ID] = @LabUVAxis;

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampExpID, '2026-02-17T01:00:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpAbs, @AS_AbsVec, @SmpID, 1, 1, 1, @PersonTechID, '2026-02-18T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2026-02-17T01:00:00', 2); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueVector] ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
SELECT @ObsID, vb.[ValueBin_ID], ROUND(EXP(-POWER(CAST(vb.[BinIndex] AS FLOAT) - 2.5, 2) / 2.0), 4), 1
FROM [dbo].[ValueBin] vb WHERE vb.[ValueBinningAxis_ID] = @LabUVAxis;

INSERT INTO [dbo].[Sample] ([SamplingPoint_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart]) VALUES (@SP_FinalEff, @PersonTechID, @CampExpID, '2026-02-17T02:30:00'); SET @SmpID = SCOPE_IDENTITY();
INSERT INTO [dbo].[LabAnalysis] ([LabExperiment_ID], [AnalysisSeries_ID], [Sample_ID], [Replicate], [QualityCode_ID], [Laboratory_ID], [AnalystPerson_ID], [AnalysisDateTime]) VALUES (@ExpAbs, @AS_AbsVec, @SmpID, 1, 1, 1, @PersonTechID, '2026-02-18T09:00:00'); SET @LaID = SCOPE_IDENTITY();
INSERT INTO [dbo].[Observation] ([Channel_ID], [LabAnalysis_ID], [Timestamp], [ValueKind_ID]) VALUES (NULL, @LaID, '2026-02-17T02:30:00', 2); SET @ObsID = SCOPE_IDENTITY();
INSERT INTO [dbo].[ValueVector] ([Observation_ID], [ValueBin_ID], [Value], [QualityCode])
SELECT @ObsID, vb.[ValueBin_ID], ROUND(EXP(-POWER(CAST(vb.[BinIndex] AS FLOAT) - 4.0, 2) / 2.0), 4), 1
FROM [dbo].[ValueBin] vb WHERE vb.[ValueBinningAxis_ID] = @LabUVAxis;

PRINT 'Demo seed loaded: 3 persons, 1 site (TEST_pilEAUte WWTP), 6 process units, 6 sampling points, 2 campaigns, 15 analysis series (14 scalar/image + 1 vector absorbance), 1 lab panel (TEST_ WWTP Weekly Panel), plus lab measurements (5 scalar COD @ Feb 2024 incl. a replicate, 3 UV-Vis spectra @ Feb 2026).';
