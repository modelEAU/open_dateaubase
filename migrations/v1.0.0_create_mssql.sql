-- Baseline CREATE script for schema v1.0.0
-- Platform: mssql
-- Generated: 2026-02-14 03:42:59 UTC

CREATE TABLE [dbo].[Comments] (
    [Comment_ID] INT IDENTITY(1,1),
    [Comment] NVARCHAR(MAX),
    CONSTRAINT [PK_Comments] PRIMARY KEY ([Comment_ID])
);

CREATE TABLE [dbo].[Contact] (
    [Contact_ID] INT IDENTITY(1,1),
    [Last_name] NVARCHAR(100),
    [First_name] NVARCHAR(255),
    [Company] NVARCHAR(MAX),
    [Status] NVARCHAR(255),
    [Function] NVARCHAR(MAX),
    [Office_number] NVARCHAR(100),
    [Email] NVARCHAR(100),
    [Phone] NVARCHAR(100),
    [Skype_name] NVARCHAR(100),
    [Linkedin] NVARCHAR(100),
    [Street_number] NVARCHAR(100),
    [Street_name] NVARCHAR(100),
    [City] NVARCHAR(255),
    [Zip_code] NVARCHAR(45),
    [Country] NVARCHAR(255),
    [Website] NVARCHAR(60),
    CONSTRAINT [PK_Contact] PRIMARY KEY ([Contact_ID])
);

CREATE TABLE [dbo].[EquipmentModel] (
    [Equipment_model_ID] INT IDENTITY(1,1),
    [Equipment_model] NVARCHAR(100),
    [Method] NVARCHAR(100),
    [Functions] NVARCHAR(MAX),
    [Manufacturer] NVARCHAR(100),
    [Manual_location] NVARCHAR(100),
    CONSTRAINT [PK_EquipmentModel] PRIMARY KEY ([Equipment_model_ID])
);

CREATE TABLE [dbo].[HydrologicalCharacteristics] (
    [Watershed_ID] INT IDENTITY(1,1),
    [Urban_area] REAL,
    [Forest] REAL,
    [Wetlands] REAL,
    [Cropland] REAL,
    [Meadow] REAL,
    [Grassland] REAL,
    CONSTRAINT [PK_HydrologicalCharacteristics] PRIMARY KEY ([Watershed_ID])
);

CREATE TABLE [dbo].[Procedures] (
    [Procedure_ID] INT IDENTITY(1,1),
    [Procedure_name] NVARCHAR(100),
    [Procedure_type] NVARCHAR(255),
    [Description] NVARCHAR(MAX),
    [Procedure_location] NVARCHAR(100),
    CONSTRAINT [PK_Procedures] PRIMARY KEY ([Procedure_ID])
);

CREATE TABLE [dbo].[Project] (
    [Project_ID] INT IDENTITY(1,1),
    [name] NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_Project] PRIMARY KEY ([Project_ID])
);

CREATE TABLE [dbo].[Purpose] (
    [Purpose_ID] INT IDENTITY(1,1),
    [Purpose] NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_Purpose] PRIMARY KEY ([Purpose_ID])
);

CREATE TABLE [dbo].[Unit] (
    [Unit_ID] INT IDENTITY(1,1),
    [Unit] NVARCHAR(100),
    CONSTRAINT [PK_Unit] PRIMARY KEY ([Unit_ID])
);

CREATE TABLE [dbo].[UrbanCharacteristics] (
    [Watershed_ID] INT IDENTITY(1,1),
    [Commercial] REAL,
    [Green_spaces] REAL,
    [Industrial] REAL,
    [Institutional] REAL,
    [Residential] REAL,
    [Agricultural] REAL,
    [Recreational] REAL,
    CONSTRAINT [PK_UrbanCharacteristics] PRIMARY KEY ([Watershed_ID])
);

CREATE TABLE [dbo].[Watershed] (
    [Watershed_ID] INT IDENTITY(1,1),
    [name] NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    [Surface_area] REAL,
    [Concentration_time] INT,
    [Impervious_surface] REAL,
    CONSTRAINT [PK_Watershed] PRIMARY KEY ([Watershed_ID])
);

CREATE TABLE [dbo].[WeatherCondition] (
    [Condition_ID] INT IDENTITY(1,1),
    [Weather_condition] NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_WeatherCondition] PRIMARY KEY ([Condition_ID])
);

CREATE TABLE [dbo].[Equipment] (
    [Equipment_ID] INT IDENTITY(1,1),
    [model_ID] INT,
    [identifier] NVARCHAR(100),
    [Serial_number] NVARCHAR(100),
    [Owner] NVARCHAR(MAX),
    [Storage_location] NVARCHAR(100),
    [Purchase_date] DATE,
    CONSTRAINT [PK_Equipment] PRIMARY KEY ([Equipment_ID])
);

CREATE TABLE [dbo].[EquipmentModelHasParameter] (
    [Equipment_model_ID] INT,
    [Parameter_ID] INT,
    CONSTRAINT [PK_EquipmentModelHasParameter] PRIMARY KEY ([Equipment_model_ID], [Parameter_ID])
);

CREATE TABLE [dbo].[EquipmentModelHasProcedures] (
    [Equipment_model_ID] INT,
    [Procedure_ID] INT,
    CONSTRAINT [PK_EquipmentModelHasProcedures] PRIMARY KEY ([Equipment_model_ID], [Procedure_ID])
);

CREATE TABLE [dbo].[MetaData] (
    [Metadata_ID] INT IDENTITY(1,1) NOT NULL,
    [Project_ID] INT,
    [Contact_ID] INT,
    [Equipment_ID] INT,
    [Parameter_ID] INT,
    [Procedure_ID] INT,
    [Unit_ID] INT,
    [Purpose_ID] INT,
    [Sampling_point_ID] INT,
    [Condition_ID] INT,
    CONSTRAINT [PK_MetaData] PRIMARY KEY ([Metadata_ID])
);

CREATE TABLE [dbo].[Parameter] (
    [Unit_ID] INT,
    [Parameter] NVARCHAR(100),
    [Parameter_ID] INT IDENTITY(1,1),
    [Description] NVARCHAR(MAX),
    CONSTRAINT [PK_Parameter] PRIMARY KEY ([Parameter_ID])
);

CREATE TABLE [dbo].[ParameterHasProcedures] (
    [Procedure_ID] INT,
    [Parameter_ID] INT,
    CONSTRAINT [PK_ParameterHasProcedures] PRIMARY KEY ([Procedure_ID], [Parameter_ID])
);

CREATE TABLE [dbo].[ProjectHasContact] (
    [Contact_ID] INT,
    [Project_ID] INT,
    CONSTRAINT [PK_ProjectHasContact] PRIMARY KEY ([Contact_ID], [Project_ID])
);

CREATE TABLE [dbo].[ProjectHasEquipment] (
    [Equipment_ID] INT,
    [Project_ID] INT,
    CONSTRAINT [PK_ProjectHasEquipment] PRIMARY KEY ([Equipment_ID], [Project_ID])
);

CREATE TABLE [dbo].[ProjectHasSamplingPoints] (
    [Project_ID] INT,
    [Sampling_point_ID] INT,
    CONSTRAINT [PK_ProjectHasSamplingPoints] PRIMARY KEY ([Project_ID], [Sampling_point_ID])
);

CREATE TABLE [dbo].[SamplingPoints] (
    [Sampling_point_ID] INT IDENTITY(1,1),
    [Site_ID] INT,
    [Sampling_point] NVARCHAR(100),
    [Sampling_location] NVARCHAR(100),
    [Latitude_GPS] NVARCHAR(100),
    [Longitude_GPS] NVARCHAR(100),
    [Description] NVARCHAR(MAX),
    [Pictures] VARBINARY(MAX),
    CONSTRAINT [PK_SamplingPoints] PRIMARY KEY ([Sampling_point_ID])
);

CREATE TABLE [dbo].[Site] (
    [Site_ID] INT IDENTITY(1,1),
    [Watershed_ID] INT,
    [name] NVARCHAR(100),
    [type] NVARCHAR(255),
    [Description] NVARCHAR(MAX),
    [Picture] VARBINARY(MAX),
    [Street_number] NVARCHAR(100),
    [Street_name] NVARCHAR(100),
    [City] NVARCHAR(255),
    [Zip_code] NVARCHAR(100),
    [Province] NVARCHAR(255),
    [Country] NVARCHAR(255),
    CONSTRAINT [PK_Site] PRIMARY KEY ([Site_ID])
);

CREATE TABLE [dbo].[Value] (
    [Comment_ID] INT,
    [Metadata_ID] INT,
    [Value_ID] INT IDENTITY(1,1),
    [Value] FLOAT,
    [Number_of_experiment] INT,
    [Timestamp] INT,
    CONSTRAINT [PK_Value] PRIMARY KEY ([Value_ID])
);
























ALTER TABLE [dbo].[Equipment] ADD CONSTRAINT [FK_Equipment_EquipmentModel] FOREIGN KEY ([model_ID]) REFERENCES [dbo].[EquipmentModel] ([Equipment_model_ID]);
ALTER TABLE [dbo].[EquipmentModelHasParameter] ADD CONSTRAINT [FK_EquipmentModelHasParameter_EquipmentModel] FOREIGN KEY ([Equipment_model_ID]) REFERENCES [dbo].[EquipmentModel] ([Equipment_model_ID]);
ALTER TABLE [dbo].[EquipmentModelHasParameter] ADD CONSTRAINT [FK_EquipmentModelHasParameter_Parameter] FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);
ALTER TABLE [dbo].[EquipmentModelHasProcedures] ADD CONSTRAINT [FK_EquipmentModelHasProcedures_EquipmentModel] FOREIGN KEY ([Equipment_model_ID]) REFERENCES [dbo].[EquipmentModel] ([Equipment_model_ID]);
ALTER TABLE [dbo].[EquipmentModelHasProcedures] ADD CONSTRAINT [FK_EquipmentModelHasProcedures_Procedures] FOREIGN KEY ([Procedure_ID]) REFERENCES [dbo].[Procedures] ([Procedure_ID]);
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_Project] FOREIGN KEY ([Project_ID]) REFERENCES [dbo].[Project] ([Project_ID]);
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_Contact] FOREIGN KEY ([Contact_ID]) REFERENCES [dbo].[Contact] ([Contact_ID]);
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_Parameter] FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_Procedures] FOREIGN KEY ([Procedure_ID]) REFERENCES [dbo].[Procedures] ([Procedure_ID]);
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_Unit] FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_Purpose] FOREIGN KEY ([Purpose_ID]) REFERENCES [dbo].[Purpose] ([Purpose_ID]);
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_SamplingPoints] FOREIGN KEY ([Sampling_point_ID]) REFERENCES [dbo].[SamplingPoints] ([Sampling_point_ID]);
ALTER TABLE [dbo].[MetaData] ADD CONSTRAINT [FK_MetaData_WeatherCondition] FOREIGN KEY ([Condition_ID]) REFERENCES [dbo].[WeatherCondition] ([Condition_ID]);
ALTER TABLE [dbo].[Parameter] ADD CONSTRAINT [FK_Parameter_Unit] FOREIGN KEY ([Unit_ID]) REFERENCES [dbo].[Unit] ([Unit_ID]);
ALTER TABLE [dbo].[ParameterHasProcedures] ADD CONSTRAINT [FK_ParameterHasProcedures_Procedures] FOREIGN KEY ([Procedure_ID]) REFERENCES [dbo].[Procedures] ([Procedure_ID]);
ALTER TABLE [dbo].[ParameterHasProcedures] ADD CONSTRAINT [FK_ParameterHasProcedures_Parameter] FOREIGN KEY ([Parameter_ID]) REFERENCES [dbo].[Parameter] ([Parameter_ID]);
ALTER TABLE [dbo].[ProjectHasContact] ADD CONSTRAINT [FK_ProjectHasContact_Contact] FOREIGN KEY ([Contact_ID]) REFERENCES [dbo].[Contact] ([Contact_ID]);
ALTER TABLE [dbo].[ProjectHasContact] ADD CONSTRAINT [FK_ProjectHasContact_Project] FOREIGN KEY ([Project_ID]) REFERENCES [dbo].[Project] ([Project_ID]);
ALTER TABLE [dbo].[ProjectHasEquipment] ADD CONSTRAINT [FK_ProjectHasEquipment_Equipment] FOREIGN KEY ([Equipment_ID]) REFERENCES [dbo].[Equipment] ([Equipment_ID]);
ALTER TABLE [dbo].[ProjectHasEquipment] ADD CONSTRAINT [FK_ProjectHasEquipment_Project] FOREIGN KEY ([Project_ID]) REFERENCES [dbo].[Project] ([Project_ID]);
ALTER TABLE [dbo].[ProjectHasSamplingPoints] ADD CONSTRAINT [FK_ProjectHasSamplingPoints_Project] FOREIGN KEY ([Project_ID]) REFERENCES [dbo].[Project] ([Project_ID]);
ALTER TABLE [dbo].[ProjectHasSamplingPoints] ADD CONSTRAINT [FK_ProjectHasSamplingPoints_SamplingPoints] FOREIGN KEY ([Sampling_point_ID]) REFERENCES [dbo].[SamplingPoints] ([Sampling_point_ID]);
ALTER TABLE [dbo].[SamplingPoints] ADD CONSTRAINT [FK_SamplingPoints_Site] FOREIGN KEY ([Site_ID]) REFERENCES [dbo].[Site] ([Site_ID]);
ALTER TABLE [dbo].[Site] ADD CONSTRAINT [FK_Site_Watershed] FOREIGN KEY ([Watershed_ID]) REFERENCES [dbo].[Watershed] ([Watershed_ID]);
ALTER TABLE [dbo].[Value] ADD CONSTRAINT [FK_Value_Comments] FOREIGN KEY ([Comment_ID]) REFERENCES [dbo].[Comments] ([Comment_ID]);
ALTER TABLE [dbo].[Value] ADD CONSTRAINT [FK_Value_MetaData] FOREIGN KEY ([Metadata_ID]) REFERENCES [dbo].[MetaData] ([Metadata_ID]);
