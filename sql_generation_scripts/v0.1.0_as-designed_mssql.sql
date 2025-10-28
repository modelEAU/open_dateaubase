-- Auto-generated SQL schema from Parts metadata table
-- Target database: MSSQL
-- Generated: 2025-10-28T20:58:28.454637



-- Table for Comments
CREATE TABLE [comments] (
    [Comment] nvarchar(1073741823) NULL,
    [Comment_ID] int NULL,
    CONSTRAINT [PK_comments] PRIMARY KEY ([Comment_ID])
);


-- Table for Contact
CREATE TABLE [contact] (
    [Company] nvarchar(1073741823) NULL,
    [Contact_ID] int NULL,
    [Email] nvarchar(100) NULL,
    [First_name] nvarchar(255) NULL,
    [Function] nvarchar(1073741823) NULL,
    [Last_name] nvarchar(100) NULL,
    [Linkedin] nvarchar(100) NULL,
    [Office_number] nvarchar(100) NULL,
    [Phone] nvarchar(100) NULL,
    [Skype_name] nvarchar(100) NULL,
    [Status] nvarchar(255) NULL,
    [Website] nvarchar(60) NULL,
    [City] nvarchar(255) NULL,
    [Country] nvarchar(255) NULL,
    [Street_name] nvarchar(100) NULL,
    [Street_number] nvarchar(100) NULL,
    [Zip_code] nvarchar(45) NULL,
    CONSTRAINT [PK_contact] PRIMARY KEY ([Contact_ID])
);


-- Table for Equipment
CREATE TABLE [equipment] (
    [Equipment_ID] int NULL,
    [Equipment_identifier] nvarchar(100) NULL,
    [Equipment_model_ID] int NULL,
    [Owner] nvarchar(1073741823) NULL,
    [Purchase_date] date NULL,
    [Serial_number] nvarchar(100) NULL,
    [Storage_location] nvarchar(100) NULL,
    CONSTRAINT [PK_equipment] PRIMARY KEY ([Equipment_ID])
);


-- Table for Equipment Model
CREATE TABLE [equipment_model] (
    [Equipment_model] nvarchar(100) NULL,
    [Equipment_model_ID] int NULL,
    [Functions] nvarchar(1073741823) NULL,
    [Manual_location] nvarchar(100) NULL,
    [Manufacturer] nvarchar(100) NULL,
    [Method] nvarchar(100) NULL,
    CONSTRAINT [PK_equipment_model] PRIMARY KEY ([Equipment_model_ID])
);


-- Table for Equipment Model Has Parameter
CREATE TABLE [equipment_model_has_Parameter] (
    [Equipment_model_ID] int NULL,
    [Parameter_ID] int NULL,
    CONSTRAINT [PK_equipment_model_has_Parameter] PRIMARY KEY ([Equipment_model_ID], [Parameter_ID])
);


-- Table for Equipment Model Has Procedures
CREATE TABLE [equipment_model_has_procedures] (
    [Equipment_model_ID] int NULL,
    [Procedure_ID] int NULL,
    CONSTRAINT [PK_equipment_model_has_procedures] PRIMARY KEY ([Equipment_model_ID], [Procedure_ID])
);


-- Table for Hydrological Characteristics
CREATE TABLE [hydrological_characteristics] (
    [Cropland] real NULL,
    [Forest] real NULL,
    [Grassland] real NULL,
    [Meadow] real NULL,
    [Urban_area] real NULL,
    [Watershed_ID] int NULL,
    [Wetlands] real NULL,
    CONSTRAINT [PK_hydrological_characteristics] PRIMARY KEY ([Watershed_ID])
);


-- Table for Metadata
CREATE TABLE [metadata] (
    [Condition_ID] int NULL,
    [Contact_ID] int NULL,
    [Equipment_ID] int NULL,
    [Metadata_ID] int NULL,
    [Parameter_ID] int NULL,
    [Procedure_ID] int NULL,
    [Project_ID] int NULL,
    [Purpose_ID] int NULL,
    [Sampling_point_ID] int NULL,
    [Unit_ID] int NULL,
    CONSTRAINT [PK_metadata] PRIMARY KEY ([Metadata_ID])
);


-- Table for Parameter
CREATE TABLE [parameter] (
    [Parameter] nvarchar(100) NULL,
    [Parameter_ID] int NULL,
    [Unit_ID] int NULL,
    [Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_parameter] PRIMARY KEY ([Parameter_ID])
);


-- Table for Parameter Has Procedures
CREATE TABLE [parameter_has_procedures] (
    [Parameter_ID] int NULL,
    [Procedure_ID] int NULL,
    CONSTRAINT [PK_parameter_has_procedures] PRIMARY KEY ([Parameter_ID], [Procedure_ID])
);


-- Table for Procedures
CREATE TABLE [procedures] (
    [Procedure_ID] int NULL,
    [Procedure_location] nvarchar(100) NULL,
    [Procedure_name] nvarchar(100) NULL,
    [Procedure_type] nvarchar(255) NULL,
    [Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_procedures] PRIMARY KEY ([Procedure_ID])
);


-- Table for Project
CREATE TABLE [project] (
    [Project_ID] int NULL,
    [Project_name] nvarchar(100) NULL,
    [Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_project] PRIMARY KEY ([Project_ID])
);


-- Table for Project Has Contact
CREATE TABLE [project_has_contact] (
    [Contact_ID] int NULL,
    [Project_ID] int NULL,
    CONSTRAINT [PK_project_has_contact] PRIMARY KEY ([Contact_ID], [Project_ID])
);


-- Table for Project Has Equipment
CREATE TABLE [project_has_equipment] (
    [Equipment_ID] int NULL,
    [Project_ID] int NULL,
    CONSTRAINT [PK_project_has_equipment] PRIMARY KEY ([Equipment_ID], [Project_ID])
);


-- Table for Project Has Sampling Points
CREATE TABLE [project_has_sampling_points] (
    [Project_ID] int NULL,
    [Sampling_point_ID] int NULL,
    CONSTRAINT [PK_project_has_sampling_points] PRIMARY KEY ([Project_ID], [Sampling_point_ID])
);


-- Table for Purpose
CREATE TABLE [purpose] (
    [Purpose] nvarchar(100) NULL,
    [Purpose_ID] int NULL,
    [Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_purpose] PRIMARY KEY ([Purpose_ID])
);


-- Table for Sampling Points
CREATE TABLE [sampling_points] (
    [Latitude_GPS] nvarchar(100) NULL,
    [Longitude_GPS] nvarchar(100) NULL,
    [Pictures] BLOB NULL,
    [Sampling_location] nvarchar(100) NULL,
    [Sampling_point] nvarchar(100) NULL,
    [Sampling_point_ID] int NULL,
    [Site_ID] int NULL,
    [points_Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_sampling_points] PRIMARY KEY ([Sampling_point_ID])
);


-- Table for Site
CREATE TABLE [site] (
    [Picture] image(2147483647) NULL,
    [Province] nvarchar(255) NULL,
    [Site_ID] int NULL,
    [Site_name] nvarchar(100) NULL,
    [Site_type] nvarchar(255) NULL,
    [Watershed_ID] int NULL,
    [City] nvarchar(255) NULL,
    [Country] nvarchar(255) NULL,
    [Description] nvarchar(1073741823) NULL,
    [Street_name] nvarchar(100) NULL,
    [Street_number] nvarchar(100) NULL,
    [Zip_code] nvarchar(100) NULL,
    CONSTRAINT [PK_site] PRIMARY KEY ([Site_ID])
);


-- Table for Unit
CREATE TABLE [unit] (
    [Unit] nvarchar(100) NULL,
    [Unit_ID] int NULL,
    CONSTRAINT [PK_unit] PRIMARY KEY ([Unit_ID])
);


-- Table for Urban Characteristics
CREATE TABLE [urban_characteristics] (
    [Agricultural] real NULL,
    [Commercial] real NULL,
    [Green_spaces] real NULL,
    [Industrial] real NULL,
    [Institutional] real NULL,
    [Recreational] real NULL,
    [Residential] real NULL,
    [Watershed_ID] int NULL,
    CONSTRAINT [PK_urban_characteristics] PRIMARY KEY ([Watershed_ID])
);


-- Table for Value
CREATE TABLE [value] (
    [Comment_ID] int NULL,
    [Metadata_ID] int NULL,
    [Number_of_experiment] numeric NULL,
    [Timestamp] int NULL,
    [Value] float NULL,
    [Value_ID] int NULL,
    CONSTRAINT [PK_value] PRIMARY KEY ([Value_ID])
);


-- Table for Watershed
CREATE TABLE [watershed] (
    [Concentration_time] int NULL,
    [Impervious_surface] real NULL,
    [Surface_area] real NULL,
    [Watershed_ID] int NULL,
    [Watershed_name] nvarchar(100) NULL,
    [Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_watershed] PRIMARY KEY ([Watershed_ID])
);


-- Table for Weather Condition
CREATE TABLE [weather_condition] (
    [Condition_ID] int NULL,
    [Weather_condition] nvarchar(100) NULL,
    [condition_Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_weather_condition] PRIMARY KEY ([Condition_ID])
);


-- Foreign Key Constraints

ALTER TABLE [equipment]
    ADD CONSTRAINT [FK_equipment_Equipment_model_ID]
    FOREIGN KEY ([Equipment_model_ID])
    REFERENCES [Equipment_model] ([Equipment_model_ID]);

ALTER TABLE [metadata]
    ADD CONSTRAINT [FK_metadata_Condition_ID]
    FOREIGN KEY ([Condition_ID])
    REFERENCES [Condition] ([Condition_ID]);

ALTER TABLE [metadata]
    ADD CONSTRAINT [FK_metadata_Contact_ID]
    FOREIGN KEY ([Contact_ID])
    REFERENCES [Contact] ([Contact_ID]);

ALTER TABLE [metadata]
    ADD CONSTRAINT [FK_metadata_Equipment_ID]
    FOREIGN KEY ([Equipment_ID])
    REFERENCES [Equipment] ([Equipment_ID]);

ALTER TABLE [metadata]
    ADD CONSTRAINT [FK_metadata_Parameter_ID]
    FOREIGN KEY ([Parameter_ID])
    REFERENCES [Parameter] ([Parameter_ID]);

ALTER TABLE [metadata]
    ADD CONSTRAINT [FK_metadata_Procedure_ID]
    FOREIGN KEY ([Procedure_ID])
    REFERENCES [Procedure] ([Procedure_ID]);

ALTER TABLE [metadata]
    ADD CONSTRAINT [FK_metadata_Project_ID]
    FOREIGN KEY ([Project_ID])
    REFERENCES [Project] ([Project_ID]);

ALTER TABLE [metadata]
    ADD CONSTRAINT [FK_metadata_Purpose_ID]
    FOREIGN KEY ([Purpose_ID])
    REFERENCES [Purpose] ([Purpose_ID]);

ALTER TABLE [metadata]
    ADD CONSTRAINT [FK_metadata_Sampling_point_ID]
    FOREIGN KEY ([Sampling_point_ID])
    REFERENCES [Sampling_point] ([Sampling_point_ID]);

ALTER TABLE [metadata]
    ADD CONSTRAINT [FK_metadata_Unit_ID]
    FOREIGN KEY ([Unit_ID])
    REFERENCES [Unit] ([Unit_ID]);

ALTER TABLE [parameter]
    ADD CONSTRAINT [FK_parameter_Unit_ID]
    FOREIGN KEY ([Unit_ID])
    REFERENCES [Unit] ([Unit_ID]);

ALTER TABLE [sampling_points]
    ADD CONSTRAINT [FK_sampling_points_Site_ID]
    FOREIGN KEY ([Site_ID])
    REFERENCES [Site] ([Site_ID]);

ALTER TABLE [site]
    ADD CONSTRAINT [FK_site_Watershed_ID]
    FOREIGN KEY ([Watershed_ID])
    REFERENCES [Watershed] ([Watershed_ID]);

ALTER TABLE [value]
    ADD CONSTRAINT [FK_value_Comment_ID]
    FOREIGN KEY ([Comment_ID])
    REFERENCES [Comment] ([Comment_ID]);

ALTER TABLE [value]
    ADD CONSTRAINT [FK_value_Metadata_ID]
    FOREIGN KEY ([Metadata_ID])
    REFERENCES [Metadata] ([Metadata_ID]);
