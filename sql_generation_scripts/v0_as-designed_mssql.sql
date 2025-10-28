CREATE TABLE [hydrological_characteristics] (
  [Watershed_ID] int,
  [Urban_area] real,
  [Forest] real,
  [Wetlands] real,
  [Cropland] real,
  [Meadow] real,
  [Grassland] real,
  PRIMARY KEY ([Watershed_ID])
);

CREATE TABLE [purpose] (
  [Purpose_ID] int,
  [Purpose] nvarchar(100),
  [Description] ntext(1073741823),
  PRIMARY KEY ([Purpose_ID])
);

CREATE TABLE [equipment_model] (
  [Equipment_model_ID] int,
  [Equipment_model] nvarchar(100),
  [Method] nvarchar(100),
  [Functions] ntext(1073741823),
  [Manufacturer] nvarchar(100),
  [Manual_location] nvarchar(100),
  PRIMARY KEY ([Equipment_model_ID])
);

CREATE TABLE [equipment] (
  [Equipment_ID] int,
  [Equipment_identifier] nvarchar(100),
  [Serial_number] nvarchar(100),
  [Owner] ntext(1073741823),
  [Storage_location] nvarchar(100),
  [Purchase_date] date,
  [Equipment_model_ID] int,
  PRIMARY KEY ([Equipment_ID]),
  CONSTRAINT [FK_equipment_Equipment_model_ID]
    FOREIGN KEY ([Equipment_model_ID])
      REFERENCES [equipment_model]([Equipment_model_ID])
);

CREATE TABLE [procedures] (
  [Procedure_ID] int,
  [Procedure_name] nvarchar(100),
  [Procedure_type] nvarchar(255),
  [Description] ntext(1073741823),
  [Procedure_location] nvarchar(100),
  PRIMARY KEY ([Procedure_ID])
);

CREATE TABLE [equipment_model_has_Parameter] (
  [Equipment_model_ID] int,
  [Parameter_ID] int,
  PRIMARY KEY ([Equipment_model_ID], [Parameter_ID]),
  CONSTRAINT [FK_equipment_model_has_Parameter_Parameter_ID]
    FOREIGN KEY ([Parameter_ID])
      REFERENCES [procedures]([Procedure_ID]),
  CONSTRAINT [FK_equipment_model_has_Parameter_Equipment_model_ID]
    FOREIGN KEY ([Equipment_model_ID])
      REFERENCES [equipment_model]([Equipment_model_ID])
);

CREATE TABLE [project] (
  [Project_ID] int,
  [Project_name] nvarchar(100),
  [Description] ntext(1073741823),
  PRIMARY KEY ([Project_ID])
);

CREATE TABLE [project_has_equipment] (
  [Project_ID] int,
  [Equipment_ID] int,
  PRIMARY KEY ([Project_ID], [Equipment_ID]),
  CONSTRAINT [FK_project_has_equipment_Equipment_ID]
    FOREIGN KEY ([Equipment_ID])
      REFERENCES [equipment]([Equipment_ID]),
  CONSTRAINT [FK_project_has_equipment_Project_ID]
    FOREIGN KEY ([Project_ID])
      REFERENCES [project]([Project_ID])
);

CREATE TABLE [watershed] (
  [Watershed_ID] int,
  [Watershed_name] nvarchar(100),
  [Description] ntext(1073741823),
  [Surface_area] real,
  [Concentration_time] int,
  [Impervious_surface] real,
  PRIMARY KEY ([Watershed_ID])
);

CREATE TABLE [site] (
  [Site_ID] int,
  [Site_name] nvarchar(100),
  [Site_type] nvarchar(255),
  [Watershed_ID] int,
  [Description] ntext(1073741823),
  [Picture] image(2147483647),
  [Street_number] nvarchar(100),
  [Street_name] nvarchar(100),
  [City] nvarchar(255),
  [Zip_code] nvarchar(100),
  [Province] nvarchar(255),
  [Country] nvarchar(255),
  PRIMARY KEY ([Site_ID]),
  CONSTRAINT [FK_site_Watershed_ID]
    FOREIGN KEY ([Watershed_ID])
      REFERENCES [watershed]([Watershed_ID])
);

CREATE TABLE [sampling_points] (
  [Sampling_point_ID] int,
  [Sampling_point] nvarchar(100),
  [Sampling_location] nvarchar(100),
  [Site_ID] int,
  [Latitude_GPS] nvarchar(100),
  [Longitude_GPS] nvarchar(100),
  [Description] ntext(1073741823),
  [Pictures] BLOB,
  PRIMARY KEY ([Sampling_point_ID]),
  CONSTRAINT [FK_sampling_points_Site_ID]
    FOREIGN KEY ([Site_ID])
      REFERENCES [site]([Site_ID])
);

CREATE TABLE [unit] (
  [Unit_ID] int,
  [Unit] nvarchar(100),
  PRIMARY KEY ([Unit_ID])
);

CREATE TABLE [parameter] (
  [Parameter_ID] int,
  [Parameter] nvarchar(100),
  [Unit_ID] int,
  [Description] ntext(1073741823),
  PRIMARY KEY ([Parameter_ID]),
  CONSTRAINT [FK_parameter_Unit_ID]
    FOREIGN KEY ([Unit_ID])
      REFERENCES [unit]([Unit_ID]),
  CONSTRAINT [FK_parameter_Parameter_ID]
    FOREIGN KEY ([Parameter_ID])
      REFERENCES [equipment_model_has_Parameter]([Parameter_ID])
);

CREATE TABLE [contact] (
  [Contact_ID] int,
  [Last_name] nvarchar(100),
  [First_name] nvarchar(255),
  [Company] ntext(1073741823),
  [Status] nvarchar(255),
  [Function] ntext(1073741823),
  [Office_number] nvarchar(100),
  [Email] nvarchar(100),
  [Phone] nvarchar(100),
  [Skype_name] nvarchar(100),
  [Linkedin] nvarchar(100),
  [Street_number] nvarchar(100),
  [Street_name] nvarchar(100),
  [City] nvarchar(255),
  [Zip_code] nvarchar(45),
  [Province/State] nvarchar(255),
  [Country] nvarchar(255),
  [Website] nvarchar(60),
  PRIMARY KEY ([Contact_ID])
);

CREATE TABLE [weather_condition] (
  [Condition_ID] int,
  [Weather_condition] nvarchar(100),
  [Description] ntext(1073741823),
  PRIMARY KEY ([Condition_ID])
);

CREATE TABLE [metadata] (
  [Metadata_ID] int,
  [Parameter_ID] int,
  [Unit_ID] int,
  [Purpose_ID] int,
  [Equipment_ID] int,
  [Procedure_ID] int,
  [Condition_ID] int,
  [Sampling_point_ID] int,
  [Contact_ID] int,
  [Project_ID] int,
  PRIMARY KEY ([Metadata_ID]),
  CONSTRAINT [FK_metadata_Sampling_point_ID]
    FOREIGN KEY ([Sampling_point_ID])
      REFERENCES [sampling_points]([Sampling_point_ID]),
  CONSTRAINT [FK_metadata_Project_ID]
    FOREIGN KEY ([Project_ID])
      REFERENCES [project]([Project_ID]),
  CONSTRAINT [FK_metadata_Unit_ID]
    FOREIGN KEY ([Unit_ID])
      REFERENCES [unit]([Unit_ID]),
  CONSTRAINT [FK_metadata_Procedure_ID]
    FOREIGN KEY ([Procedure_ID])
      REFERENCES [procedures]([Procedure_ID]),
  CONSTRAINT [FK_metadata_Parameter_ID]
    FOREIGN KEY ([Parameter_ID])
      REFERENCES [parameter]([Parameter_ID]),
  CONSTRAINT [FK_metadata_Contact_ID]
    FOREIGN KEY ([Contact_ID])
      REFERENCES [contact]([Contact_ID]),
  CONSTRAINT [FK_metadata_Equipment_ID]
    FOREIGN KEY ([Equipment_ID])
      REFERENCES [equipment]([Equipment_ID]),
  CONSTRAINT [FK_metadata_Condition_ID]
    FOREIGN KEY ([Condition_ID])
      REFERENCES [weather_condition]([Condition_ID]),
  CONSTRAINT [FK_metadata_Purpose_ID]
    FOREIGN KEY ([Purpose_ID])
      REFERENCES [purpose]([Purpose_ID])
);

CREATE TABLE [comments] (
  [Comment_ID] int,
  [Comment] ntext(1073741823),
  PRIMARY KEY ([Comment_ID])
);

CREATE TABLE [value] (
  [Value_ID] int,
  [Value] float,
  [Number_of_experiment] numeric,
  [Metadata_ID] int,
  [Comment_ID] int,
  [Timestamp] int,
  PRIMARY KEY ([Value_ID]),
  CONSTRAINT [FK_value_Metadata_ID]
    FOREIGN KEY ([Metadata_ID])
      REFERENCES [metadata]([Metadata_ID]),
  CONSTRAINT [FK_value_Comment_ID]
    FOREIGN KEY ([Comment_ID])
      REFERENCES [comments]([Comment_ID])
);

CREATE TABLE [project_has_sampling_points] (
  [Project_ID] int,
  [Sampling_point_ID] int,
  PRIMARY KEY ([Project_ID], [Sampling_point_ID]),
  CONSTRAINT [FK_project_has_sampling_points_Project_ID]
    FOREIGN KEY ([Project_ID])
      REFERENCES [project]([Project_ID]),
  CONSTRAINT [FK_project_has_sampling_points_Sampling_point_ID]
    FOREIGN KEY ([Sampling_point_ID])
      REFERENCES [sampling_points]([Sampling_point_ID])
);

CREATE TABLE [equipment_model_has_procedures] (
  [Equipment_model_ID] int,
  [Procedure_ID] int,
  PRIMARY KEY ([Equipment_model_ID], [Procedure_ID]),
  CONSTRAINT [FK_equipment_model_has_procedures_Equipment_model_ID]
    FOREIGN KEY ([Equipment_model_ID])
      REFERENCES [equipment_model]([Equipment_model_ID]),
  CONSTRAINT [FK_equipment_model_has_procedures_Procedure_ID]
    FOREIGN KEY ([Procedure_ID])
      REFERENCES [procedures]([Procedure_ID])
);

CREATE TABLE [urban_characteristics] (
  [Watershed_ID] int,
  [Commercial] real,
  [Green_spaces] real,
  [Industrial] real,
  [Institutional] real,
  [Residential] real,
  [Agricultural] real,
  [Recreational] real,
  PRIMARY KEY ([Watershed_ID])
);

CREATE TABLE [project_has_contact] (
  [Project_ID] int,
  [Contact_ID] int,
  PRIMARY KEY ([Project_ID], [Contact_ID]),
  CONSTRAINT [FK_project_has_contact_Project_ID]
    FOREIGN KEY ([Project_ID])
      REFERENCES [project]([Project_ID]),
  CONSTRAINT [FK_project_has_contact_Contact_ID]
    FOREIGN KEY ([Contact_ID])
      REFERENCES [contact]([Contact_ID])
);

CREATE TABLE [parameter_has_procedures] (
  [Parameter_ID] int,
  [Procedure_ID] int,
  PRIMARY KEY ([Parameter_ID], [Procedure_ID]),
  CONSTRAINT [FK_parameter_has_procedures_Procedure_ID]
    FOREIGN KEY ([Procedure_ID])
      REFERENCES [procedures]([Procedure_ID]),
  CONSTRAINT [FK_parameter_has_procedures_Parameter_ID]
    FOREIGN KEY ([Parameter_ID])
      REFERENCES [parameter]([Parameter_ID])
);

