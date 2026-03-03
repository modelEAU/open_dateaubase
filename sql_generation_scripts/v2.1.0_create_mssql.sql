-- Baseline CREATE script for schema v2.1.0
-- Platform: mssql
-- Generated: 2026-03-03 17:53:29 UTC

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

CREATE TABLE [dbo].[SensorStatusCode] (
    [StatusCodeID] INT NOT NULL,
    [StatusName] NVARCHAR(50) NOT NULL,
    [Description] NVARCHAR(200),
    [IsOperational] BIT NOT NULL DEFAULT True,
    [Severity] INT NOT NULL DEFAULT 0,
    CONSTRAINT [PK_SensorStatusCode] PRIMARY KEY ([StatusCodeID])
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

CREATE TABLE [dbo].[WeatherCondition] (
    [WeatherCondition_ID] INT IDENTITY(1,1) NOT NULL,
    [WeatherCondition] NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_WeatherCondition] PRIMARY KEY ([WeatherCondition_ID])
);

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
    [Channel_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID] INT,
    [Parameter_ID] INT,
    [DataProvenance_ID] INT,
    [ProcessingDegree_ID] INT DEFAULT 1,
    [ValueType_ID] INT NOT NULL DEFAULT 1,
    [StatusChannel_ID] INT,
    CONSTRAINT [PK_Channel] PRIMARY KEY ([Channel_ID])
);

CREATE TABLE [dbo].[ChannelAxis] (
    [Channel_ID] INT NOT NULL,
    [AxisRole] INT NOT NULL,
    [ValueBinningAxis_ID] INT NOT NULL,
    CONSTRAINT [PK_ChannelAxis] PRIMARY KEY ([Channel_ID], [AxisRole]),
    CONSTRAINT [CK_MetaDataAxis_AxisRole] CHECK (AxisRole IN (0, 1))
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
    [Equipment_ID] INT IDENTITY(1,1) NOT NULL,
    [EquipmentModel_ID] INT,
    [Identifier] NVARCHAR(100),
    [SerialNumber] NVARCHAR(100),
    [Owner] NVARCHAR(MAX),
    [StorageLocation] NVARCHAR(100),
    [PurchaseDate] DATE,
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

CREATE TABLE [dbo].[EquipmentInstallation] (
    [Installation_ID] INT IDENTITY(1,1) NOT NULL,
    [Equipment_ID] INT NOT NULL,
    [SamplingPoint_ID] INT NOT NULL,
    [InstalledDate] DATETIME2(7) NOT NULL,
    [RemovedDate] DATETIME2(7),
    [Campaign_ID] INT,
    [Notes] NVARCHAR(MAX),
    CONSTRAINT [PK_EquipmentInstallation] PRIMARY KEY ([Installation_ID])
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

CREATE TABLE [dbo].[EquipmentStatusChannel] (
    [Equipment_ID] INT NOT NULL,
    [StatusChannel_ID] INT NOT NULL,
    CONSTRAINT [PK_EquipmentStatusChannel] PRIMARY KEY ([Equipment_ID])
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

CREATE TABLE [dbo].[Parameter] (
    [Unit_ID] INT,
    [Parameter] NVARCHAR(100),
    [Parameter_ID] INT IDENTITY(1,1) NOT NULL,
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_Parameter] PRIMARY KEY ([Parameter_ID])
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
    [LatitudeGPS] NVARCHAR(100),
    [LongitudeGPS] NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    [Pictures] /* UNMAPPED TYPE */,
    [ValidFrom] DATETIME2(7),
    [ValidTo] DATETIME2(7),
    [CreatedByCampaign_ID] INT,
    CONSTRAINT [PK_SamplingPoint] PRIMARY KEY ([SamplingPoint_ID])
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
    [Channel_ID] INT,
    [Value_ID] INT IDENTITY(1,1) NOT NULL,
    [Value] FLOAT,
    [Timestamp] DATETIME2(7),
    CONSTRAINT [PK_Value] PRIMARY KEY ([Value_ID])
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
    [ValueImage_ID] BIGINT IDENTITY(1,1) NOT NULL,
    [Channel_ID] INT NOT NULL,
    [Timestamp] DATETIME2(7) NOT NULL,
    [ImageWidth] INT NOT NULL,
    [ImageHeight] INT NOT NULL,
    [NumberOfChannels] INT NOT NULL DEFAULT 3,
    [ImageFormat] NVARCHAR(20) NOT NULL,
    [FileSizeBytes] BIGINT,
    [StorageBackend] NVARCHAR(50) NOT NULL DEFAULT 'FileSystem',
    [StoragePath] NVARCHAR(1000) NOT NULL,
    [Thumbnail] VARBINARY(MAX),
    [QualityCode] INT,
    CONSTRAINT [PK_ValueImage] PRIMARY KEY ([ValueImage_ID]),
    CONSTRAINT [UQ_ValueImage_ChannelTimestamp] UNIQUE ([Channel_ID], [Timestamp])
);

CREATE TABLE [dbo].[ValueMatrix] (
    [Channel_ID] INT NOT NULL,
    [Timestamp] DATETIME2(7) NOT NULL,
    [RowValueBin_ID] INT NOT NULL,
    [ColValueBin_ID] INT NOT NULL,
    [Value] FLOAT,
    [QualityCode] INT,
    CONSTRAINT [PK_ValueMatrix] PRIMARY KEY ([Channel_ID], [Timestamp], [RowValueBin_ID], [ColValueBin_ID])
);

CREATE TABLE [dbo].[ValueVector] (
    [Channel_ID] INT NOT NULL,
    [Timestamp] DATETIME2(7) NOT NULL,
    [ValueBin_ID] INT NOT NULL,
    [Value] FLOAT,
    [QualityCode] INT,
    CONSTRAINT [PK_ValueVector] PRIMARY KEY ([Channel_ID], [Timestamp], [ValueBin_ID])
);


















CREATE INDEX [IX_Annotation_Channel_Time] ON [dbo].[Annotation] ([Channel_ID], [StartTime], [EndTime]);
CREATE INDEX [IX_Annotation_Author] ON [dbo].[Annotation] ([AuthorPerson_ID], [CreatedDateTime]);




CREATE UNIQUE INDEX [UQ_Channel_SensorStream] ON [dbo].[Channel] ([Equipment_ID], [Parameter_ID], [DataProvenance_ID], [ProcessingDegree_ID]);





CREATE INDEX [IX_EquipmentEvent_Equipment_Start] ON [dbo].[EquipmentEvent] ([Equipment_ID], [EventDateTimeStart]);

CREATE INDEX [IX_EquipmentInstallation_Equipment] ON [dbo].[EquipmentInstallation] ([Equipment_ID], [InstalledDate]);
CREATE INDEX [IX_EquipmentInstallation_SamplingPoint] ON [dbo].[EquipmentInstallation] ([SamplingPoint_ID], [InstalledDate]);









CREATE INDEX [IX_ProcessingLineage_Channel] ON [dbo].[ProcessingLineage] ([Channel_ID]);
CREATE INDEX [IX_Lineage_Step_Role] ON [dbo].[ProcessingLineage] ([ProcessingStep_ID], [RoleInProcessingStep]);









CREATE INDEX [IX_ValueImage_ChannelTimestamp] ON [dbo].[ValueImage] ([Channel_ID], [Timestamp]);



ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_AnnotationType] FOREIGN KEY ([AnnotationType_ID]) REFERENCES [dbo].[AnnotationType] ([AnnotationType_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Person] FOREIGN KEY ([AuthorPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[Annotation] ADD CONSTRAINT [FK_Annotation_EquipmentEvent] FOREIGN KEY ([EquipmentEvent_ID]) REFERENCES [dbo].[EquipmentEvent] ([EquipmentEvent_ID]);
ALTER TABLE [dbo].[Campaign] ADD CONSTRAINT [FK_Campaign_CampaignType] FOREIGN KEY ([CampaignType_ID]) REFERENCES [dbo].[CampaignType] ([CampaignType_ID]);
ALTER TABLE [dbo].[Campaign] ADD CONSTRAINT [FK_Campaign_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]);
ALTER TABLE [dbo].[CampaignEquipment] ADD CONSTRAINT [FK_CampaignEquipment_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[CampaignEquipment] ADD CONSTRAINT [FK_CampaignEquipment_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[CampaignSamplingLocation] ADD CONSTRAINT [FK_CampaignSamplingLocation_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[CampaignSamplingLocation] ADD CONSTRAINT [FK_CampaignSamplingLocation_SamplingPoint] FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_Parameter] FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_DataProvenance] FOREIGN KEY ([DataProvenance_ID]) REFERENCES [dbo].[DataProvenance] ([DataProvenance_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_ProcessingDegree] FOREIGN KEY ([ProcessingDegree_ID]) REFERENCES [dbo].[ProcessingDegree] ([ProcessingDegree_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_ValueType] FOREIGN KEY ([ValueType_ID]) REFERENCES [dbo].[ValueType] ([ValueType_ID]);
ALTER TABLE [dbo].[Channel] ADD CONSTRAINT [FK_Channel_Channel] FOREIGN KEY ([StatusChannel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ChannelAxis] ADD CONSTRAINT [FK_ChannelAxis_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ChannelAxis] ADD CONSTRAINT [FK_ChannelAxis_ValueBinningAxis] FOREIGN KEY ([ValueBinningAxis_ID]) REFERENCES [dbo].[ValueBinningAxis] ([ValueBinningAxis_ID]);
ALTER TABLE [dbo].[Dataset] ADD CONSTRAINT [FK_Dataset_Person] FOREIGN KEY ([CreatedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[DatasetChannel] ADD CONSTRAINT [FK_DatasetChannel_Dataset] FOREIGN KEY ([Dataset_ID]) REFERENCES [dbo].[Dataset] ([Dataset_ID]);
ALTER TABLE [dbo].[DatasetChannel] ADD CONSTRAINT [FK_DatasetChannel_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[Equipment] ADD CONSTRAINT [FK_Equipment_EquipmentModel] FOREIGN KEY ([EquipmentModel_ID]) REFERENCES [dbo].[EquipmentModel] ([EquipmentModel_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_EquipmentEventType] FOREIGN KEY ([EquipmentEventType_ID]) REFERENCES [dbo].[EquipmentEventType] ([EquipmentEventType_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_Person] FOREIGN KEY ([PerformedByPerson_ID]) REFERENCES [dbo].[Person] ([Person_ID]);
ALTER TABLE [dbo].[EquipmentEvent] ADD CONSTRAINT [FK_EquipmentEvent_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[EquipmentInstallation] ADD CONSTRAINT [FK_EquipmentInstallation_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[EquipmentInstallation] ADD CONSTRAINT [FK_EquipmentInstallation_SamplingPoint] FOREIGN KEY ([SamplingPoint_ID]) REFERENCES [dbo].[SamplingPoint] ([SamplingPoint_ID]);
ALTER TABLE [dbo].[EquipmentInstallation] ADD CONSTRAINT [FK_EquipmentInstallation_Campaign] FOREIGN KEY ([Campaign_ID]) REFERENCES [dbo].[Campaign] ([Campaign_ID]);
ALTER TABLE [dbo].[EquipmentModelHasParameter] ADD CONSTRAINT [FK_EquipmentModelHasParameter_EquipmentModel] FOREIGN KEY ([EquipmentModel_ID]) REFERENCES [dbo].[EquipmentModel] ([EquipmentModel_ID]);
ALTER TABLE [dbo].[EquipmentModelHasParameter] ADD CONSTRAINT [FK_EquipmentModelHasParameter_Parameter] FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);
ALTER TABLE [dbo].[EquipmentModelHasProcedures] ADD CONSTRAINT [FK_EquipmentModelHasProcedures_EquipmentModel] FOREIGN KEY ([EquipmentModel_ID]) REFERENCES [dbo].[EquipmentModel] ([EquipmentModel_ID]);
ALTER TABLE [dbo].[EquipmentModelHasProcedures] ADD CONSTRAINT [FK_EquipmentModelHasProcedures_Procedures] FOREIGN KEY ([Procedure_ID]) REFERENCES [dbo].[Procedures] ([Procedure_ID]);
ALTER TABLE [dbo].[EquipmentStatusChannel] ADD CONSTRAINT [FK_EquipmentStatusChannel_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[EquipmentStatusChannel] ADD CONSTRAINT [FK_EquipmentStatusChannel_Channel] FOREIGN KEY ([StatusChannel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
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
ALTER TABLE [dbo].[Parameter] ADD CONSTRAINT [FK_Parameter_Unit] FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);
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
ALTER TABLE [dbo].[Site] ADD CONSTRAINT [FK_Site_Watershed] FOREIGN KEY ([Watershed_ID]) REFERENCES [dbo].[Watershed] ([Watershed_ID]);
ALTER TABLE [dbo].[UrbanCharacteristics] ADD CONSTRAINT [FK_UrbanCharacteristics_Watershed] FOREIGN KEY ([Watershed_ID]) REFERENCES [dbo].[Watershed] ([Watershed_ID]);
ALTER TABLE [dbo].[Value] ADD CONSTRAINT [FK_Value_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ValueBin] ADD CONSTRAINT [FK_ValueBin_ValueBinningAxis] FOREIGN KEY ([ValueBinningAxis_ID]) REFERENCES [dbo].[ValueBinningAxis] ([ValueBinningAxis_ID]);
ALTER TABLE [dbo].[ValueBinningAxis] ADD CONSTRAINT [FK_ValueBinningAxis_Unit] FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);
ALTER TABLE [dbo].[ValueImage] ADD CONSTRAINT [FK_ValueImage_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_RowValueBin] FOREIGN KEY ([RowValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);
ALTER TABLE [dbo].[ValueMatrix] ADD CONSTRAINT [FK_ValueMatrix_ColValueBin] FOREIGN KEY ([ColValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);
ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [FK_ValueVector_Channel] FOREIGN KEY ([Channel_ID]) REFERENCES [dbo].[Channel] ([Channel_ID]);
ALTER TABLE [dbo].[ValueVector] ADD CONSTRAINT [FK_ValueVector_ValueBin] FOREIGN KEY ([ValueBin_ID]) REFERENCES [dbo].[ValueBin] ([ValueBin_ID]);

-- Views
CREATE OR ALTER VIEW [dbo].[vw_ChannelStatus] AS
SELECT
    statusC.[Channel_ID]          AS StatusChannelID,
    statusC.[StatusChannel_ID]    AS MeasurementChannelID,
    measC.[Equipment_ID]          AS EquipmentID,
    e.[Identifier]                AS EquipmentName,
    p.[Parameter]                 AS MeasurementParameter,
    v.[Timestamp],
    CAST(v.[Value] AS INT)        AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]               statusC ON statusC.[Channel_ID]      = v.[Channel_ID]
JOIN [dbo].[Channel]               measC   ON measC.[Channel_ID]        = statusC.[StatusChannel_ID]
JOIN [dbo].[Parameter]             p       ON p.[Parameter_ID]          = measC.[Parameter_ID]
JOIN [dbo].[Equipment]             e       ON e.[Equipment_ID]          = measC.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode] sc      ON sc.[StatusCodeID]         = CAST(v.[Value] AS INT)
WHERE statusC.[StatusChannel_ID] IS NOT NULL;

CREATE OR ALTER VIEW [dbo].[vw_DeviceStatus] AS
SELECT
    statusC.[Channel_ID]          AS StatusChannelID,
    esc.[Equipment_ID]            AS EquipmentID,
    e.[Identifier]                AS EquipmentName,
    v.[Timestamp],
    CAST(v.[Value] AS INT)        AS StatusCodeID,
    sc.[StatusName],
    sc.[IsOperational],
    sc.[Severity]
FROM [dbo].[Value] v
JOIN [dbo].[Channel]                 statusC ON statusC.[Channel_ID]   = v.[Channel_ID]
JOIN [dbo].[EquipmentStatusChannel]  esc     ON esc.[StatusChannel_ID] = statusC.[Channel_ID]
JOIN [dbo].[Equipment]               e       ON e.[Equipment_ID]       = esc.[Equipment_ID]
LEFT JOIN [dbo].[SensorStatusCode]   sc      ON sc.[StatusCodeID]      = CAST(v.[Value] AS INT);

