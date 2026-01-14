-- Auto-generated SQL schema from dictionary.json
-- Target database: MSSQL
-- Generated: 2025-12-10T18:46:32.837716



-- Stores any additional textual comments, notes, or observations related to a specific measured value
CREATE TABLE [comments] (
    [Comment] nvarchar(1073741823) NULL,
    [Comment_ID] int NULL,
    CONSTRAINT [PK_comments] PRIMARY KEY ([Comment_ID])
);


-- Stores detailed personal and professional information for people involved in projects (e.g., name, affiliation, function, e-mail, phone)
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


-- Stores information about a specific, physical piece of equipment (e.g., serial number, owner, purchase date, storage location)
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


-- Stores detailed, non-redundant specifications for a specific sensor or instrument model (e.g., manufacturer, functions, method)
CREATE TABLE [equipment_model] (
    [Equipment_model] nvarchar(100) NULL,
    [Equipment_model_ID] int NULL,
    [Functions] nvarchar(1073741823) NULL,
    [Manual_location] nvarchar(100) NULL,
    [Manufacturer] nvarchar(100) NULL,
    [Method] nvarchar(100) NULL,
    CONSTRAINT [PK_equipment_model] PRIMARY KEY ([Equipment_model_ID])
);


-- Links equipment models to the parameters they can measure
CREATE TABLE [equipment_model_has_Parameter] (
    [Equipment_model_ID] int NULL,
    [Parameter_ID] int NULL,
    CONSTRAINT [PK_equipment_model_has_Parameter] PRIMARY KEY ([Equipment_model_ID], [Parameter_ID])
);


-- Links equipment models to the relevant maintenance procedures
CREATE TABLE [equipment_model_has_procedures] (
    [Equipment_model_ID] int NULL,
    [Procedure_ID] int NULL,
    CONSTRAINT [PK_equipment_model_has_procedures] PRIMARY KEY ([Equipment_model_ID], [Procedure_ID])
);


-- Stores the hydrological land use percentages (e.g., forest, wetlands, cropland, grassland) within the watershed
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


-- Contains a list of all existing unique metadata combinations (represented by a series of foreign keys/IDs) that describe a single measurement
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


-- Stores the different water quality or quantity parameters that are measured (e.g., pH, TSS, N-components)
CREATE TABLE [parameter] (
    [Parameter] nvarchar(100) NULL,
    [Parameter_ID] int NULL,
    [Unit_ID] int NULL,
    [Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_parameter] PRIMARY KEY ([Parameter_ID])
);


-- Links parameters to the relevant measurement procedures
CREATE TABLE [parameter_has_procedures] (
    [Parameter_ID] int NULL,
    [Procedure_ID] int NULL,
    CONSTRAINT [PK_parameter_has_procedures] PRIMARY KEY ([Parameter_ID], [Procedure_ID])
);


-- Stores details for different measurement procedures (e.g., calibration, validation, standard operating procedures, ISO methods)
CREATE TABLE [procedures] (
    [Procedure_ID] int NULL,
    [Procedure_location] nvarchar(100) NULL,
    [Procedure_name] nvarchar(100) NULL,
    [Procedure_type] nvarchar(255) NULL,
    [Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_procedures] PRIMARY KEY ([Procedure_ID])
);


-- Stores descriptive information about the research or monitoring project for which the data was collected
CREATE TABLE [project] (
    [Project_ID] int NULL,
    [Project_name] nvarchar(100) NULL,
    [Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_project] PRIMARY KEY ([Project_ID])
);


-- Links projects to the personnel involved in them
CREATE TABLE [project_has_contact] (
    [Contact_ID] int NULL,
    [Project_ID] int NULL,
    CONSTRAINT [PK_project_has_contact] PRIMARY KEY ([Contact_ID], [Project_ID])
);


-- Links projects to the specific equipment used within them
CREATE TABLE [project_has_equipment] (
    [Equipment_ID] int NULL,
    [Project_ID] int NULL,
    CONSTRAINT [PK_project_has_equipment] PRIMARY KEY ([Equipment_ID], [Project_ID])
);


-- Links projects to the sampling points used within them
CREATE TABLE [project_has_sampling_points] (
    [Project_ID] int NULL,
    [Sampling_point_ID] int NULL,
    CONSTRAINT [PK_project_has_sampling_points] PRIMARY KEY ([Project_ID], [Sampling_point_ID])
);


-- Stores information about the aim of the measurement (e.g., on-line measurement, laboratory analysis, calibration, validation, cleaning)
CREATE TABLE [purpose] (
    [Purpose] nvarchar(100) NULL,
    [Purpose_ID] int NULL,
    [Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_purpose] PRIMARY KEY ([Purpose_ID])
);


-- Stores the identification, specific geographical coordinates (Latitude/Longitude/GPS), and description of a particular spot where a sample or measurement is taken
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


-- Stores general site information, including address, site type, and a link to the associated watershed
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


-- Stores the SI units of measurement (or other relevant units) corresponding to the parameters (e.g., mg/L, g/L, s)
CREATE TABLE [unit] (
    [Unit] nvarchar(100) NULL,
    [Unit_ID] int NULL,
    CONSTRAINT [PK_unit] PRIMARY KEY ([Unit_ID])
);


-- Stores the urban land use percentages (e.g., commercial, residential, green spaces) within the watershed
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


-- Stores each measured water quality or quantity value, its time stamp, replicate identification, and the link to its specific metadata set
CREATE TABLE [value] (
    [Comment_ID] int NULL,
    [Metadata_ID] int NULL,
    [Number_of_experiment] numeric NULL,
    [Timestamp] int NULL,
    [Value] float NULL,
    [Value_ID] int NULL,
    CONSTRAINT [PK_value] PRIMARY KEY ([Value_ID])
);


-- Stores general information about the watershed area, including surface area, concentration time, and impervious surface percentage
CREATE TABLE [watershed] (
    [Concentration_time] int NULL,
    [Impervious_surface] real NULL,
    [Surface_area] real NULL,
    [Watershed_ID] int NULL,
    [Watershed_name] nvarchar(100) NULL,
    [Description] nvarchar(1073741823) NULL,
    CONSTRAINT [PK_watershed] PRIMARY KEY ([Watershed_ID])
);


-- Stores descriptive information about the prevailing weather conditions when the measurement was taken (e.g., dry weather, wet weather, snow melt)
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

ALTER TABLE [equipment_model_has_Parameter]
    ADD CONSTRAINT [FK_equipment_model_has_Parameter_Equipment_model_ID]
    FOREIGN KEY ([Equipment_model_ID])
    REFERENCES [Equipment_model] ([Equipment_model_ID]);

ALTER TABLE [equipment_model_has_procedures]
    ADD CONSTRAINT [FK_equipment_model_has_procedures_Equipment_model_ID]
    FOREIGN KEY ([Equipment_model_ID])
    REFERENCES [Equipment_model] ([Equipment_model_ID]);

ALTER TABLE [equipment_model_has_procedures]
    ADD CONSTRAINT [FK_equipment_model_has_procedures_Procedure_ID]
    FOREIGN KEY ([Procedure_ID])
    REFERENCES [Procedure] ([Procedure_ID]);

ALTER TABLE [hydrological_characteristics]
    ADD CONSTRAINT [FK_hydrological_characteristics_Watershed_ID]
    FOREIGN KEY ([Watershed_ID])
    REFERENCES [Watershed] ([Watershed_ID]);

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

ALTER TABLE [parameter_has_procedures]
    ADD CONSTRAINT [FK_parameter_has_procedures_Procedure_ID]
    FOREIGN KEY ([Procedure_ID])
    REFERENCES [Procedure] ([Procedure_ID]);

ALTER TABLE [project_has_contact]
    ADD CONSTRAINT [FK_project_has_contact_Contact_ID]
    FOREIGN KEY ([Contact_ID])
    REFERENCES [Contact] ([Contact_ID]);

ALTER TABLE [project_has_contact]
    ADD CONSTRAINT [FK_project_has_contact_Project_ID]
    FOREIGN KEY ([Project_ID])
    REFERENCES [Project] ([Project_ID]);

ALTER TABLE [project_has_equipment]
    ADD CONSTRAINT [FK_project_has_equipment_Equipment_ID]
    FOREIGN KEY ([Equipment_ID])
    REFERENCES [Equipment] ([Equipment_ID]);

ALTER TABLE [project_has_equipment]
    ADD CONSTRAINT [FK_project_has_equipment_Project_ID]
    FOREIGN KEY ([Project_ID])
    REFERENCES [Project] ([Project_ID]);

ALTER TABLE [project_has_sampling_points]
    ADD CONSTRAINT [FK_project_has_sampling_points_Project_ID]
    FOREIGN KEY ([Project_ID])
    REFERENCES [Project] ([Project_ID]);

ALTER TABLE [project_has_sampling_points]
    ADD CONSTRAINT [FK_project_has_sampling_points_Sampling_point_ID]
    FOREIGN KEY ([Sampling_point_ID])
    REFERENCES [Sampling_point] ([Sampling_point_ID]);

ALTER TABLE [sampling_points]
    ADD CONSTRAINT [FK_sampling_points_Site_ID]
    FOREIGN KEY ([Site_ID])
    REFERENCES [Site] ([Site_ID]);

ALTER TABLE [site]
    ADD CONSTRAINT [FK_site_Watershed_ID]
    FOREIGN KEY ([Watershed_ID])
    REFERENCES [Watershed] ([Watershed_ID]);

ALTER TABLE [urban_characteristics]
    ADD CONSTRAINT [FK_urban_characteristics_Watershed_ID]
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
