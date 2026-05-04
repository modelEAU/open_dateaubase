-- v4.2.0: Add DASLocationHistory table for tracking DAS deployments across sites.
-- Rollback: v4.2.0_add_das_location_history_rollback.sql

CREATE TABLE [dbo].[DASLocationHistory] (
    [DASLocationHistory_ID]      INT           IDENTITY(1,1) NOT NULL,
    [DataAcquisitionSystem_ID]   INT           NOT NULL,
    [Site_ID]                    INT           NOT NULL,
    [Campaign_ID]                INT           NULL,
    [ValidFrom]                  DATETIME2(7)  NOT NULL,
    [ValidTo]                    DATETIME2(7)  NULL,
    [Notes]                      NVARCHAR(MAX) NULL,

    CONSTRAINT [PK_DASLocationHistory]
        PRIMARY KEY CLUSTERED ([DASLocationHistory_ID]),

    CONSTRAINT [FK_DASLocationHistory_DAS]
        FOREIGN KEY ([DataAcquisitionSystem_ID])
        REFERENCES [dbo].[DataAcquisitionSystem] ([DataAcquisitionSystem_ID]),

    CONSTRAINT [FK_DASLocationHistory_Site]
        FOREIGN KEY ([Site_ID])
        REFERENCES [dbo].[Site] ([Site_ID]),

    CONSTRAINT [FK_DASLocationHistory_Campaign]
        FOREIGN KEY ([Campaign_ID])
        REFERENCES [dbo].[Campaign] ([Campaign_ID])
);

-- At most one active (ValidTo IS NULL) row per DAS.
CREATE UNIQUE INDEX [UQ_DASLocationHistory_ActivePerDAS]
    ON [dbo].[DASLocationHistory] ([DataAcquisitionSystem_ID])
    WHERE [ValidTo] IS NULL;

-- Supports "what DAS was at this site when?" queries.
CREATE INDEX [IX_DASLocationHistory_Site_ValidFrom]
    ON [dbo].[DASLocationHistory] ([Site_ID], [ValidFrom]);
