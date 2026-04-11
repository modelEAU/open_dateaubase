-- Seed data for schema v1.3.0
-- Phase 2b: Lab Data Support — Laboratory, Sample, Campaign junction tables

-- =============================================================================
-- Laboratory
-- =============================================================================

-- On-site water quality lab at Site 1
INSERT INTO [dbo].[Laboratory] ([Name], [Site_ID], [Description])
VALUES (N'ModelEAU Water Quality Lab', 1, N'Primary on-site laboratory for physicochemical analysis');
-- Laboratory_ID = 1

-- =============================================================================
-- Sample (uses existing Person and SamplingPoints from seed_v1.0.0)
-- =============================================================================

-- Grab sample taken by the first person (Person_ID=1) at SamplingPoints ID=1
-- as part of Campaign_ID=2 (TSS Validation Study from seed_v1.2.0)
INSERT INTO [dbo].[Sample]
    ([Sampling_point_ID], [SampledByPerson_ID], [Campaign_ID],
     [SampleDateTimeStart], [SampleDateTimeEnd], [SampleType], [SampleEquipment_ID], [Description])
VALUES
    (1, 1, 2,
     '2025-03-15T08:00:00', NULL, 'Grab', NULL,
     N'Morning grab sample for TSS validation');
-- Sample_ID = 1

-- =============================================================================
-- Campaign junction tables (using seed_v1.2.0 campaigns)
-- =============================================================================

-- Campaign 1 (Operations) uses SamplingPoint 1
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [Sampling_point_ID], [Role])
VALUES (1, 1, N'Primary');

-- Campaign 2 (TSS Validation Study) uses SamplingPoint 1
INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [Sampling_point_ID], [Role])
VALUES (2, 1, N'Primary');

-- Campaign 1 uses Equipment 1 (from seed_v1.0.0)
INSERT INTO [dbo].[CampaignEquipment] ([Campaign_ID], [Equipment_ID], [Role])
VALUES (1, 1, N'Primary sensor');

-- Campaign 2 uses Equipment 1
INSERT INTO [dbo].[CampaignEquipment] ([Campaign_ID], [Equipment_ID], [Role])
VALUES (2, 1, N'Reference sensor');

-- Campaign 1 uses Parameter 1 (from seed_v1.0.0)
INSERT INTO [dbo].[CampaignParameter] ([Campaign_ID], [Parameter_ID])
VALUES (1, 1);

-- Campaign 2 uses Parameter 1
INSERT INTO [dbo].[CampaignParameter] ([Campaign_ID], [Parameter_ID])
VALUES (2, 1);
