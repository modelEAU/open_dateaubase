-- Baseline CREATE script for schema v3.0.0
-- Platform: mssql
-- Generated: 2026-03-30

-- ============================================================
-- Lookup / root tables (no FKs to other user tables)
-- ============================================================

CREATE TABLE [dbo].[AnnotationType] (
    [AnnotationType_ID] INT NOT NULL,
    [AnnotationTypeName] NVARCHAR(100) NOT NULL,
    [Description] NVARCHAR(500),
    [Color] NVARCHAR(7),
    CONSTRAINT [PK_AnnotationType] PRIMARY KEY ([AnnotationType_ID])
);

CREATE TABLE [dbo].[CampaignType] (
    [CampaignType_ID] INT IDENTITY(1,1) NOT NULL,
    [CampaignType_Name] NVARCHAR(100) NOT NULL,
    CONSTRAINT [PK_CampaignType] PRIMARY KEY ([CampaignType_ID])
);

CREATE TABLE [dbo].[ControlLoopPortRole] (
    [ControlLoopPortRole_ID] INT          NOT NULL,
    [Name]                   NVARCHAR(50) NOT NULL,
    [Description]            NVARCHAR(200) NULL,
    CONSTRAINT [PK_ControlLoopPortRole] PRIMARY KEY ([ControlLoopPortRole_ID])
);

CREATE TABLE [dbo].[ControlVariableType] (
    [ControlVariableType_ID] INT          NOT NULL,
    [Name]                   NVARCHAR(50) NOT NULL,
    [Description]            NVARCHAR(200) NULL,
    CONSTRAINT [PK_ControlVariableType] PRIMARY KEY ([ControlVariableType_ID])
);

CREATE TABLE [dbo].[DataProvenance] (
    [DataProvenance_ID] INT IDENTITY(1,1) NOT NULL,
    [DataProvenance_Name] NVARCHAR(50) NOT NULL,
    CONSTRAINT [PK_DataProvenance] PRIMARY KEY ([DataProvenance_ID])
);

CREATE TABLE [dbo].[EquipmentEventType] (
    [EquipmentEventType_ID] INT IDENTITY(1,1) NOT NULL,
    [EquipmentEventType_Name] NVARCHAR(100) NOT NULL,
    CONSTRAINT [PK_EquipmentEventType] PRIMARY KEY ([EquipmentEventType_ID])
);

CREATE TABLE [dbo].[EquipmentModel] (
    [EquipmentModel_ID] INT IDENTITY(1,1) NOT NULL,
    [EquipmentModel] NVARCHAR(100),
    [Method] NVARCHAR(100),
    [Functions] NVARCHAR(MAX),
    [Manufacturer] NVARCHAR(100),
    [ManualLocation] NVARCHAR(100),
    CONSTRAINT [PK_EquipmentModel] PRIMARY KEY ([EquipmentModel_ID])
);

CREATE TABLE [dbo].[Person] (
    [Person_ID] INT IDENTITY(1,1) NOT NULL,
    [LastName] NVARCHAR(100),
    [FirstName] NVARCHAR(255),
    [Company] NVARCHAR(MAX),
    [Role] NVARCHAR(255),
    [Function] NVARCHAR(MAX),
    [Email] NVARCHAR(100),
    [Phone] NVARCHAR(100),
    [Linkedin] NVARCHAR(100),
    [Website] NVARCHAR(60),
    CONSTRAINT [PK_Person] PRIMARY KEY ([Person_ID])
);

CREATE TABLE [dbo].[Procedures] (
    [Procedure_ID] INT IDENTITY(1,1) NOT NULL,
    [ProcedureName] NVARCHAR(100),
    [ProcedureType] NVARCHAR(255),
    [Description] NVARCHAR(MAX),
    [ProcedureLocation] NVARCHAR(100),
    CONSTRAINT [PK_Procedures] PRIMARY KEY ([Procedure_ID])
);

CREATE TABLE [dbo].[ProcessingDegree] (
    [ProcessingDegree_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_ProcessingDegree] PRIMARY KEY ([ProcessingDegree_ID])
);

CREATE TABLE [dbo].[QualityCode] (
    [QualityCode_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    [IsUsable] BIT NOT NULL DEFAULT True,
    CONSTRAINT [PK_QualityCode] PRIMARY KEY ([QualityCode_ID])
);

CREATE TABLE [dbo].[SampleMethod] (
    [SampleMethod_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_SampleMethod] PRIMARY KEY ([SampleMethod_ID])
);

CREATE TABLE [dbo].[SampleType] (
    [SampleType_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_SampleType] PRIMARY KEY ([SampleType_ID])
);

CREATE TABLE [dbo].[SchemaVersion] (
    [VersionID] INT IDENTITY(1,1) NOT NULL,
    [Version] NVARCHAR(20) NOT NULL,
    [AppliedDateTime] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    [Description] NVARCHAR(500),
    [MigrationScript] NVARCHAR(200),
    CONSTRAINT [PK_SchemaVersion] PRIMARY KEY ([VersionID])
);

CREATE TABLE [dbo].[SignalPortType] (
    [SignalPortType_ID] INT          NOT NULL,
    [Name]              NVARCHAR(50) NOT NULL,
    [Description]       NVARCHAR(200) NULL,
    CONSTRAINT [PK_SignalPortType] PRIMARY KEY ([SignalPortType_ID])
);

CREATE TABLE [dbo].[Unit] (
    [Unit_ID] INT IDENTITY(1,1) NOT NULL,
    [Unit] NVARCHAR(100),
    CONSTRAINT [PK_Unit] PRIMARY KEY ([Unit_ID])
);

CREATE TABLE [dbo].[ValueType] (
    [ValueType_ID] INT IDENTITY(1,1) NOT NULL,
    [ValueType_Name] NVARCHAR(50) NOT NULL,
    CONSTRAINT [PK_ValueType] PRIMARY KEY ([ValueType_ID])
);

CREATE TABLE [dbo].[Watershed] (
    [Watershed_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    [SurfaceArea] REAL,
    [ConcentrationTime] INT,
    [ImperviousSurface] REAL,
    CONSTRAINT [PK_Watershed] PRIMARY KEY ([Watershed_ID])
);

-- ============================================================
-- Second-level tables (FK to root tables only)
-- ============================================================

CREATE TABLE [dbo].[Annotation] (
    [Annotation_ID] INT IDENTITY(1,1) NOT NULL,
    [Channel_ID] INT NOT NULL,
    [AnnotationType_ID] INT NOT NULL,
    [StartTime] DATETIME2(7) NOT NULL,
    [EndTime] DATETIME2(7),
    [AuthorPerson_ID] INT,
    [Campaign_ID] INT,
    [EquipmentEvent_ID] INT,
    [Title] NVARCHAR(200),
    [Comment] NVARCHAR(MAX),
    [CreatedDateTime] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    [ModifiedDateTime] DATETIME2(7),
    [Observation_ID] INT,
    CONSTRAINT [PK_Annotation] PRIMARY KEY ([Annotation_ID])
);

CREATE TABLE [dbo].[Campaign] (
    [Campaign_ID] INT IDENTITY(1,1) NOT NULL,
    [CampaignType_ID] INT NOT NULL,
    [Site_ID] INT NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Description] NVARCHAR(2000),
    [CampaignStartDateTime] DATETIME2(7),
    [CampaignEndDateTime] DATETIME2(7),
    CONSTRAINT [PK_Campaign] PRIMARY KEY ([Campaign_ID])
);

CREATE TABLE [dbo].[CampaignEquipment] (
    [Campaign_ID] INT NOT NULL,
    [Equipment_ID] INT NOT NULL,
    [Role] NVARCHAR(100),
    CONSTRAINT [PK_CampaignEquipment] PRIMARY KEY ([Campaign_ID], [Equipment_ID])
);

CREATE TABLE [dbo].[CampaignSamplingLocation] (
    [Campaign_ID] INT NOT NULL,
    [SamplingPoint_ID] INT NOT NULL,
    [Role] NVARCHAR(100),
    CONSTRAINT [PK_CampaignSamplingLocation] PRIMARY KEY ([Campaign_ID], [SamplingPoint_ID])
);

CREATE TABLE [dbo].[Channel] (
    [Channel_ID]          INT IDENTITY(1,1) NOT NULL,
    [SignalPort_ID]       INT NOT NULL,
    [Parameter_ID]        INT,
    [DataProvenance_ID]   INT,
    [ProcessingDegree_ID] INT DEFAULT 1,
    [ValueType_ID]        INT NOT NULL DEFAULT 1,
    CONSTRAINT [PK_Channel] PRIMARY KEY ([Channel_ID])
);

CREATE TABLE [dbo].[ChannelAxis] (
    [Channel_ID] INT NOT NULL,
    [AxisRole] INT NOT NULL,
    [ValueBinningAxis_ID] INT NOT NULL,
    CONSTRAINT [PK_ChannelAxis] PRIMARY KEY ([Channel_ID], [AxisRole]),
    CONSTRAINT [CK_MetaDataAxis_AxisRole] CHECK (AxisRole IN (0, 1))
);

CREATE TABLE [dbo].[ControlLoop] (
    [ControlLoop_ID]         INT IDENTITY(1,1) NOT NULL,
    [Name]                   NVARCHAR(200) NOT NULL,
    [ControllerType]         NVARCHAR(50)  NOT NULL,
    [FallbackControlLoop_ID] INT           NULL,
    [AlgorithmReference]     NVARCHAR(500) NULL,
    [Description]            NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_ControlLoop] PRIMARY KEY ([ControlLoop_ID])
);

CREATE TABLE [dbo].[ControlLoopApplication] (
    [ControlLoopApplication_ID] INT IDENTITY(1,1) NOT NULL,
    [ControlLoop_ID]            INT           NOT NULL,
    [StartTime]                 DATETIME2(7)  NOT NULL,
    [EndTime]                   DATETIME2(7)  NULL,
    [Parameters]                NVARCHAR(MAX) NULL,
    [AppliedByPerson_ID]        INT           NULL,
    [Notes]                     NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_ControlLoopApplication] PRIMARY KEY ([ControlLoopApplication_ID])
);

CREATE TABLE [dbo].[ControlLoopPort] (
    [ControlLoopPort_ID]     INT IDENTITY(1,1) NOT NULL,
    [ControlLoop_ID]         INT NOT NULL,
    [SignalPort_ID]          INT NOT NULL,
    [ControlLoopPortRole_ID] INT NOT NULL,
    CONSTRAINT [PK_ControlLoopPort] PRIMARY KEY ([ControlLoopPort_ID]),
    CONSTRAINT [UQ_ControlLoopPort_LoopPort] UNIQUE ([ControlLoop_ID], [SignalPort_ID])
);

CREATE TABLE [dbo].[DataAcquisitionSystem] (
    [DataAcquisitionSystem_ID] INT IDENTITY(1,1) NOT NULL,
    [ParentSystem_ID]          INT           NULL,
    [Name]                     NVARCHAR(200) NOT NULL,
    [SystemType]               NVARCHAR(50)  NULL,
    [Manufacturer]             NVARCHAR(100) NULL,
    [Model]                    NVARCHAR(100) NULL,
    [Description]              NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_DataAcquisitionSystem] PRIMARY KEY ([DataAcquisitionSystem_ID])
);

CREATE TABLE [dbo].[Dataset] (
    [Dataset_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Description] NVARCHAR(2000),
    [Purpose] NVARCHAR(500),
    [CreatedOn] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    [CreatedByPerson_ID] INT,
    CONSTRAINT [PK_Dataset] PRIMARY KEY ([Dataset_ID])
);

CREATE TABLE [dbo].[DatasetChannel] (
    [Dataset_ID] INT NOT NULL,
    [Channel_ID] INT NOT NULL,
    CONSTRAINT [PK_DatasetChannel] PRIMARY KEY ([Dataset_ID], [Channel_ID])
);

CREATE TABLE [dbo].[Equipment] (
    [Equipment_ID]      INT IDENTITY(1,1) NOT NULL,
    [EquipmentModel_ID] INT,
    [Identifier]        NVARCHAR(100),
    [SerialNumber]      NVARCHAR(100),
    [Owner]             NVARCHAR(MAX),
    [StorageLocation]   NVARCHAR(100),
    [PurchaseDate]      DATE,
    [IsActive]          BIT NOT NULL DEFAULT 1,
    CONSTRAINT [PK_Equipment] PRIMARY KEY ([Equipment_ID])
);

CREATE TABLE [dbo].[EquipmentEvent] (
    [EquipmentEvent_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID] INT NOT NULL,
    [EquipmentEventType_ID] INT NOT NULL,
    [EventDateTimeStart] DATETIME2(7) NOT NULL,
    [EventDateTimeEnd] DATETIME2(7),
    [PerformedByPerson_ID] INT,
    [Campaign_ID] INT,
    [Notes] NVARCHAR(MAX),
    CONSTRAINT [PK_EquipmentEvent] PRIMARY KEY ([EquipmentEvent_ID])
);

CREATE TABLE [dbo].[EquipmentModelHasParameter] (
    [EquipmentModel_ID] INT NOT NULL,
    [Parameter_ID] INT NOT NULL,
    CONSTRAINT [PK_EquipmentModelHasParameter] PRIMARY KEY ([EquipmentModel_ID], [Parameter_ID])
);

CREATE TABLE [dbo].[EquipmentModelHasProcedures] (
    [EquipmentModel_ID] INT NOT NULL,
    [Procedure_ID] INT NOT NULL,
    CONSTRAINT [PK_EquipmentModelHasProcedures] PRIMARY KEY ([EquipmentModel_ID], [Procedure_ID])
);

CREATE TABLE [dbo].[HydrologicalCharacteristics] (
    [Watershed_ID] INT IDENTITY(1,1) NOT NULL,
    [UrbanArea] REAL,
    [Forest] REAL,
    [Wetlands] REAL,
    [Cropland] REAL,
    [Meadow] REAL,
    [Grassland] REAL,
    CONSTRAINT [PK_HydrologicalCharacteristics] PRIMARY KEY ([Watershed_ID])
);

CREATE TABLE [dbo].[LabAnalysis] (
    [LabAnalysis_ID] INT IDENTITY(1,1) NOT NULL,
    [Sample_ID] INT NOT NULL,
    [Laboratory_ID] INT,
    [AnalystPerson_ID] INT,
    [Procedure_ID] INT,
    [AnalysisDateTime] DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
    [Campaign_ID] INT,
    [Notes] NVARCHAR(MAX),
    CONSTRAINT [PK_LabAnalysis] PRIMARY KEY ([LabAnalysis_ID])
);

CREATE TABLE [dbo].[LabValue] (
    [LabValue_ID] INT IDENTITY(1,1) NOT NULL,
    [LabAnalysis_ID] INT NOT NULL,
    [Parameter_ID] INT NOT NULL,
    [LabResult] FLOAT NOT NULL,
    [Replicate] INT NOT NULL DEFAULT 1,
    [QualityCode_ID] INT,
    [Comment] NVARCHAR(MAX),
    CONSTRAINT [PK_LabValue] PRIMARY KEY ([LabValue_ID])
);

CREATE TABLE [dbo].[Laboratory] (
    [Laboratory_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Site_ID] INT,
    [Description] NVARCHAR(500),
    CONSTRAINT [PK_Laboratory] PRIMARY KEY ([Laboratory_ID])
);

CREATE TABLE [dbo].[Observation] (
    [Observation_ID] INT IDENTITY(1,1) NOT NULL,
    [Channel_ID] INT NOT NULL,
    [Timestamp] DATETIME2(7) NOT NULL,
    [DataType] NVARCHAR(10) NOT NULL,
    CONSTRAINT [PK_Observation] PRIMARY KEY ([Observation_ID]),
    CONSTRAINT [UQ_Observation_ChannelTimestampDataType] UNIQUE ([Channel_ID], [Timestamp], [DataType])
);

CREATE TABLE [dbo].[Parameter] (
    [Unit_ID] INT,
    [Parameter] NVARCHAR(100),
    [Parameter_ID] INT IDENTITY(1,1) NOT NULL,
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_Parameter] PRIMARY KEY ([Parameter_ID])
);

CREATE TABLE [dbo].[SignalPortEquipmentHistory] (
    [SignalPortEquipmentHistory_ID] INT IDENTITY(1,1) NOT NULL,
    [SignalPort_ID]                 INT          NOT NULL,
    [Equipment_ID]                  INT          NULL,
    [StartTime]                     DATETIME2(7) NOT NULL,
    [EndTime]                       DATETIME2(7) NULL,
    [Notes]                         NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_SignalPortEquipmentHistory] PRIMARY KEY ([SignalPortEquipmentHistory_ID])
);

CREATE TABLE [dbo].[ProcessingLineage] (
    [ProcessingLineage_ID] INT IDENTITY(1,1) NOT NULL,
    [ProcessingStep_ID] INT NOT NULL,
    [Channel_ID] INT NOT NULL,
    [RoleInProcessingStep] NVARCHAR(10) NOT NULL,
    [StartTime] DATETIME2(7),
    [EndTime] DATETIME2(7),
    CONSTRAINT [PK_ProcessingLineage] PRIMARY KEY ([ProcessingLineage_ID])
);

CREATE TABLE [dbo].[ProcessingStep] (
    [ProcessingStep_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Description] NVARCHAR(MAX),
    [MethodName] NVARCHAR(200),
    [MethodVersion] NVARCHAR(100),
    [ProcessingType] NVARCHAR(100),
    [Parameters] NVARCHAR(MAX),
    [ExecutedDateTime] DATETIME2(7),
    [ExecutedByPerson_ID] INT,
    [Dataset_ID] INT,
    CONSTRAINT [PK_ProcessingStep] PRIMARY KEY ([ProcessingStep_ID])
);

CREATE TABLE [dbo].[Sample] (
    [Sample_ID] INT IDENTITY(1,1) NOT NULL,
    [ParentSample_ID] INT,
    [SampleType_ID] INT,
    [SamplingPoint_ID] INT NOT NULL,
    [SampledByPerson_ID] INT,
    [Campaign_ID] INT,
    [SampleDateTimeStart] DATETIME2(7) NOT NULL,
    [SampleDateTimeEnd] DATETIME2(7),
    [SampleMethod_ID] INT,
    [SampleEquipment_ID] INT,
    [Description] NVARCHAR(500),
    CONSTRAINT [PK_Sample] PRIMARY KEY ([Sample_ID])
);

CREATE TABLE [dbo].[SamplingPoint] (
    [SamplingPoint_ID] INT IDENTITY(1,1) NOT NULL,
    [Site_ID] INT,
    [SamplingPoint] NVARCHAR(100),
    [SamplingLocation] NVARCHAR(100),
    [LatitudeWGS84] FLOAT,
    [LongitudeWGS84] FLOAT,
    [Description] NVARCHAR(MAX),
    [Pictures] /* UNMAPPED TYPE */,
    [ValidFrom] DATETIME2(7),
    [ValidTo] DATETIME2(7),
    [CreatedByCampaign_ID] INT,
    CONSTRAINT [PK_SamplingPoint] PRIMARY KEY ([SamplingPoint_ID])
);

CREATE TABLE [dbo].[SignalPort] (
    [SignalPort_ID]            INT IDENTITY(1,1) NOT NULL,
    [DataAcquisitionSystem_ID] INT           NOT NULL,
    [Tag]                      NVARCHAR(200) NOT NULL,
    [SignalPortType_ID]        INT           NOT NULL,
    [ControlVariableType_ID]   INT           NULL,
    [ParentPort_ID]            INT           NULL,
    [IsActive]                 BIT           NOT NULL DEFAULT 1,
    [Description]              NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_SignalPort] PRIMARY KEY ([SignalPort_ID]),
    CONSTRAINT [UQ_SignalPort_DAS_Tag] UNIQUE ([DataAcquisitionSystem_ID], [Tag])
);

CREATE TABLE [dbo].[SignalPortLocationHistory] (
    [SignalPortLocationHistory_ID] INT IDENTITY(1,1) NOT NULL,
    [SignalPort_ID]                INT          NOT NULL,
    [SamplingPoint_ID]             INT          NOT NULL,
    [StartTime]                    DATETIME2(7) NOT NULL,
    [EndTime]                      DATETIME2(7) NULL,
    [Notes]                        NVARCHAR(MAX) NULL,
    CONSTRAINT [PK_SignalPortLocationHistory] PRIMARY KEY ([SignalPortLocationHistory_ID])
);

CREATE TABLE [dbo].[Site] (
    [Site_ID] INT IDENTITY(1,1) NOT NULL,
    [Watershed_ID] INT,
    [Name] NVARCHAR(100),
    [Type] NVARCHAR(255),
    [Description] NVARCHAR(MAX),
    [LatitudeWGS84] FLOAT,
    [LongitudeWGS84] FLOAT,
    [StreetNumber] NVARCHAR(100),
    [StreetName] NVARCHAR(100),
    [City] NVARCHAR(255),
    [PostCode] NVARCHAR(100),
    [Province] NVARCHAR(255),
    [Country] NVARCHAR(255),
    CONSTRAINT [PK_Site] PRIMARY KEY ([Site_ID])
);

CREATE TABLE [dbo].[UrbanCharacteristics] (
    [Watershed_ID] INT IDENTITY(1,1) NOT NULL,
    [Commercial] REAL,
    [GreenSpaces] REAL,
    [Industrial] REAL,
    [Institutional] REAL,
    [Residential] REAL,
    [Agricultural] REAL,
    [Recreational] REAL,
    CONSTRAINT [PK_UrbanCharacteristics] PRIMARY KEY ([Watershed_ID])
);

CREATE TABLE [dbo].[Value] (
    [Observation_ID] INT NOT NULL,
    [Value] FLOAT,
    CONSTRAINT [PK_Value] PRIMARY KEY ([Observation_ID])
);

CREATE TABLE [dbo].[ValueBin] (
    [ValueBin_ID] INT IDENTITY(1,1) NOT NULL,
    [ValueBinningAxis_ID] INT NOT NULL,
    [BinIndex] INT NOT NULL,
    [LowerBound] FLOAT NOT NULL,
    [UpperBound] FLOAT NOT NULL,
    CONSTRAINT [PK_ValueBin] PRIMARY KEY ([ValueBin_ID]),
    CONSTRAINT [UQ_ValueBin_AxisIndex] UNIQUE ([ValueBinningAxis_ID], [BinIndex]),
    CONSTRAINT [CK_ValueBin_Bounds] CHECK (UpperBound > LowerBound)
);

CREATE TABLE [dbo].[ValueBinningAxis] (
    [ValueBinningAxis_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Description] NVARCHAR(500),
    [NumberOfBins] INT NOT NULL,
    [Unit_ID] INT NOT NULL,
    CONSTRAINT [PK_ValueBinningAxis] PRIMARY KEY ([ValueBinningAxis_ID])
);

CREATE TABLE [dbo].[ValueImage] (
    [Observation_ID] INT NOT NULL,
    [ImageWidth] INT NOT NULL,
    [ImageHeight] INT NOT NULL,
    [NumberOfChannels] INT NOT NULL DEFAULT 3,
    [ImageFormat] NVARCHAR(20) NOT NULL,
    [FileSizeBytes] BIGINT,
    [StorageBackend] NVARCHAR(50) NOT NULL DEFAULT 'FileSystem',
    [StoragePath] NVARCHAR(1000) NOT NULL,
    [Thumbnail] VARBINARY(MAX),
    [QualityCode] INT,
    CONSTRAINT [PK_ValueImage] PRIMARY KEY ([Observation_ID])
);

CREATE TABLE [dbo].[ValueMatrix] (
    [Observation_ID] INT NOT NULL,
    [RowValueBin_ID] INT NOT NULL,
    [ColValueBin_ID] INT NOT NULL,
    [Value] FLOAT,
    [QualityCode] INT,
    CONSTRAINT [PK_ValueMatrix] PRIMARY KEY ([Observation_ID], [RowValueBin_ID], [ColValueBin_ID])
);

CREATE TABLE [dbo].[ValueVector] (
    [Observation_ID] INT NOT NULL,
    [ValueBin_ID] INT NOT NULL,
    [Value] FLOAT,
    [QualityCode] INT,
    CONSTRAINT [PK_ValueVector] PRIMARY KEY ([Observation_ID], [ValueBin_ID])
);

-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX [IX_Annotation_Channel_Time] ON [dbo].[Annotation] ([Channel_ID], [StartTime], [EndTime]);
CREATE INDEX [IX_Annotation_Author] ON [dbo].[Annotation] ([AuthorPerson_ID], [CreatedDateTime]);

CREATE UNIQUE INDEX [UQ_Channel_SignalStream]
    ON [dbo].[Channel] ([SignalPort_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID])
    WHERE [Parameter_ID] IS NOT NULL;

CREATE UNIQUE INDEX [UQ_ControlLoopApplication_ActiveRow]
    ON [dbo].[ControlLoopApplication] ([ControlLoop_ID])
    WHERE [EndTime] IS NULL;

CREATE INDEX [IX_EquipmentEvent_Equipment_Start] ON [dbo].[EquipmentEvent] ([Equipment_ID], [EventDateTimeStart]);

CREATE INDEX [IX_ProcessingLineage_Channel] ON [dbo].[ProcessingLineage] ([Channel_ID]);
CREATE INDEX [IX_Lineage_Step_Role] ON [dbo].[ProcessingLineage] ([ProcessingStep_ID], [RoleInProcessingStep]);

CREATE UNIQUE INDEX [UQ_SignalPortEquipmentHistory_ActiveRow]
    ON [dbo].[SignalPortEquipmentHistory] ([SignalPort_ID])
    WHERE [EndTime] IS NULL;

CREATE UNIQUE INDEX [UQ_SignalPortLocationHistory_ActiveRow]
    ON [dbo].[SignalPortLocationHistory] ([SignalPort_ID])
    WHERE [EndTime] IS NULL;

-- ============================================================
-- Foreign key constraints
-- ============================================================

ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_AnnotationType] FOREIGN KEY ([AnnotationType_ID]) REFERENCES [dbo].[AnnotationType] ([AnnotationType_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Person] FOREIGN KEY ([AuthorPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_EquipmentEvent] FOREIGN KEY ([EquipmentEvent_ID]) REFERENCES [dbo].[EquipmentEvent] ([EquipmentEvent_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Observation] FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
ALTER TABLE [dbo].[Campaign] ADD CONSTRAINT [FK_Campaign_CampaignType] FOREIGN KEY ([CampaignType_ID]) REFERENCES [dbo].[CampaignType] ([CampaignType_ID]);
ALTER TABLE [dbo].[Campaign] ADD CONSTRAINT [FK_Campaign_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]);
ALTER TABLE [dbo].[CampaignEquipment] ADD CONSTRAINT [FK_CampaignEquipment_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[CampaignEquipment] ADD CONSTRAINT [FK_CampaignEquipment_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[CampaignSamplingLocation] ADD CONSTRAINT [FK_CampaignSamplingLocation_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[CampaignSamplingLocation] ADD CONSTRAINT [FK_CampaignSamplingLocation_SamplingPoint] FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_SignalPort] FOREIGN KEY ([SignalPort_ID]) REFERENCES [dbo].[SignalPort] ([SignalPort_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_Parameter] FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_DataProvenance] FOREIGN KEY ([DataProvenance_ID]) REFERENCES [dbo].[DataProvenance] ([DataProvenance_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_ProcessingDegree] FOREIGN KEY ([ProcessingDegree_ID]) REFERENCES [dbo].[ProcessingDegree] ([ProcessingDegree_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_ValueType] FOREIGN KEY ([ValueType_ID]) REFERENCES [dbo].[ValueType] ([ValueType_ID]);
ALTER TABLE [dbo].[ChannelAxis] ADD CONSTRAINT [FK_ChannelAxis_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ChannelAxis] ADD CONSTRAINT [FK_ChannelAxis_ValueBinningAxis] FOREIGN KEY ([ValueBinningAxis_ID]) REFERENCES [dbo].[ValueBinningAxis] ([ValueBinningAxis_ID]);
ALTER TABLE [dbo].[ControlLoop] ADD CONSTRAINT [FK_ControlLoop_Fallback] FOREIGN KEY ([FallbackControlLoop_ID]) REFERENCES [dbo].[ControlLoop] ([ControlLoop_ID]);
ALTER TABLE [dbo].[ControlLoopApplication] ADD CONSTRAINT [FK_ControlLoopApplication_Loop] FOREIGN KEY ([ControlLoop_ID]) REFERENCES [dbo].[ControlLoop] ([ControlLoop_ID]);
ALTER TABLE [dbo].[ControlLoopApplication] ADD CONSTRAINT [FK_ControlLoopApplication_Person] FOREIGN KEY ([AppliedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[ControlLoopPort] ADD CONSTRAINT [FK_ControlLoopPort_Loop] FOREIGN KEY ([ControlLoop_ID]) REFERENCES [dbo].[ControlLoop] ([ControlLoop_ID]);
ALTER TABLE [dbo].[ControlLoopPort] ADD CONSTRAINT [FK_ControlLoopPort_Port] FOREIGN KEY ([SignalPort_ID]) REFERENCES [dbo].[SignalPort] ([SignalPort_ID]);
ALTER TABLE [dbo].[ControlLoopPort] ADD CONSTRAINT [FK_ControlLoopPort_Role] FOREIGN KEY ([ControlLoopPortRole_ID]) REFERENCES [dbo].[ControlLoopPortRole] ([ControlLoopPortRole_ID]);
ALTER TABLE [dbo].[DataAcquisitionSystem] ADD CONSTRAINT [FK_DAS_ParentSystem] FOREIGN KEY ([ParentSystem_ID]) REFERENCES [dbo].[DataAcquisitionSystem] ([DataAcquisitionSystem_ID]);
ALTER TABLE [dbo].[Dataset] ADD CONSTRAINT [FK_Dataset_Person] FOREIGN KEY ([CreatedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[DatasetChannel] ADD CONSTRAINT [FK_DatasetChannel_Dataset] FOREIGN KEY ([Dataset_ID]) REFERENCES [dbo].[Dataset] ([Dataset_ID]);
ALTER TABLE [dbo].[DatasetChannel] ADD CONSTRAINT [FK_DatasetChannel_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[Equipment] ADD CONSTRAINT [FK_Equipment_EquipmentModel] FOREIGN KEY ([EquipmentModel_ID]) REFERENCES [dbo].[EquipmentModel] ([EquipmentModel_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_EquipmentEventType] FOREIGN KEY ([EquipmentEventType_ID]) REFERENCES [dbo].[EquipmentEventType] ([EquipmentEventType_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_Person] FOREIGN KEY ([PerformedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[EquipmentModelHasParameter] ADD CONSTRAINT [FK_EquipmentModelHasParameter_EquipmentModel] FOREIGN KEY ([EquipmentModel_ID]) REFERENCES [dbo].[EquipmentModel] ([EquipmentModel_ID]);
ALTER TABLE [dbo].[EquipmentModelHasParameter] ADD CONSTRAINT [FK_EquipmentModelHasParameter_Parameter] FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);
ALTER TABLE [dbo].[EquipmentModelHasProcedures] ADD CONSTRAINT [FK_EquipmentModelHasProcedures_EquipmentModel] FOREIGN KEY ([EquipmentModel_ID]) REFERENCES [dbo].[EquipmentModel] ([EquipmentModel_ID]);
ALTER TABLE [dbo].[EquipmentModelHasProcedures] ADD CONSTRAINT [FK_EquipmentModelHasProcedures_Procedures] FOREIGN KEY ([Procedure_ID]) REFERENCES [dbo].[Procedures] ([Procedure_ID]);
ALTER TABLE [dbo].[HydrologicalCharacteristics] ADD CONSTRAINT [FK_HydrologicalCharacteristics_Watershed] FOREIGN KEY ([Watershed_ID]) REFERENCES [dbo].[Watershed] ([Watershed_ID]);
ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_Sample] FOREIGN KEY ([Sample_ID]) REFERENCES [dbo].[Sample] ([Sample_ID]);
ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_Laboratory] FOREIGN KEY ([Laboratory_ID]) REFERENCES [dbo].[Laboratory] ([Laboratory_ID]);
ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_Person] FOREIGN KEY ([AnalystPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_Procedures] FOREIGN KEY ([Procedure_ID]) REFERENCES [dbo].[Procedures] ([Procedure_ID]);
ALTER TABLE [dbo].[LabAnalysis] ADD CONSTRAINT [FK_LabAnalysis_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[LabValue] ADD CONSTRAINT [FK_LabValue_LabAnalysis] FOREIGN KEY ([LabAnalysis_ID]) REFERENCES [dbo].[LabAnalysis] ([LabAnalysis_ID]);
ALTER TABLE [dbo].[LabValue] ADD CONSTRAINT [FK_LabValue_Parameter] FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);
ALTER TABLE [dbo].[LabValue] ADD CONSTRAINT [FK_LabValue_QualityCode] FOREIGN KEY ([QualityCode_ID]) REFERENCES [dbo].[QualityCode] ([QualityCode_ID]);
ALTER TABLE [dbo].[Laboratory] ADD CONSTRAINT [FK_Laboratory_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]);
ALTER TABLE [dbo].[Observation] ADD CONSTRAINT [FK_Observation_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[Parameter] ADD CONSTRAINT [FK_Parameter_Unit] FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);
ALTER TABLE [dbo].[SignalPortEquipmentHistory] ADD CONSTRAINT [FK_SignalPortEquipmentHistory_Port] FOREIGN KEY ([SignalPort_ID]) REFERENCES [dbo].[SignalPort] ([SignalPort_ID]);
ALTER TABLE [dbo].[SignalPortEquipmentHistory] ADD CONSTRAINT [FK_SignalPortEquipmentHistory_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[ProcessingLineage] ADD CONSTRAINT [FK_ProcessingLineage_ProcessingStep] FOREIGN KEY ([ProcessingStep_ID]) REFERENCES [dbo].[ProcessingStep] ([ProcessingStep_ID]);
ALTER TABLE [dbo].[ProcessingLineage] ADD CONSTRAINT [FK_ProcessingLineage_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ProcessingStep] ADD CONSTRAINT [FK_ProcessingStep_Person] FOREIGN KEY ([ExecutedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[ProcessingStep] ADD CONSTRAINT [FK_ProcessingStep_Dataset] FOREIGN KEY ([Dataset_ID]) REFERENCES [dbo].[Dataset] ([Dataset_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_Sample] FOREIGN KEY ([ParentSample_ID]) REFERENCES [dbo].[Sample] ([Sample_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_SampleType] FOREIGN KEY ([SampleType_ID]) REFERENCES [dbo].[SampleType] ([SampleType_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_SamplingPoint] FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_Person] FOREIGN KEY ([SampledByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_SampleMethod] FOREIGN KEY ([SampleMethod_ID]) REFERENCES [dbo].[SampleMethod] ([SampleMethod_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_Equipment] FOREIGN KEY ([SampleEquipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[SamplingPoint] ADD CONSTRAINT [FK_SamplingPoint_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]);
ALTER TABLE [dbo].[SamplingPoint] ADD CONSTRAINT [FK_SamplingPoint_Campaign] FOREIGN KEY ([CreatedByCampaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[SignalPort] ADD CONSTRAINT [FK_SignalPort_DAS] FOREIGN KEY ([DataAcquisitionSystem_ID]) REFERENCES [dbo].[DataAcquisitionSystem] ([DataAcquisitionSystem_ID]);
ALTER TABLE [dbo].[SignalPort] ADD CONSTRAINT [FK_SignalPort_Type] FOREIGN KEY ([SignalPortType_ID]) REFERENCES [dbo].[SignalPortType] ([SignalPortType_ID]);
ALTER TABLE [dbo].[SignalPort] ADD CONSTRAINT [FK_SignalPort_ControlVariableType] FOREIGN KEY ([ControlVariableType_ID]) REFERENCES [dbo].[ControlVariableType] ([ControlVariableType_ID]);
ALTER TABLE [dbo].[SignalPort] ADD CONSTRAINT [FK_SignalPort_ParentPort] FOREIGN KEY ([ParentPort_ID]) REFERENCES [dbo].[SignalPort] ([SignalPort_ID]);
ALTER TABLE [dbo].[SignalPortLocationHistory] ADD CONSTRAINT [FK_SignalPortLocationHistory_Port] FOREIGN KEY ([SignalPort_ID]) REFERENCES [dbo].[SignalPort] ([SignalPort_ID]);
ALTER TABLE [dbo].[SignalPortLocationHistory] ADD CONSTRAINT [FK_SignalPortLocationHistory_SamplingPoint] FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);
ALTER TABLE [dbo].[Site] ADD CONSTRAINT [FK_Site_Watershed] FOREIGN KEY ([Watershed_ID]) REFERENCES [dbo].[Watershed] ([Watershed_ID]);
ALTER TABLE [dbo].[UrbanCharacteristics] ADD CONSTRAINT [FK_UrbanCharacteristics_Watershed] FOREIGN KEY ([Watershed_ID]) REFERENCES [dbo].[Watershed] ([Watershed_ID]);
ALTER TABLE [dbo].[Value] ADD CONSTRAINT [FK_Value_Observation] FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
ALTER TABLE [dbo].[ValueBin] ADD CONSTRAINT [FK_ValueBin_ValueBinningAxis] FOREIGN KEY ([ValueBinningAxis_ID]) REFERENCES [dbo].[ValueBinningAxis] ([ValueBinningAxis_ID]);
ALTER TABLE [dbo].[ValueBinningAxis] ADD CONSTRAINT [FK_ValueBinningAxis_Unit] FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);
ALTER TABLE [dbo].[ValueImage] ADD CONSTRAINT [FK_ValueImage_Observation] FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_Observation] FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_RowValueBin] FOREIGN KEY ([RowValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_ColValueBin] FOREIGN KEY ([ColValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);
ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [FK_ValueVector_Observation] FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [FK_ValueVector_ValueBin] FOREIGN KEY ([ValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);

-- ============================================================
-- Views
-- ============================================================

CREATE OR ALTER VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    valueC.[Channel_ID]         AS MeasurementChannelID,
    e.[Equipment_ID]            AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    p.[Parameter]               AS MeasurementParameter,
    o.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]               o        ON o.[Observation_ID]      = v.[Observation_ID]
JOIN [dbo].[Channel]                   statusC  ON statusC.[Channel_ID]    = o.[Channel_ID]
JOIN [dbo].[SignalPort]                statusP  ON statusP.[SignalPort_ID] = statusC.[SignalPort_ID]
JOIN [dbo].[SignalPortType]            spt      ON spt.[SignalPortType_ID] = statusP.[SignalPortType_ID]
JOIN [dbo].[SignalPort]                valueP   ON valueP.[SignalPort_ID]  = statusP.[ParentPort_ID]
JOIN [dbo].[Channel]                   valueC   ON valueC.[SignalPort_ID]  = valueP.[SignalPort_ID]
JOIN [dbo].[Parameter]                 p        ON p.[Parameter_ID]        = valueC.[Parameter_ID]
LEFT JOIN [dbo].[SignalPortEquipmentHistory] peh  ON peh.[SignalPort_ID]     = valueP.[SignalPort_ID]
                                                  AND peh.[EndTime]          IS NULL
LEFT JOIN [dbo].[Equipment]            e        ON e.[Equipment_ID]        = peh.[Equipment_ID]
WHERE spt.[Name] = N'Status'
  AND statusP.[ParentPort_ID] IS NOT NULL;
GO

CREATE OR ALTER VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]        AS StatusChannelID,
    e.[Equipment_ID]            AS EquipmentID,
    e.[Identifier]              AS EquipmentName,
    o.[Timestamp],
    CAST(v.[Value] AS INT)      AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]               o        ON o.[Observation_ID]      = v.[Observation_ID]
JOIN [dbo].[Channel]                   statusC  ON statusC.[Channel_ID]    = o.[Channel_ID]
JOIN [dbo].[SignalPort]                statusP  ON statusP.[SignalPort_ID] = statusC.[SignalPort_ID]
JOIN [dbo].[SignalPortType]            spt      ON spt.[SignalPortType_ID] = statusP.[SignalPortType_ID]
JOIN [dbo].[SignalPortEquipmentHistory]  peh      ON peh.[SignalPort_ID]     = statusP.[SignalPort_ID]
                                                 AND peh.[EndTime]          IS NULL
JOIN [dbo].[Equipment]                 e        ON e.[Equipment_ID]        = peh.[Equipment_ID]
WHERE spt.[Name] = N'Status';
GO
