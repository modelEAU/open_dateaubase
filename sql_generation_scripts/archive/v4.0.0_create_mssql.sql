-- Baseline CREATE script for schema v4.0.0
-- Platform: mssql
-- Generated: 2026-05-03 17:26:58 UTC

CREATE TABLE [dbo].[AnnotationKind] (
    [AnnotationKind_ID] INT NOT NULL,
    [Name] NVARCHAR(100) NOT NULL,
    [Description] NVARCHAR(500),
    [Color] NVARCHAR(7),
    CONSTRAINT [PK_AnnotationKind] PRIMARY KEY ([AnnotationKind_ID])
);

CREATE TABLE [dbo].[BinKind] (
    [BinKind_ID] INT NOT NULL,
    [Name] NVARCHAR(30) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_BinKind] PRIMARY KEY ([BinKind_ID])
);

CREATE TABLE [dbo].[CampaignKind] (
    [CampaignKind_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(100) NOT NULL,
    [Description] NVARCHAR(300),
    CONSTRAINT [PK_CampaignKind] PRIMARY KEY ([CampaignKind_ID])
);

CREATE TABLE [dbo].[ChannelKind] (
    [ChannelKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_ChannelKind] PRIMARY KEY ([ChannelKind_ID])
);

CREATE TABLE [dbo].[ControlLoopPortKind] (
    [ControlLoopPortKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_ControlLoopPortKind] PRIMARY KEY ([ControlLoopPortKind_ID])
);

CREATE TABLE [dbo].[DataProvenanceKind] (
    [DataProvenanceKind_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(300),
    CONSTRAINT [PK_DataProvenanceKind] PRIMARY KEY ([DataProvenanceKind_ID])
);

CREATE TABLE [dbo].[EquipmentEventKind] (
    [EquipmentEventKind_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(100) NOT NULL,
    [Description] NVARCHAR(300),
    CONSTRAINT [PK_EquipmentEventKind] PRIMARY KEY ([EquipmentEventKind_ID])
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

CREATE TABLE [dbo].[Parameter] (
    [Parameter] NVARCHAR(100),
    [Parameter_ID] INT IDENTITY(1,1) NOT NULL,
    [Description] NVARCHAR(MAX),
    [ENVO_IRI] NVARCHAR(256),
    CONSTRAINT [PK_Parameter] PRIMARY KEY ([Parameter_ID])
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

CREATE TABLE [dbo].[ProcessUnitKind] (
    [ProcessUnitKind_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(100) NOT NULL,
    [Description] NVARCHAR(300),
    CONSTRAINT [PK_ProcessUnitKind] PRIMARY KEY ([ProcessUnitKind_ID])
);

CREATE TABLE [dbo].[ProcessingKind] (
    [ProcessingKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_ProcessingKind] PRIMARY KEY ([ProcessingKind_ID])
);

CREATE TABLE [dbo].[QualityCode] (
    [QualityCode_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    [IsUsable] BIT NOT NULL DEFAULT 1,
    CONSTRAINT [PK_QualityCode] PRIMARY KEY ([QualityCode_ID])
);

CREATE TABLE [dbo].[SampleCollectionKind] (
    [SampleCollectionKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_SampleCollectionKind] PRIMARY KEY ([SampleCollectionKind_ID])
);

CREATE TABLE [dbo].[SampleKind] (
    [SampleKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_SampleKind] PRIMARY KEY ([SampleKind_ID])
);

CREATE TABLE [dbo].[SchemaVersion] (
    [VersionID] INT IDENTITY(1,1) NOT NULL,
    [Version] NVARCHAR(20) NOT NULL,
    [AppliedDateTime] DATETIME2(7) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    [Description] NVARCHAR(500),
    [MigrationScript] NVARCHAR(200),
    CONSTRAINT [PK_SchemaVersion] PRIMARY KEY ([VersionID])
);

CREATE TABLE [dbo].[SignalInterfaceKind] (
    [SignalInterfaceKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(300),
    CONSTRAINT [PK_SignalInterfaceKind] PRIMARY KEY ([SignalInterfaceKind_ID])
);

CREATE TABLE [dbo].[SignalInterfacePortKind] (
    [SignalInterfacePortKind_ID] INT NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_SignalInterfacePortKind] PRIMARY KEY ([SignalInterfacePortKind_ID])
);

CREATE TABLE [dbo].[SiteKind] (
    [SiteKind_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(100) NOT NULL,
    [Description] NVARCHAR(300),
    CONSTRAINT [PK_SiteKind] PRIMARY KEY ([SiteKind_ID])
);

CREATE TABLE [dbo].[Unit] (
    [Unit_ID] INT IDENTITY(1,1) NOT NULL,
    [Unit] NVARCHAR(100),
    [QUDT_IRI] NVARCHAR(256),
    [UnitVector] NVARCHAR(64),
    CONSTRAINT [PK_Unit] PRIMARY KEY ([Unit_ID])
);

CREATE TABLE [dbo].[ValueKind] (
    [ValueKind_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    CONSTRAINT [PK_ValueKind] PRIMARY KEY ([ValueKind_ID])
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

CREATE TABLE [dbo].[Annotation] (
    [Annotation_ID] INT IDENTITY(1,1) NOT NULL,
    [Channel_ID] INT NOT NULL,
    [AnnotationKind_ID] INT NOT NULL,
    [StartTime] DATETIME2(7) NOT NULL,
    [EndTime] DATETIME2(7),
    [AuthorPerson_ID] INT,
    [Campaign_ID] INT,
    [EquipmentEvent_ID] INT,
    [Title] NVARCHAR(200),
    [Comment] NVARCHAR(MAX),
    [CreatedDateTime] DATETIME2(7) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    [ModifiedDateTime] DATETIME2(7),
    [Observation_ID] INT,
    CONSTRAINT [PK_Annotation] PRIMARY KEY ([Annotation_ID])
);

CREATE TABLE [dbo].[Campaign] (
    [Campaign_ID] INT IDENTITY(1,1) NOT NULL,
    [CampaignKind_ID] INT NOT NULL,
    [Site_ID] INT NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Description] NVARCHAR(2000),
    [CampaignStartDateTime] DATETIME2(7),
    [CampaignEndDateTime] DATETIME2(7),
    [ResponsiblePerson_ID] INT,
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
    [Channel_ID] INT IDENTITY(1,1) NOT NULL,
    [SignalInterface_ID] INT NOT NULL,
    [TagName] NVARCHAR(200) NOT NULL,
    [SignalInterfacePort_ID] INT,
    [ParentChannel_ID] INT,
    [ChannelKind_ID] INT NOT NULL DEFAULT 1,
    [Parameter_ID] INT,
    [DataProvenanceKind_ID] INT,
    [ProcessingKind_ID] INT DEFAULT 1,
    [ValueKind_ID] INT NOT NULL DEFAULT 1,
    [Unit_ID] INT,
    CONSTRAINT [PK_Channel] PRIMARY KEY ([Channel_ID])
);

CREATE TABLE [dbo].[ChannelAxis] (
    [Channel_ID] INT NOT NULL,
    [AxisRole] INT NOT NULL,
    [ValueBinningAxis_ID] INT NOT NULL,
    CONSTRAINT [PK_ChannelAxis] PRIMARY KEY ([Channel_ID], [AxisRole]),
    CONSTRAINT [CK_MetaDataAxis_AxisRole] CHECK (AxisRole IN (0, 1))
);

CREATE TABLE [dbo].[ChannelPortHistory] (
    [ChannelPortHistory_ID] INT IDENTITY(1,1) NOT NULL,
    [Channel_ID] INT NOT NULL,
    [SignalInterfacePort_ID] INT,
    [ValidFrom] DATETIME2(7) NOT NULL,
    [ValidTo] DATETIME2(7),
    [GatingNote] NVARCHAR(MAX),
    CONSTRAINT [PK_ChannelPortHistory] PRIMARY KEY ([ChannelPortHistory_ID])
);

CREATE TABLE [dbo].[ControlLoop] (
    [ControlLoop_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [ControllerType] NVARCHAR(50) NOT NULL,
    [FallbackControlLoop_ID] INT,
    [AlgorithmReference] NVARCHAR(500),
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_ControlLoop] PRIMARY KEY ([ControlLoop_ID])
);

CREATE TABLE [dbo].[ControlLoopApplication] (
    [ControlLoopApplication_ID] INT IDENTITY(1,1) NOT NULL,
    [ControlLoop_ID] INT NOT NULL,
    [StartTime] DATETIME2(7) NOT NULL,
    [EndTime] DATETIME2(7),
    [Parameters] NVARCHAR(MAX),
    [AppliedByPerson_ID] INT,
    [Notes] NVARCHAR(MAX),
    CONSTRAINT [PK_ControlLoopApplication] PRIMARY KEY ([ControlLoopApplication_ID])
);

CREATE TABLE [dbo].[ControlLoopPort] (
    [ControlLoopPort_ID] INT IDENTITY(1,1) NOT NULL,
    [ControlLoop_ID] INT NOT NULL,
    [Channel_ID] INT NOT NULL,
    [ControlLoopPortKind_ID] INT NOT NULL,
    CONSTRAINT [PK_ControlLoopPort] PRIMARY KEY ([ControlLoopPort_ID])
);

CREATE TABLE [dbo].[DataAcquisitionSystem] (
    [DataAcquisitionSystem_ID] INT IDENTITY(1,1) NOT NULL,
    [ParentSystem_ID] INT,
    [Name] NVARCHAR(200) NOT NULL,
    [SystemType] NVARCHAR(50),
    [Manufacturer] NVARCHAR(100),
    [Model] NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_DataAcquisitionSystem] PRIMARY KEY ([DataAcquisitionSystem_ID])
);

CREATE TABLE [dbo].[Dataset] (
    [Dataset_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Description] NVARCHAR(2000),
    [Purpose] NVARCHAR(500),
    [CreatedOn] DATETIME2(7) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    [CreatedByPerson_ID] INT,
    CONSTRAINT [PK_Dataset] PRIMARY KEY ([Dataset_ID])
);

CREATE TABLE [dbo].[DatasetChannel] (
    [Dataset_ID] INT NOT NULL,
    [Channel_ID] INT NOT NULL,
    CONSTRAINT [PK_DatasetChannel] PRIMARY KEY ([Dataset_ID], [Channel_ID])
);

CREATE TABLE [dbo].[Equipment] (
    [Equipment_ID] INT IDENTITY(1,1) NOT NULL,
    [EquipmentModel_ID] INT,
    [Identifier] NVARCHAR(100),
    [SerialNumber] NVARCHAR(100),
    [Owner] NVARCHAR(MAX),
    [StorageLocation] NVARCHAR(100),
    [PurchaseDate] DATE,
    [IsActive] BIT NOT NULL DEFAULT 1,
    CONSTRAINT [PK_Equipment] PRIMARY KEY ([Equipment_ID])
);

CREATE TABLE [dbo].[EquipmentEvent] (
    [EquipmentEvent_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID] INT NOT NULL,
    [EquipmentEventKind_ID] INT NOT NULL,
    [EventDateTimeStart] DATETIME2(7) NOT NULL,
    [EventDateTimeEnd] DATETIME2(7),
    [PerformedByPerson_ID] INT,
    [Campaign_ID] INT,
    [Notes] NVARCHAR(MAX),
    CONSTRAINT [PK_EquipmentEvent] PRIMARY KEY ([EquipmentEvent_ID])
);

CREATE TABLE [dbo].[EquipmentLocationHistory] (
    [EquipmentLocationHistory_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID] INT NOT NULL,
    [SamplingPoint_ID] INT NOT NULL,
    [ValidFrom] DATETIME2(7) NOT NULL,
    [ValidTo] DATETIME2(7),
    [Campaign_ID] INT,
    [Notes] NVARCHAR(MAX),
    CONSTRAINT [PK_EquipmentLocationHistory] PRIMARY KEY ([EquipmentLocationHistory_ID])
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

CREATE TABLE [dbo].[EquipmentWiringHistory] (
    [EquipmentWiringHistory_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID] INT NOT NULL,
    [SignalInterface_ID] INT NOT NULL,
    [SignalInterfacePort_ID] INT,
    [ValidFrom] DATETIME2(7) NOT NULL,
    [ValidTo] DATETIME2(7),
    [Note] NVARCHAR(MAX),
    CONSTRAINT [PK_EquipmentWiringHistory] PRIMARY KEY ([EquipmentWiringHistory_ID])
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

CREATE TABLE [dbo].[ProcessUnit] (
    [ProcessUnit_ID] INT IDENTITY(1,1) NOT NULL,
    [Site_ID] INT NOT NULL,
    [Tag] NVARCHAR(100) NOT NULL,
    [Name] NVARCHAR(255) NOT NULL,
    [Description] NVARCHAR(MAX),
    [ProcessUnitKind_ID] INT,
    [Parent_ID] INT,
    CONSTRAINT [PK_ProcessUnit] PRIMARY KEY ([ProcessUnit_ID])
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
    [SampleKind_ID] INT,
    [SamplingPoint_ID] INT NOT NULL,
    [SampledByPerson_ID] INT,
    [Campaign_ID] INT,
    [SampleDateTimeStart] DATETIME2(7) NOT NULL,
    [SampleDateTimeEnd] DATETIME2(7),
    [SampleCollectionKind_ID] INT,
    [SampleEquipment_ID] INT,
    [Description] NVARCHAR(500),
    CONSTRAINT [PK_Sample] PRIMARY KEY ([Sample_ID])
);

CREATE TABLE [dbo].[SamplingPoint] (
    [SamplingPoint_ID] INT IDENTITY(1,1) NOT NULL,
    [Site_ID] INT NOT NULL,
    [SamplingPoint] NVARCHAR(100) NOT NULL,
    [SamplingLocation] NVARCHAR(100),
    [LatitudeWGS84] FLOAT,
    [LongitudeWGS84] FLOAT,
    [Description] NVARCHAR(MAX),
    [PicturePath] NVARCHAR(500),
    [ValidFrom] DATETIME2(7),
    [ValidTo] DATETIME2(7),
    [ProcessUnit_ID] INT,
    [CreatedByCampaign_ID] INT,
    CONSTRAINT [PK_SamplingPoint] PRIMARY KEY ([SamplingPoint_ID])
);

CREATE TABLE [dbo].[SignalInterface] (
    [SignalInterface_ID] INT IDENTITY(1,1) NOT NULL,
    [DataAcquisitionSystem_ID] INT NOT NULL,
    [SignalInterfaceKind_ID] INT NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Make] NVARCHAR(100),
    [Model] NVARCHAR(100),
    [SerialNumber] NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    [IsActive] BIT NOT NULL DEFAULT 1,
    CONSTRAINT [PK_SignalInterface] PRIMARY KEY ([SignalInterface_ID])
);

CREATE TABLE [dbo].[SignalInterfacePort] (
    [SignalInterfacePort_ID] INT IDENTITY(1,1) NOT NULL,
    [SignalInterface_ID] INT NOT NULL,
    [PortIdentifier] NVARCHAR(100) NOT NULL,
    [SignalInterfacePortKind_ID] INT NOT NULL,
    [Description] NVARCHAR(MAX),
    [IsActive] BIT NOT NULL DEFAULT 1,
    CONSTRAINT [PK_SignalInterfacePort] PRIMARY KEY ([SignalInterfacePort_ID])
);

CREATE TABLE [dbo].[Site] (
    [Site_ID] INT IDENTITY(1,1) NOT NULL,
    [Watershed_ID] INT,
    [Name] NVARCHAR(100),
    [SiteKind_ID] INT,
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
    [QualityCode] INT,
    CONSTRAINT [PK_Value] PRIMARY KEY ([Observation_ID])
);

CREATE TABLE [dbo].[ValueBin] (
    [ValueBin_ID] INT IDENTITY(1,1) NOT NULL,
    [ValueBinningAxis_ID] INT NOT NULL,
    [BinIndex] INT NOT NULL,
    [LowerBound] FLOAT,
    [UpperBound] FLOAT,
    [NominalValue] FLOAT,
    CONSTRAINT [PK_ValueBin] PRIMARY KEY ([ValueBin_ID]),
    CONSTRAINT [UQ_ValueBin_AxisIndex] UNIQUE ([ValueBinningAxis_ID], [BinIndex]),
    CONSTRAINT [CK_ValueBin_BinValues] CHECK (((LowerBound IS NULL AND UpperBound IS NULL) OR (LowerBound IS NOT NULL AND UpperBound IS NOT NULL)) AND (LowerBound IS NULL OR UpperBound > LowerBound) AND (NominalValue IS NOT NULL OR LowerBound IS NOT NULL)
)
);

CREATE TABLE [dbo].[ValueBinningAxis] (
    [ValueBinningAxis_ID] INT IDENTITY(1,1) NOT NULL,
    [Name] NVARCHAR(200) NOT NULL,
    [Description] NVARCHAR(500),
    [NumberOfBins] INT NOT NULL,
    [Unit_ID] INT NOT NULL,
    [BinKind_ID] INT NOT NULL DEFAULT 1,
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
























CREATE INDEX [IX_Annotation_Channel_Time] ON [dbo].[Annotation] ([Channel_ID], [StartTime], [EndTime]);
CREATE INDEX [IX_Annotation_Author] ON [dbo].[Annotation] ([AuthorPerson_ID], [CreatedDateTime]);




CREATE UNIQUE INDEX [UQ_Channel_SignalStream] ON [dbo].[Channel] ([SignalInterface_ID], [TagName], [Parameter_ID], [DataProvenanceKind_ID], [ProcessingKind_ID]);
CREATE INDEX [IX_Channel_ParentChannel] ON [dbo].[Channel] ([ParentChannel_ID]);


CREATE UNIQUE INDEX [UQ_ChannelPortHistory_ActiveRow] ON [dbo].[ChannelPortHistory] ([Channel_ID]);
CREATE INDEX [IX_ChannelPortHistory_Port] ON [dbo].[ChannelPortHistory] ([SignalInterfacePort_ID], [ValidFrom]);


CREATE UNIQUE INDEX [UQ_ControlLoopApplication_ActiveRow] ON [dbo].[ControlLoopApplication] ([ControlLoop_ID]);

CREATE UNIQUE INDEX [UQ_ControlLoopPort_LoopChannel] ON [dbo].[ControlLoopPort] ([ControlLoop_ID], [Channel_ID]);





CREATE INDEX [IX_EquipmentEvent_Equipment_Start] ON [dbo].[EquipmentEvent] ([Equipment_ID], [EventDateTimeStart]);

CREATE UNIQUE INDEX [UQ_EquipmentLocationHistory_ActiveRow] ON [dbo].[EquipmentLocationHistory] ([Equipment_ID]);
CREATE INDEX [IX_EquipmentLocationHistory_SamplingPoint] ON [dbo].[EquipmentLocationHistory] ([SamplingPoint_ID], [ValidFrom]);



CREATE UNIQUE INDEX [UQ_EquipmentWiringHistory_ActiveRow] ON [dbo].[EquipmentWiringHistory] ([Equipment_ID]);
CREATE INDEX [IX_EquipmentWiringHistory_Interface] ON [dbo].[EquipmentWiringHistory] ([SignalInterface_ID], [ValidFrom]);







CREATE INDEX [IX_ProcessingLineage_Channel] ON [dbo].[ProcessingLineage] ([Channel_ID]);
CREATE INDEX [IX_Lineage_Step_Role] ON [dbo].[ProcessingLineage] ([ProcessingStep_ID], [RoleInProcessingStep]);




CREATE UNIQUE INDEX [UQ_SignalInterface_DAS_Name] ON [dbo].[SignalInterface] ([DataAcquisitionSystem_ID], [Name]);

CREATE UNIQUE INDEX [UQ_SignalInterfacePort_Interface_PortId] ON [dbo].[SignalInterfacePort] ([SignalInterface_ID], [PortIdentifier]);









ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_AnnotationKind] FOREIGN KEY ([AnnotationKind_ID]) REFERENCES [dbo].[AnnotationKind] ([AnnotationKind_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Person] FOREIGN KEY ([AuthorPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_EquipmentEvent] FOREIGN KEY ([EquipmentEvent_ID]) REFERENCES [dbo].[EquipmentEvent] ([EquipmentEvent_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Observation] FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
ALTER TABLE [dbo].[Campaign] ADD CONSTRAINT [FK_Campaign_CampaignKind] FOREIGN KEY ([CampaignKind_ID]) REFERENCES [dbo].[CampaignKind] ([CampaignKind_ID]);
ALTER TABLE [dbo].[Campaign] ADD CONSTRAINT [FK_Campaign_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]);
ALTER TABLE [dbo].[Campaign] ADD CONSTRAINT [FK_Campaign_Person] FOREIGN KEY ([ResponsiblePerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[CampaignEquipment] ADD CONSTRAINT [FK_CampaignEquipment_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[CampaignEquipment] ADD CONSTRAINT [FK_CampaignEquipment_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[CampaignSamplingLocation] ADD CONSTRAINT [FK_CampaignSamplingLocation_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[CampaignSamplingLocation] ADD CONSTRAINT [FK_CampaignSamplingLocation_SamplingPoint] FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_SignalInterface] FOREIGN KEY ([SignalInterface_ID]) REFERENCES [dbo].[SignalInterface] ([SignalInterface_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_SignalInterfacePort] FOREIGN KEY ([SignalInterfacePort_ID]) REFERENCES [dbo].[SignalInterfacePort] ([SignalInterfacePort_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_Channel] FOREIGN KEY ([ParentChannel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_ChannelKind] FOREIGN KEY ([ChannelKind_ID]) REFERENCES [dbo].[ChannelKind] ([ChannelKind_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_Parameter] FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_DataProvenanceKind] FOREIGN KEY ([DataProvenanceKind_ID]) REFERENCES [dbo].[DataProvenanceKind] ([DataProvenanceKind_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_ProcessingKind] FOREIGN KEY ([ProcessingKind_ID]) REFERENCES [dbo].[ProcessingKind] ([ProcessingKind_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_ValueKind] FOREIGN KEY ([ValueKind_ID]) REFERENCES [dbo].[ValueKind] ([ValueKind_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_Unit] FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);
ALTER TABLE [dbo].[ChannelAxis] ADD CONSTRAINT [FK_ChannelAxis_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ChannelAxis] ADD CONSTRAINT [FK_ChannelAxis_ValueBinningAxis] FOREIGN KEY ([ValueBinningAxis_ID]) REFERENCES [dbo].[ValueBinningAxis] ([ValueBinningAxis_ID]);
ALTER TABLE [dbo].[ChannelPortHistory] ADD CONSTRAINT [FK_ChannelPortHistory_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ChannelPortHistory] ADD CONSTRAINT [FK_ChannelPortHistory_SignalInterfacePort] FOREIGN KEY ([SignalInterfacePort_ID]) REFERENCES [dbo].[SignalInterfacePort] ([SignalInterfacePort_ID]);
ALTER TABLE [dbo].[ControlLoop] ADD CONSTRAINT [FK_ControlLoop_ControlLoop] FOREIGN KEY ([FallbackControlLoop_ID]) REFERENCES [dbo].[ControlLoop] ([ControlLoop_ID]);
ALTER TABLE [dbo].[ControlLoopApplication] ADD CONSTRAINT [FK_ControlLoopApplication_ControlLoop] FOREIGN KEY ([ControlLoop_ID]) REFERENCES [dbo].[ControlLoop] ([ControlLoop_ID]);
ALTER TABLE [dbo].[ControlLoopApplication] ADD CONSTRAINT [FK_ControlLoopApplication_Person] FOREIGN KEY ([AppliedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[ControlLoopPort] ADD CONSTRAINT [FK_ControlLoopPort_ControlLoop] FOREIGN KEY ([ControlLoop_ID]) REFERENCES [dbo].[ControlLoop] ([ControlLoop_ID]);
ALTER TABLE [dbo].[ControlLoopPort] ADD CONSTRAINT [FK_ControlLoopPort_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ControlLoopPort] ADD CONSTRAINT [FK_ControlLoopPort_ControlLoopPortKind] FOREIGN KEY ([ControlLoopPortKind_ID]) REFERENCES [dbo].[ControlLoopPortKind] ([ControlLoopPortKind_ID]);
ALTER TABLE [dbo].[DataAcquisitionSystem] ADD CONSTRAINT [FK_DataAcquisitionSystem_DataAcquisitionSystem] FOREIGN KEY ([ParentSystem_ID]) REFERENCES [dbo].[DataAcquisitionSystem] ([DataAcquisitionSystem_ID]);
ALTER TABLE [dbo].[Dataset] ADD CONSTRAINT [FK_Dataset_Person] FOREIGN KEY ([CreatedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[DatasetChannel] ADD CONSTRAINT [FK_DatasetChannel_Dataset] FOREIGN KEY ([Dataset_ID]) REFERENCES [dbo].[Dataset] ([Dataset_ID]);
ALTER TABLE [dbo].[DatasetChannel] ADD CONSTRAINT [FK_DatasetChannel_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[Equipment] ADD CONSTRAINT [FK_Equipment_EquipmentModel] FOREIGN KEY ([EquipmentModel_ID]) REFERENCES [dbo].[EquipmentModel] ([EquipmentModel_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_EquipmentEventKind] FOREIGN KEY ([EquipmentEventKind_ID]) REFERENCES [dbo].[EquipmentEventKind] ([EquipmentEventKind_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_Person] FOREIGN KEY ([PerformedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[EquipmentLocationHistory] ADD CONSTRAINT [FK_EquipmentLocationHistory_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[EquipmentLocationHistory] ADD CONSTRAINT [FK_EquipmentLocationHistory_SamplingPoint] FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);
ALTER TABLE [dbo].[EquipmentLocationHistory] ADD CONSTRAINT [FK_EquipmentLocationHistory_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[EquipmentModelHasParameter] ADD CONSTRAINT [FK_EquipmentModelHasParameter_EquipmentModel] FOREIGN KEY ([EquipmentModel_ID]) REFERENCES [dbo].[EquipmentModel] ([EquipmentModel_ID]);
ALTER TABLE [dbo].[EquipmentModelHasParameter] ADD CONSTRAINT [FK_EquipmentModelHasParameter_Parameter] FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);
ALTER TABLE [dbo].[EquipmentModelHasProcedures] ADD CONSTRAINT [FK_EquipmentModelHasProcedures_EquipmentModel] FOREIGN KEY ([EquipmentModel_ID]) REFERENCES [dbo].[EquipmentModel] ([EquipmentModel_ID]);
ALTER TABLE [dbo].[EquipmentModelHasProcedures] ADD CONSTRAINT [FK_EquipmentModelHasProcedures_Procedures] FOREIGN KEY ([Procedure_ID]) REFERENCES [dbo].[Procedures] ([Procedure_ID]);
ALTER TABLE [dbo].[EquipmentWiringHistory] ADD CONSTRAINT [FK_EquipmentWiringHistory_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[EquipmentWiringHistory] ADD CONSTRAINT [FK_EquipmentWiringHistory_SignalInterface] FOREIGN KEY ([SignalInterface_ID]) REFERENCES [dbo].[SignalInterface] ([SignalInterface_ID]);
ALTER TABLE [dbo].[EquipmentWiringHistory] ADD CONSTRAINT [FK_EquipmentWiringHistory_SignalInterfacePort] FOREIGN KEY ([SignalInterfacePort_ID]) REFERENCES [dbo].[SignalInterfacePort] ([SignalInterfacePort_ID]);
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
ALTER TABLE [dbo].[ProcessUnit] ADD CONSTRAINT [FK_ProcessUnit_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]);
ALTER TABLE [dbo].[ProcessUnit] ADD CONSTRAINT [FK_ProcessUnit_ProcessUnitKind] FOREIGN KEY ([ProcessUnitKind_ID]) REFERENCES [dbo].[ProcessUnitKind] ([ProcessUnitKind_ID]);
ALTER TABLE [dbo].[ProcessUnit] ADD CONSTRAINT [FK_ProcessUnit_ProcessUnit] FOREIGN KEY ([Parent_ID]) REFERENCES [dbo].[ProcessUnit] ([ProcessUnit_ID]);
ALTER TABLE [dbo].[ProcessingLineage] ADD CONSTRAINT [FK_ProcessingLineage_ProcessingStep] FOREIGN KEY ([ProcessingStep_ID]) REFERENCES [dbo].[ProcessingStep] ([ProcessingStep_ID]);
ALTER TABLE [dbo].[ProcessingLineage] ADD CONSTRAINT [FK_ProcessingLineage_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ProcessingStep] ADD CONSTRAINT [FK_ProcessingStep_Person] FOREIGN KEY ([ExecutedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[ProcessingStep] ADD CONSTRAINT [FK_ProcessingStep_Dataset] FOREIGN KEY ([Dataset_ID]) REFERENCES [dbo].[Dataset] ([Dataset_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_Sample] FOREIGN KEY ([ParentSample_ID]) REFERENCES [dbo].[Sample] ([Sample_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_SampleKind] FOREIGN KEY ([SampleKind_ID]) REFERENCES [dbo].[SampleKind] ([SampleKind_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_SamplingPoint] FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_Person] FOREIGN KEY ([SampledByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_SampleCollectionKind] FOREIGN KEY ([SampleCollectionKind_ID]) REFERENCES [dbo].[SampleCollectionKind] ([SampleCollectionKind_ID]);
ALTER TABLE [dbo].[Sample] ADD CONSTRAINT [FK_Sample_Equipment] FOREIGN KEY ([SampleEquipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[SamplingPoint] ADD CONSTRAINT [FK_SamplingPoint_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]);
ALTER TABLE [dbo].[SamplingPoint] ADD CONSTRAINT [FK_SamplingPoint_ProcessUnit] FOREIGN KEY ([ProcessUnit_ID]) REFERENCES [dbo].[ProcessUnit] ([ProcessUnit_ID]);
ALTER TABLE [dbo].[SamplingPoint] ADD CONSTRAINT [FK_SamplingPoint_Campaign] FOREIGN KEY ([CreatedByCampaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[SignalInterface] ADD CONSTRAINT [FK_SignalInterface_DataAcquisitionSystem] FOREIGN KEY ([DataAcquisitionSystem_ID]) REFERENCES [dbo].[DataAcquisitionSystem] ([DataAcquisitionSystem_ID]);
ALTER TABLE [dbo].[SignalInterface] ADD CONSTRAINT [FK_SignalInterface_SignalInterfaceKind] FOREIGN KEY ([SignalInterfaceKind_ID]) REFERENCES [dbo].[SignalInterfaceKind] ([SignalInterfaceKind_ID]);
ALTER TABLE [dbo].[SignalInterfacePort] ADD CONSTRAINT [FK_SignalInterfacePort_SignalInterface] FOREIGN KEY ([SignalInterface_ID]) REFERENCES [dbo].[SignalInterface] ([SignalInterface_ID]);
ALTER TABLE [dbo].[SignalInterfacePort] ADD CONSTRAINT [FK_SignalInterfacePort_SignalInterfacePortKind] FOREIGN KEY ([SignalInterfacePortKind_ID]) REFERENCES [dbo].[SignalInterfacePortKind] ([SignalInterfacePortKind_ID]);
ALTER TABLE [dbo].[Site] ADD CONSTRAINT [FK_Site_Watershed] FOREIGN KEY ([Watershed_ID]) REFERENCES [dbo].[Watershed] ([Watershed_ID]);
ALTER TABLE [dbo].[Site] ADD CONSTRAINT [FK_Site_SiteKind] FOREIGN KEY ([SiteKind_ID]) REFERENCES [dbo].[SiteKind] ([SiteKind_ID]);
ALTER TABLE [dbo].[UrbanCharacteristics] ADD CONSTRAINT [FK_UrbanCharacteristics_Watershed] FOREIGN KEY ([Watershed_ID]) REFERENCES [dbo].[Watershed] ([Watershed_ID]);
ALTER TABLE [dbo].[Value] ADD CONSTRAINT [FK_Value_Observation] FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
ALTER TABLE [dbo].[ValueBin] ADD CONSTRAINT [FK_ValueBin_ValueBinningAxis] FOREIGN KEY ([ValueBinningAxis_ID]) REFERENCES [dbo].[ValueBinningAxis] ([ValueBinningAxis_ID]);
ALTER TABLE [dbo].[ValueBinningAxis] ADD CONSTRAINT [FK_ValueBinningAxis_Unit] FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);
ALTER TABLE [dbo].[ValueBinningAxis] ADD CONSTRAINT [FK_ValueBinningAxis_BinKind] FOREIGN KEY ([BinKind_ID]) REFERENCES [dbo].[BinKind] ([BinKind_ID]);
ALTER TABLE [dbo].[ValueImage] ADD CONSTRAINT [FK_ValueImage_Observation] FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_Observation] FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_RowValueBin] FOREIGN KEY ([RowValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_ColValueBin] FOREIGN KEY ([ColValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);
ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [FK_ValueVector_Observation] FOREIGN KEY ([Observation_ID]) REFERENCES [dbo].[Observation] ([Observation_ID]);
ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [FK_ValueVector_ValueBin] FOREIGN KEY ([ValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);

-- Views
GO
CREATE OR ALTER VIEW [dbo].[vw_ChannelEquipmentAtTime] AS
WITH channel_wiring AS (
    SELECT
        o.[Observation_ID] AS ObservationID,
        c.[Channel_ID]     AS ChannelID,
        o.[Timestamp]      AS Timestamp,
        c.[SignalInterface_ID],
        c.[SignalInterfacePort_ID],
        ewh.[Equipment_ID] AS EquipmentID,
        ROW_NUMBER() OVER (
            PARTITION BY o.[Observation_ID]
            ORDER BY
                CASE WHEN ewh.[SignalInterfacePort_ID] IS NOT NULL THEN 0 ELSE 1 END,
                ewh.[ValidFrom] DESC
        ) AS rn,
        COUNT(*) OVER (PARTITION BY o.[Observation_ID]) AS match_count
    FROM [dbo].[Observation] o
    JOIN [dbo].[Channel] c                      ON c.[Channel_ID]           = o.[Channel_ID]
    LEFT JOIN [dbo].[EquipmentWiringHistory] ewh ON ewh.[SignalInterface_ID] = c.[SignalInterface_ID]
                                                AND (
                                                     ewh.[SignalInterfacePort_ID] = c.[SignalInterfacePort_ID]
                                                     OR (ewh.[SignalInterfacePort_ID] IS NULL AND c.[SignalInterfacePort_ID] IS NULL)
                                                     OR c.[SignalInterfacePort_ID] IS NULL
                                                    )
                                                AND ewh.[ValidFrom] <= o.[Timestamp]
                                                AND (ewh.[ValidTo] IS NULL OR ewh.[ValidTo] > o.[Timestamp])
)
SELECT
    cw.ObservationID,
    cw.ChannelID,
    cw.Timestamp,
    CASE WHEN cw.match_count > 1 AND cw.[SignalInterfacePort_ID] IS NULL THEN NULL ELSE cw.EquipmentID END AS EquipmentID,
    e.[Identifier]     AS EquipmentName,
    CASE
        WHEN cw.EquipmentID IS NULL AND cw.match_count = 0 THEN N'unlinked'
        WHEN cw.match_count > 1 AND cw.[SignalInterfacePort_ID] IS NULL THEN N'ambiguous'
        ELSE N'resolved'
    END AS Resolution
FROM channel_wiring cw
LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = cw.EquipmentID
WHERE cw.rn = 1;

GO
CREATE OR ALTER VIEW [dbo].[vw_ChannelLocationAtTime] AS
SELECT
    cea.ObservationID,
    cea.ChannelID,
    cea.Timestamp,
    cea.EquipmentID,
    elh.[SamplingPoint_ID] AS SamplingPointID,
    sp.[SamplingPoint]     AS SamplingPointName
FROM [dbo].[vw_ChannelEquipmentAtTime] cea
LEFT JOIN [dbo].[EquipmentLocationHistory] elh ON elh.[Equipment_ID] = cea.EquipmentID
                                              AND elh.[ValidFrom]   <= cea.Timestamp
                                              AND (elh.[ValidTo] IS NULL OR elh.[ValidTo] > cea.Timestamp)
LEFT JOIN [dbo].[SamplingPoint] sp ON sp.[SamplingPoint_ID] = elh.[SamplingPoint_ID];

GO
CREATE OR ALTER VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Channel_ID]      AS StatusChannelID,
    valueC.[Channel_ID]       AS MeasurementChannelID,
    e.[Equipment_ID]          AS EquipmentID,
    e.[Identifier]            AS EquipmentName,
    p.[Parameter]             AS MeasurementParameter,
    o.[Timestamp],
    CAST(v.[Value] AS INT)    AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]   o       ON o.[Observation_ID]   = v.[Observation_ID]
JOIN [dbo].[Channel]       statusC ON statusC.[Channel_ID] = o.[Channel_ID]
JOIN [dbo].[ChannelKind]   role    ON role.[ChannelKind_ID] = statusC.[ChannelKind_ID]
JOIN [dbo].[Channel]       valueC  ON valueC.[Channel_ID]   = statusC.[ParentChannel_ID]
JOIN [dbo].[Parameter]     p       ON p.[Parameter_ID]     = valueC.[Parameter_ID]
LEFT JOIN [dbo].[EquipmentWiringHistory] ewh
       ON ewh.[SignalInterface_ID] = valueC.[SignalInterface_ID]
      AND (
           ewh.[SignalInterfacePort_ID] = valueC.[SignalInterfacePort_ID]
           OR valueC.[SignalInterfacePort_ID] IS NULL
          )
      AND ewh.[ValidTo] IS NULL
LEFT JOIN [dbo].[Equipment] e ON e.[Equipment_ID] = ewh.[Equipment_ID]
WHERE role.[Name] = N'Status'
  AND statusC.[ParentChannel_ID] IS NOT NULL;

GO
CREATE OR ALTER VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]       AS StatusChannelID,
    e.[Equipment_ID]           AS EquipmentID,
    e.[Identifier]             AS EquipmentName,
    o.[Timestamp],
    CAST(v.[Value] AS INT)     AS StatusCodeID
FROM [dbo].[Value] v
JOIN [dbo].[Observation]  o       ON o.[Observation_ID]   = v.[Observation_ID]
JOIN [dbo].[Channel]      statusC ON statusC.[Channel_ID] = o.[Channel_ID]
JOIN [dbo].[ChannelKind]  role    ON role.[ChannelKind_ID] = statusC.[ChannelKind_ID]
JOIN [dbo].[Channel]      valueC  ON valueC.[Channel_ID]   = statusC.[ParentChannel_ID]
JOIN [dbo].[EquipmentWiringHistory] ewh
       ON ewh.[SignalInterface_ID] = valueC.[SignalInterface_ID]
      AND (
           ewh.[SignalInterfacePort_ID] = valueC.[SignalInterfacePort_ID]
           OR valueC.[SignalInterfacePort_ID] IS NULL
          )
      AND ewh.[ValidTo] IS NULL
JOIN [dbo].[Equipment]    e       ON e.[Equipment_ID]     = ewh.[Equipment_ID]
WHERE role.[Name] = N'Status';

