SET NOCOUNT ON;
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET XACT_ABORT ON;

BEGIN TRY
BEGIN TRAN;

IF SCHEMA_ID('dbo') IS NULL
    EXEC('CREATE SCHEMA dbo');

------------------------------------------------------------
-- 1) Reference tables
------------------------------------------------------------

IF OBJECT_ID('dbo.weather_condition', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.weather_condition (
        Condition_ID       int            NOT NULL,
        Weather_condition  nvarchar(100)  NULL,
        [Description]      nvarchar(max)  NULL,
        CONSTRAINT PK_weather_condition PRIMARY KEY (Condition_ID)
    );
END;

IF OBJECT_ID('dbo.purpose', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.purpose (
        Purpose_ID    int            NOT NULL,
        Purpose       nvarchar(100)  NULL,
        [Description] nvarchar(max)  NULL,
        CONSTRAINT PK_purpose PRIMARY KEY (Purpose_ID)
    );
END;

IF OBJECT_ID('dbo.project', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.project (
        Project_ID    int            NOT NULL,
        Project_name  nvarchar(100)  NULL,
        [Description] nvarchar(max)  NULL,
        CONSTRAINT PK_project PRIMARY KEY (Project_ID)
    );
END;

IF OBJECT_ID('dbo.watershed', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.watershed (
        Watershed_ID        int            NOT NULL,
        Watershed_name      nvarchar(100)  NULL,
        [Description]       nvarchar(max)  NULL,
        Surface_area        real           NULL,
        Concentration_time  int            NULL,
        Impervious_surface  real           NULL,
        CONSTRAINT PK_watershed PRIMARY KEY (Watershed_ID)
    );
END;

IF OBJECT_ID('dbo.unit', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.unit (
        Unit_ID int           NOT NULL,
        Unit    nvarchar(100) NULL,
        CONSTRAINT PK_unit PRIMARY KEY (Unit_ID)
    );
END;

IF OBJECT_ID('dbo.procedures', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.procedures (
        Procedure_ID       int            NOT NULL,
        Procedure_name     nvarchar(100)  NULL,
        Procedure_type     nvarchar(255)  NULL,
        [Description]      nvarchar(max)  NULL,
        Procedure_location nvarchar(100)  NULL,
        CONSTRAINT PK_procedures PRIMARY KEY (Procedure_ID)
    );
END;

IF OBJECT_ID('dbo.comments', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.comments (
        Comment_ID int           NOT NULL,
        Comment    nvarchar(max) NULL,
        CONSTRAINT PK_comments PRIMARY KEY (Comment_ID)
    );
END;

------------------------------------------------------------
-- 2) Equipment
------------------------------------------------------------

IF OBJECT_ID('dbo.equipment_model', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.equipment_model (
        Equipment_model_ID int            NOT NULL,
        Equipment_model    nvarchar(100)  NULL,
        Method             nvarchar(100)  NULL,
        Functions          nvarchar(max)  NULL,
        Manufacturer       nvarchar(100)  NULL,
        Manual_location    nvarchar(100)  NULL,
        CONSTRAINT PK_equipment_model PRIMARY KEY (Equipment_model_ID)
    );
END;

IF OBJECT_ID('dbo.equipment', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.equipment (
        Equipment_ID         int            NOT NULL,
        Equipment_identifier nvarchar(100)  NULL,
        Serial_number        nvarchar(100)  NULL,
        Owner                nvarchar(max)  NULL,
        Storage_location     nvarchar(100)  NULL,
        Purchase_date        date           NULL,
        Equipment_model_ID   int            NULL,
        CONSTRAINT PK_equipment PRIMARY KEY (Equipment_ID)
    );
END;

IF OBJECT_ID('dbo.FK_equipment_Equipment_model_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.equipment
      ADD CONSTRAINT FK_equipment_Equipment_model_ID
      FOREIGN KEY (Equipment_model_ID)
      REFERENCES dbo.equipment_model (Equipment_model_ID);
END;

IF OBJECT_ID('dbo.project_has_equipment', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.project_has_equipment (
        Project_ID   int NOT NULL,
        Equipment_ID int NOT NULL,
        CONSTRAINT PK_project_has_equipment PRIMARY KEY (Project_ID, Equipment_ID)
    );
END;

IF OBJECT_ID('dbo.FK_project_has_equipment_Project_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.project_has_equipment
      ADD CONSTRAINT FK_project_has_equipment_Project_ID
      FOREIGN KEY (Project_ID) REFERENCES dbo.project(Project_ID);
END;

IF OBJECT_ID('dbo.FK_project_has_equipment_Equipment_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.project_has_equipment
      ADD CONSTRAINT FK_project_has_equipment_Equipment_ID
      FOREIGN KEY (Equipment_ID) REFERENCES dbo.equipment(Equipment_ID);
END;

------------------------------------------------------------
-- 3) Contacts + projects
------------------------------------------------------------

IF OBJECT_ID('dbo.contact', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.contact (
        Contact_ID       int            NOT NULL,
        Last_name        nvarchar(100)  NULL,
        First_name       nvarchar(255)  NULL,
        Company          nvarchar(max)  NULL,
        Status           nvarchar(255)  NULL,
        [Function]       nvarchar(max)  NULL,
        Office_number    nvarchar(100)  NULL,
        Email            nvarchar(100)  NULL,
        Phone            nvarchar(100)  NULL,
        Skype_name       nvarchar(100)  NULL,
        Linkedin         nvarchar(100)  NULL,
        Street_number    nvarchar(100)  NULL,
        Street_name      nvarchar(100)  NULL,
        City             nvarchar(255)  NULL,
        Zip_code         nvarchar(45)   NULL,
        [Province/State] nvarchar(255)  NULL,
        Country          nvarchar(255)  NULL,
        Website          nvarchar(60)   NULL,
        CONSTRAINT PK_contact PRIMARY KEY (Contact_ID)
    );
END;

IF OBJECT_ID('dbo.project_has_contact', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.project_has_contact (
        Project_ID int NOT NULL,
        Contact_ID int NOT NULL,
        CONSTRAINT PK_project_has_contact PRIMARY KEY (Project_ID, Contact_ID)
    );
END;

IF OBJECT_ID('dbo.FK_project_has_contact_Project_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.project_has_contact
      ADD CONSTRAINT FK_project_has_contact_Project_ID
      FOREIGN KEY (Project_ID) REFERENCES dbo.project(Project_ID);
END;

IF OBJECT_ID('dbo.FK_project_has_contact_Contact_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.project_has_contact
      ADD CONSTRAINT FK_project_has_contact_Contact_ID
      FOREIGN KEY (Contact_ID) REFERENCES dbo.contact(Contact_ID);
END;

------------------------------------------------------------
-- 4) Watershed characteristics (WITH FK to watershed)
------------------------------------------------------------

IF OBJECT_ID('dbo.hydrological_characteristics', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.hydrological_characteristics (
        Watershed_ID int  NOT NULL,
        Urban_area   real NULL,
        Forest       real NULL,
        Wetlands     real NULL,
        Cropland     real NULL,
        Meadow       real NULL,
        Grassland    real NULL,
        CONSTRAINT PK_hydrological_characteristics PRIMARY KEY (Watershed_ID)
    );
END;

IF OBJECT_ID('dbo.urban_characteristics', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.urban_characteristics (
        Watershed_ID   int  NOT NULL,
        Commercial     real NULL,
        Green_spaces   real NULL,
        Industrial     real NULL,
        Institutional  real NULL,
        Residential    real NULL,
        Agricultural   real NULL,
        Recreational   real NULL,
        CONSTRAINT PK_urban_characteristics PRIMARY KEY (Watershed_ID)
    );
END;

IF OBJECT_ID('dbo.FK_hydrological_characteristics_Watershed_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.hydrological_characteristics
      ADD CONSTRAINT FK_hydrological_characteristics_Watershed_ID
      FOREIGN KEY (Watershed_ID) REFERENCES dbo.watershed(Watershed_ID);
END;

IF OBJECT_ID('dbo.FK_urban_characteristics_Watershed_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.urban_characteristics
      ADD CONSTRAINT FK_urban_characteristics_Watershed_ID
      FOREIGN KEY (Watershed_ID) REFERENCES dbo.watershed(Watershed_ID);
END;

------------------------------------------------------------
-- 5) Sites + sampling points
------------------------------------------------------------

IF OBJECT_ID('dbo.site', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.site (
        Site_ID        int            NOT NULL,
        Site_name      nvarchar(100)  NULL,
        Site_type      nvarchar(255)  NULL,
        Watershed_ID   int            NULL,
        [Description]  nvarchar(max)  NULL,
        Picture        varbinary(max) NULL,
        Street_number  nvarchar(100)  NULL,
        Street_name    nvarchar(100)  NULL,
        City           nvarchar(255)  NULL,
        Zip_code       nvarchar(100)  NULL,
        Province       nvarchar(255)  NULL,
        Country        nvarchar(255)  NULL,
        CONSTRAINT PK_site PRIMARY KEY (Site_ID)
    );
END;

IF OBJECT_ID('dbo.FK_site_Watershed_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.site
      ADD CONSTRAINT FK_site_Watershed_ID
      FOREIGN KEY (Watershed_ID) REFERENCES dbo.watershed(Watershed_ID);
END;

IF OBJECT_ID('dbo.sampling_points', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.sampling_points (
        Sampling_point_ID int            NOT NULL,
        Sampling_point    nvarchar(100)  NULL,
        Sampling_location nvarchar(100)  NULL,
        Site_ID           int            NULL,
        Latitude_GPS      nvarchar(100)  NULL,
        Longitude_GPS     nvarchar(100)  NULL,
        [Description]     nvarchar(max)  NULL,
        Pictures          varbinary(max) NULL,
        CONSTRAINT PK_sampling_points PRIMARY KEY (Sampling_point_ID)
    );
END;

IF OBJECT_ID('dbo.FK_sampling_points_Site_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.sampling_points
      ADD CONSTRAINT FK_sampling_points_Site_ID
      FOREIGN KEY (Site_ID) REFERENCES dbo.site(Site_ID);
END;

IF OBJECT_ID('dbo.project_has_sampling_points', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.project_has_sampling_points (
        Project_ID        int NOT NULL,
        Sampling_point_ID int NOT NULL,
        CONSTRAINT PK_project_has_sampling_points PRIMARY KEY (Project_ID, Sampling_point_ID)
    );
END;

IF OBJECT_ID('dbo.FK_project_has_sampling_points_Project_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.project_has_sampling_points
      ADD CONSTRAINT FK_project_has_sampling_points_Project_ID
      FOREIGN KEY (Project_ID) REFERENCES dbo.project(Project_ID);
END;

IF OBJECT_ID('dbo.FK_project_has_sampling_points_Sampling_point_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.project_has_sampling_points
      ADD CONSTRAINT FK_project_has_sampling_points_Sampling_point_ID
      FOREIGN KEY (Sampling_point_ID) REFERENCES dbo.sampling_points(Sampling_point_ID);
END;

------------------------------------------------------------
-- 6) Parameter (MUST exist before equipment_model_has_Parameter)
------------------------------------------------------------

IF OBJECT_ID('dbo.parameter', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.parameter (
        Parameter_ID  int            NOT NULL,
        Parameter     nvarchar(100)  NULL,
        Unit_ID       int            NULL,
        [Description] nvarchar(max)  NULL,
        CONSTRAINT PK_parameter PRIMARY KEY (Parameter_ID)
    );
END;

IF OBJECT_ID('dbo.FK_parameter_Unit_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.parameter
      ADD CONSTRAINT FK_parameter_Unit_ID
      FOREIGN KEY (Unit_ID) REFERENCES dbo.unit(Unit_ID);
END;

------------------------------------------------------------
-- 7) Procedure relations
------------------------------------------------------------

IF OBJECT_ID('dbo.parameter_has_procedures', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.parameter_has_procedures (
        Parameter_ID int NOT NULL,
        Procedure_ID int NOT NULL,
        CONSTRAINT PK_parameter_has_procedures PRIMARY KEY (Parameter_ID, Procedure_ID)
    );
END;

IF OBJECT_ID('dbo.FK_parameter_has_procedures_Parameter_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.parameter_has_procedures
      ADD CONSTRAINT FK_parameter_has_procedures_Parameter_ID
      FOREIGN KEY (Parameter_ID) REFERENCES dbo.parameter(Parameter_ID);
END;

IF OBJECT_ID('dbo.FK_parameter_has_procedures_Procedure_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.parameter_has_procedures
      ADD CONSTRAINT FK_parameter_has_procedures_Procedure_ID
      FOREIGN KEY (Procedure_ID) REFERENCES dbo.procedures(Procedure_ID);
END;

IF OBJECT_ID('dbo.equipment_model_has_procedures', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.equipment_model_has_procedures (
        Equipment_model_ID int NOT NULL,
        Procedure_ID       int NOT NULL,
        CONSTRAINT PK_equipment_model_has_procedures PRIMARY KEY (Equipment_model_ID, Procedure_ID)
    );
END;

IF OBJECT_ID('dbo.FK_equipment_model_has_procedures_Equipment_model_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.equipment_model_has_procedures
      ADD CONSTRAINT FK_equipment_model_has_procedures_Equipment_model_ID
      FOREIGN KEY (Equipment_model_ID) REFERENCES dbo.equipment_model(Equipment_model_ID);
END;

IF OBJECT_ID('dbo.FK_equipment_model_has_procedures_Procedure_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.equipment_model_has_procedures
      ADD CONSTRAINT FK_equipment_model_has_procedures_Procedure_ID
      FOREIGN KEY (Procedure_ID) REFERENCES dbo.procedures(Procedure_ID);
END;

IF OBJECT_ID('dbo.equipment_model_has_Parameter', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.equipment_model_has_Parameter (
        Equipment_model_ID int NOT NULL,
        Parameter_ID       int NOT NULL,
        CONSTRAINT PK_equipment_model_has_Parameter PRIMARY KEY (Equipment_model_ID, Parameter_ID)
    );
END;

IF OBJECT_ID('dbo.FK_equipment_model_has_Parameter_Equipment_model_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.equipment_model_has_Parameter
      ADD CONSTRAINT FK_equipment_model_has_Parameter_Equipment_model_ID
      FOREIGN KEY (Equipment_model_ID) REFERENCES dbo.equipment_model(Equipment_model_ID);
END;

IF OBJECT_ID('dbo.FK_equipment_model_has_Parameter_Parameter_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.equipment_model_has_Parameter
      ADD CONSTRAINT FK_equipment_model_has_Parameter_Parameter_ID
      FOREIGN KEY (Parameter_ID) REFERENCES dbo.parameter(Parameter_ID);
END;

------------------------------------------------------------
-- 8) Metadata
------------------------------------------------------------

IF OBJECT_ID('dbo.metadata', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.metadata (
        Metadata_ID       int NOT NULL,
        Parameter_ID      int NULL,
        Unit_ID           int NULL,
        Purpose_ID        int NULL,
        Equipment_ID      int NULL,
        Procedure_ID      int NULL,
        Condition_ID      int NULL,
        Sampling_point_ID int NULL,
        Contact_ID        int NULL,
        Project_ID        int NULL,
        StartDate         int NULL,  -- Unix time
        EndDate           int NULL,  -- Unix time
        CONSTRAINT PK_metadata PRIMARY KEY (Metadata_ID)
    );
END;

IF OBJECT_ID('dbo.FK_metadata_Condition_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.metadata
      ADD CONSTRAINT FK_metadata_Condition_ID
      FOREIGN KEY (Condition_ID) REFERENCES dbo.weather_condition(Condition_ID);
END;

IF OBJECT_ID('dbo.FK_metadata_Procedure_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.metadata
      ADD CONSTRAINT FK_metadata_Procedure_ID
      FOREIGN KEY (Procedure_ID) REFERENCES dbo.procedures(Procedure_ID);
END;

IF OBJECT_ID('dbo.FK_metadata_Unit_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.metadata
      ADD CONSTRAINT FK_metadata_Unit_ID
      FOREIGN KEY (Unit_ID) REFERENCES dbo.unit(Unit_ID);
END;

IF OBJECT_ID('dbo.FK_metadata_Parameter_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.metadata
      ADD CONSTRAINT FK_metadata_Parameter_ID
      FOREIGN KEY (Parameter_ID) REFERENCES dbo.parameter(Parameter_ID);
END;

IF OBJECT_ID('dbo.FK_metadata_Sampling_point_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.metadata
      ADD CONSTRAINT FK_metadata_Sampling_point_ID
      FOREIGN KEY (Sampling_point_ID) REFERENCES dbo.sampling_points(Sampling_point_ID);
END;

IF OBJECT_ID('dbo.FK_metadata_Contact_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.metadata
      ADD CONSTRAINT FK_metadata_Contact_ID
      FOREIGN KEY (Contact_ID) REFERENCES dbo.contact(Contact_ID);
END;

IF OBJECT_ID('dbo.FK_metadata_Purpose_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.metadata
      ADD CONSTRAINT FK_metadata_Purpose_ID
      FOREIGN KEY (Purpose_ID) REFERENCES dbo.purpose(Purpose_ID);
END;

IF OBJECT_ID('dbo.FK_metadata_Project_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.metadata
      ADD CONSTRAINT FK_metadata_Project_ID
      FOREIGN KEY (Project_ID) REFERENCES dbo.project(Project_ID);
END;

IF OBJECT_ID('dbo.FK_metadata_Equipment_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.metadata
      ADD CONSTRAINT FK_metadata_Equipment_ID
      FOREIGN KEY (Equipment_ID) REFERENCES dbo.equipment(Equipment_ID);
END;

------------------------------------------------------------
-- 9) Value table (time series)
------------------------------------------------------------

IF OBJECT_ID('dbo.[value]', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.[value] (
        Value_ID             int IDENTITY(1,1) NOT NULL,
        Value                float             NULL,
        Number_of_experiment numeric           NULL,
        Metadata_ID          int               NULL,
        Comment_ID           int               NULL,
        Timestamp            int               NULL, -- Unix time
        CONSTRAINT PK_value PRIMARY KEY (Value_ID)
    );
END;

IF OBJECT_ID('dbo.FK_value_Metadata_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.[value]
      ADD CONSTRAINT FK_value_Metadata_ID
      FOREIGN KEY (Metadata_ID) REFERENCES dbo.metadata(Metadata_ID);
END;

IF OBJECT_ID('dbo.FK_value_Comment_ID', 'F') IS NULL
BEGIN
    ALTER TABLE dbo.[value]
      ADD CONSTRAINT FK_value_Comment_ID
      FOREIGN KEY (Comment_ID) REFERENCES dbo.comments(Comment_ID);
END;

-- Unique anti-duplicates: one value per (Metadata_ID, Timestamp)
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'UX_value_MetadataID_Timestamp'
      AND object_id = OBJECT_ID('dbo.[value]')
)
BEGIN
    CREATE UNIQUE INDEX UX_value_MetadataID_Timestamp
    ON dbo.[value] (Metadata_ID, Timestamp)
    WHERE Metadata_ID IS NOT NULL AND Timestamp IS NOT NULL;
END;

COMMIT TRAN;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRAN;

    DECLARE @msg nvarchar(4000) = ERROR_MESSAGE();
    DECLARE @line int = ERROR_LINE();
    DECLARE @num int = ERROR_NUMBER();
    RAISERROR('Schema init failed (error %d at line %d): %s', 16, 1, @num, @line, @msg);
END CATCH;
