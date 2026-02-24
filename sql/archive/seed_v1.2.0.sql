-- Seed data for schema v1.2.0
-- Phase 2a: Campaign, DataProvenance, and Person sample records
-- (CampaignType and DataProvenance seed data is in the migration script itself)

-- =============================================================================
-- Sample Person records (migrated from Contact)
-- =============================================================================
-- After the migration, existing Contact rows become Person rows with Person_ID.
-- The seed data below inserts new persons for testing purposes.
-- In production, existing Contact rows are preserved by the migration.

-- =============================================================================
-- Sample Site (re-use existing Site_ID=1 from seed_v1.0.0)
-- =============================================================================

-- =============================================================================
-- Sample Campaigns
-- =============================================================================

-- Ongoing operations campaign at Site 1
INSERT INTO [dbo].[Campaign] ([CampaignType_ID], [Site_ID], [Name], [Description], [StartDate], [EndDate], [Project_ID])
VALUES (
    2,                      -- Operations
    1,                      -- Site 1 (from seed_v1.0.0)
    N'Ongoing Operations 2025',
    N'Continuous monitoring of the primary site during 2025',
    '2025-01-01T00:00:00',
    NULL,
    NULL
);
-- Campaign_ID = 1

-- Experiment campaign
INSERT INTO [dbo].[Campaign] ([CampaignType_ID], [Site_ID], [Name], [Description], [StartDate], [EndDate], [Project_ID])
VALUES (
    1,                      -- Experiment
    1,                      -- Site 1
    N'TSS Validation Study 2025',
    N'Parallel sensor vs. lab validation for TSS measurement at primary effluent',
    '2025-03-01T00:00:00',
    '2025-06-30T00:00:00',
    NULL
);
-- Campaign_ID = 2
