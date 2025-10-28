CREATE TABLE [equipment_model] (
  [Equipment_model_ID] int,
  [Equipment_model] nvarchar(100),
  [Method] nvarchar(100),
  [Functions] ntext(1073741823),
  [Manufacturer] nvarchar(100),
  [Manual_location] nvarchar(100),
  [Equipment_type] nvarchar(100),
  [Product_number] nvarchar(100),
  [SOP_number] int,
  [SOP_URL] nvarchar(255),
  [Contact_ID] int,
  [Resources_URL] varchar(300),
  [Notes] nvarchar(150),
  PRIMARY KEY ([Equipment_model_ID])
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
      REFERENCES [unit]([Unit_ID])
);

CREATE TABLE [equipment_model_has_specification (renamed from Equipment_model_has_Parameter)] (
  [Equipment_model_ID] int,
  [Parameter_ID] int,
  [Range_min] float,
  [Range_max] float,
  [Resolution] nvarchar(100),
  [Unit_ID] int,
  PRIMARY KEY ([Equipment_model_ID], [Parameter_ID]),
  CONSTRAINT [FK_equipment_model_has_specification (renamed from Equipment_model_has_Parameter)_Equipment_model_ID]
    FOREIGN KEY ([Equipment_model_ID])
      REFERENCES [equipment_model]([Equipment_model_ID]),
  CONSTRAINT [FK_equipment_model_has_specification (renamed from Equipment_model_has_Parameter)_Parameter_ID]
    FOREIGN KEY ([Parameter_ID])
      REFERENCES [parameter]([Parameter_ID])
);

CREATE TABLE [comments] (
  [Comment_ID] int,
  [Comment] ntext(1073741823),
  PRIMARY KEY ([Comment_ID])
);

CREATE TABLE [weather_condition] (
  [Condition_ID] int,
  [Weather_condition] nvarchar(100),
  [Description] ntext(1073741823),
  PRIMARY KEY ([Condition_ID]),
  CONSTRAINT [FK_weather_condition_Description]
    FOREIGN KEY ([Description])
      REFERENCES [comments]([Comment_ID])
);

CREATE TABLE [source] (
  [Source_ID] int,
  [Signal_Transmission] nvarchar(25),
  [Signal_Transmission_Address] nvarchar(50),
  [Source_Location] nvarchar(100),
  [Source_Software] nvarchar(50),
  [Raw_Database_Path] nvarchar(100),
  [TAG_Name] nvarchar(50),
  [TAG_Number] int,
  [Sampling_Time] nvarchar(10),
  [Import_Location] nvarchar(100),
  [Importing_Software] nvarchar(50),
  [Import_Script] nvarchar(50),
  PRIMARY KEY ([Source_ID])
);

CREATE TABLE [operations] (
  [Operations_ID] int,
  [NOR_min] float,
  [NOR_max] float,
  [Alarm_low] float,
  [Alarm_high] float,
  PRIMARY KEY ([Operations_ID])
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

CREATE TABLE [equipment] (
  [Equipment_ID] int,
  [Equipment_identifier] nvarchar(100),
  [Serial_number] nvarchar(100),
  [Owner] ntext(1073741823),
  [Storage_location] nvarchar(100),
  [Purchase_date] date,
  [Equipment_model_ID] int,
  [Status] nvarchar(10),
  [Notes] nvarchar(300),
  [Commissioning_date] date,
  PRIMARY KEY ([Equipment_ID]),
  CONSTRAINT [FK_equipment_Equipment_model_ID]
    FOREIGN KEY ([Equipment_model_ID])
      REFERENCES [equipment_model]([Equipment_model_ID])
);

CREATE TABLE [metadata] (
  [Metadata_ID] int,
  [Parameter_ID] int,
  [Purpose_ID] int,
  [Equipment_ID] int,
  [Sampling_point_ID] int,
  [Contact_ID] int,
  [Project_ID] int,
  [Type_ID] int,
  [Status_ID] int,
  [Operations_ID] int,
  [Source_ID] int,
  PRIMARY KEY ([Metadata_ID]),
  CONSTRAINT [FK_metadata_Parameter_ID]
    FOREIGN KEY ([Parameter_ID])
      REFERENCES [parameter]([Parameter_ID]),
  CONSTRAINT [FK_metadata_Source_ID]
    FOREIGN KEY ([Source_ID])
      REFERENCES [source]([Source_ID]),
  CONSTRAINT [FK_metadata_Operations_ID]
    FOREIGN KEY ([Operations_ID])
      REFERENCES [operations]([Operations_ID]),
  CONSTRAINT [FK_metadata_Contact_ID]
    FOREIGN KEY ([Contact_ID])
      REFERENCES [contact]([Contact_ID]),
  CONSTRAINT [FK_metadata_Equipment_ID]
    FOREIGN KEY ([Equipment_ID])
      REFERENCES [equipment]([Equipment_ID])
);

CREATE TABLE [value_before_12_04_2025] (
  [Value_ID] int,
  [Value] float,
  [Number_of_experiment] numeric,
  [Metadata_ID] int,
  [Comment_ID] int,
  [Timestamp] int,
  PRIMARY KEY ([Value_ID]),
  CONSTRAINT [FK_value_before_12_04_2025_Metadata_ID]
    FOREIGN KEY ([Metadata_ID])
      REFERENCES [metadata]([Metadata_ID]),
  CONSTRAINT [FK_value_before_12_04_2025_Comment_ID]
    FOREIGN KEY ([Comment_ID])
      REFERENCES [comments]([Comment_ID])
);

CREATE TABLE [watershed] (
  [Watershed_ID] int,
  [Watershed_name] nvarchar(100),
  [Description] ntext(1073741823),
  [Surface_area] real,
  [Concentration_time] int,
  [Impervious_surface] real,
  [Geo_Boundary] nvarchar(1000),
  PRIMARY KEY ([Watershed_ID])
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
  PRIMARY KEY ([Watershed_ID]),
  CONSTRAINT [FK_urban_characteristics_Watershed_ID]
    FOREIGN KEY ([Watershed_ID])
      REFERENCES [watershed]([Watershed_ID])
);

CREATE TABLE [project_has_sampling_points] (
  [Project_ID] int,
  [Sampling_point_ID] int,
  PRIMARY KEY ([Project_ID], [Sampling_point_ID])
);

CREATE TABLE [type_data] (
  [Type_ID] int,
  [Type] nvarchar(20),
  [Description] ntext(1073741823),
  PRIMARY KEY ([Type_ID])
);

CREATE TABLE [maxTimestamp] (
  [MaxTimestamp_ID] int,
  [Timestamp] int,
  [Hits1000] int,
  PRIMARY KEY ([MaxTimestamp_ID]),
  CONSTRAINT [FK_maxTimestamp_Hits1000]
    FOREIGN KEY ([Hits1000])
      REFERENCES [type_data]([Type_ID])
);

CREATE TABLE [sampling_points] (
  [Sampling_point_ID] int,
  [Sampling_point] nvarchar(100),
  [Sampling_location] nvarchar(100),
  [Site_ID] int,
  [Latitude_GPS] nvarchar(100),
  [Longitude_GPS] nvarchar(100),
  [Description] ntext(1073741823),
  [Pictures_URL] nvarchar(500),
  PRIMARY KEY ([Sampling_point_ID])
);

CREATE TABLE [equipment_has_sampling_points] (
  [Equipment_ID] int,
  [Sampling_point_ID] int,
  PRIMARY KEY ([Equipment_ID], [Sampling_point_ID]),
  CONSTRAINT [FK_equipment_has_sampling_points_Sampling_point_ID]
    FOREIGN KEY ([Sampling_point_ID])
      REFERENCES [sampling_points]([Sampling_point_ID]),
  CONSTRAINT [FK_equipment_has_sampling_points_Equipment_ID]
    FOREIGN KEY ([Equipment_ID])
      REFERENCES [equipment]([Equipment_ID])
);

CREATE TABLE [project] (
  [Project_ID] int,
  [Project_name] nvarchar(100),
  [Description] ntext(1073741823),
  PRIMARY KEY ([Project_ID])
);

CREATE TABLE [project_has_contact] (
  [Project_ID] int,
  [Contact_ID] int,
  PRIMARY KEY ([Project_ID], [Contact_ID]),
  CONSTRAINT [FK_project_has_contact_Contact_ID]
    FOREIGN KEY ([Contact_ID])
      REFERENCES [contact]([Contact_ID]),
  CONSTRAINT [FK_project_has_contact_Project_ID]
    FOREIGN KEY ([Project_ID])
      REFERENCES [project]([Project_ID])
);

CREATE TABLE [procedures] (
  [Procedure_ID] int,
  [Procedure_name] nvarchar(100),
  [Procedure_type] nvarchar(255),
  [Description] ntext(1073741823),
  [Procedure_location] nvarchar(100),
  PRIMARY KEY ([Procedure_ID])
);

CREATE TABLE [purpose] (
  [Purpose_ID] int,
  [Purpose] nvarchar(100),
  [Description] ntext(1073741823),
  [Code] nvarchar(10),
  PRIMARY KEY ([Purpose_ID])
);

CREATE TABLE [holdkey] (
  [Metadata_ID] int,
  [Timestamp] int,
  [col3] int,
  CONSTRAINT [FK_holdkey_col3]
    FOREIGN KEY ([col3])
      REFERENCES [purpose]([Purpose_ID])
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
      REFERENCES [metadata]([Metadata_ID])
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

CREATE TABLE [control_loop] (
  [Measurement] int,
  [Controller] int,
  [Actuator] int,
  [Notes] nvarchar(200),
  CONSTRAINT [FK_control_loop_Actuator]
    FOREIGN KEY ([Actuator])
      REFERENCES [metadata]([Metadata_ID]),
  CONSTRAINT [FK_control_loop_Controller]
    FOREIGN KEY ([Controller])
      REFERENCES [metadata]([Metadata_ID]),
  CONSTRAINT [FK_control_loop_Measurement]
    FOREIGN KEY ([Measurement])
      REFERENCES [metadata]([Metadata_ID])
);

CREATE TABLE [hydrological_characteristics] (
  [Watershed_ID] int,
  [Urban_area] real,
  [Forest] real,
  [Wetlands] real,
  [Cropland] real,
  [Meadow] real,
  [Grassland] real,
  PRIMARY KEY ([Watershed_ID]),
  CONSTRAINT [FK_hydrological_characteristics_Watershed_ID]
    FOREIGN KEY ([Watershed_ID])
      REFERENCES [watershed]([Watershed_ID])
);

CREATE TABLE [value_test_hedi] (
  [Value_ID] int,
  [Value] float,
  [Number_of_experiment] numeric,
  [Metadata_ID] int,
  [Comment_ID] int,
  [Timestamp] int,
  PRIMARY KEY ([Value_ID]),
  CONSTRAINT [FK_value_test_hedi_Comment_ID]
    FOREIGN KEY ([Comment_ID])
      REFERENCES [comments]([Comment_ID]),
  CONSTRAINT [FK_value_test_hedi_Metadata_ID]
    FOREIGN KEY ([Metadata_ID])
      REFERENCES [metadata]([Metadata_ID])
);

CREATE TABLE [sysdiagrams] (
  [name] nvarchar(128),
  [principal_id] int,
  [diagram_id] int,
  [version] int,
  [definition] varbinary,
  PRIMARY KEY ([diagram_id])
);

CREATE INDEX [AK] ON  [sysdiagrams] ([name], [principal_id]);

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

CREATE TABLE [project_has_equipment] (
  [Project_ID] int,
  [Equipment_ID] int,
  PRIMARY KEY ([Project_ID], [Equipment_ID]),
  CONSTRAINT [FK_project_has_equipment_Project_ID]
    FOREIGN KEY ([Project_ID])
      REFERENCES [project]([Project_ID]),
  CONSTRAINT [FK_project_has_equipment_Equipment_ID]
    FOREIGN KEY ([Equipment_ID])
      REFERENCES [equipment]([Equipment_ID])
);

CREATE TABLE [status] (
  [Status_ID] int,
  [Status] nvarchar(50),
  PRIMARY KEY ([Status_ID])
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

