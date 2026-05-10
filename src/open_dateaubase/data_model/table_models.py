"""
Pydantic models representing the data rows for database tables and views.
These models are generated based on the YAML schema definitions and are used
for API request/response validation and data manipulation.
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class QualityCodeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    qualitycodeID: int = Field(
        alias="QualityCode_ID", description="Surrogate primary key, manually assigned"
    )
    name: str = Field(
        alias="Name",
        description="Short code name (e.g. 'Accepted', 'BelowLoD')",
        max_length=50,
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Explanation of what this quality code means",
        max_length=200,
    )
    isusable: bool = Field(
        alias="IsUsable",
        description="Whether a value carrying this code should be included in analysis. true = value is fit for use; false = value must be excluded or treated specially.\n",
        default=True,
    )


class QualityCodeCreate(QualityCodeBase):
    pass


class QualityCode(QualityCodeBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DASLocationHistoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    dataacquisitionsystemID: int = Field(
        alias="DataAcquisitionSystem_ID",
        description="The DAS whose site deployment is recorded here",
    )
    siteID: int = Field(
        alias="Site_ID",
        description="The site where this DAS is deployed during this period",
    )
    validfrom: datetime = Field(
        alias="ValidFrom",
        description="UTC datetime when the DAS was deployed at this site",
    )
    validto: Optional[datetime] = Field(
        alias="ValidTo",
        default=None,
        description="UTC datetime when the DAS left this site. NULL = currently deployed.",
    )
    campaignID: Optional[int] = Field(
        alias="Campaign_ID",
        default=None,
        description="Campaign during which this deployment started (if applicable)",
    )
    notes: Optional[str] = Field(
        alias="Notes",
        default=None,
        description="Free-text notes about the deployment or move",
    )


class DASLocationHistoryCreate(DASLocationHistoryBase):
    pass


class DASLocationHistory(DASLocationHistoryBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    daslocationhistoryID: int = Field(
        alias="DASLocationHistory_ID", description="Surrogate primary key"
    )


class EquipmentLocationHistoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmentID: int = Field(
        alias="Equipment_ID",
        description="The equipment whose physical location is recorded here",
    )
    samplingpointID: int = Field(
        alias="SamplingPoint_ID",
        description="The SamplingPoint where this equipment is deployed during this period",
    )
    validfrom: datetime = Field(
        alias="ValidFrom",
        description="UTC datetime when the equipment started measuring at this SamplingPoint",
    )
    validto: Optional[datetime] = Field(
        alias="ValidTo",
        description="UTC datetime when the equipment stopped measuring here. NULL = currently active.",
    )
    campaignID: Optional[int] = Field(
        alias="Campaign_ID",
        description="Campaign during which this deployment occurred (if applicable)",
    )
    notes: Optional[str] = Field(
        alias="Notes", description="Free-text notes (e.g. reason for relocation)"
    )


class EquipmentLocationHistoryCreate(EquipmentLocationHistoryBase):
    pass


class EquipmentLocationHistory(EquipmentLocationHistoryBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmentlocationhistoryID: int = Field(
        alias="EquipmentLocationHistory_ID", description="Surrogate primary key"
    )


class ObservationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    channelID: int = Field(
        alias="Channel_ID", description="The channel this observation belongs to"
    )
    timestamp: datetime = Field(
        alias="Timestamp", description="UTC timestamp of the observation"
    )
    valuekindID: int = Field(
        alias="ValueKind_ID",
        description="Payload kind FK (1=Scalar, 2=Vector, 3=Matrix, 4=Image). Must match the Channel's ValueKind.",
    )


class ObservationCreate(ObservationBase):
    pass


class Observation(ObservationBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    observationID: int = Field(
        alias="Observation_ID",
        description="Surrogate key; auto-assigned by the database",
    )


class SampleMethodBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    samplemethodID: int = Field(
        alias="SampleMethod_ID", description="Surrogate primary key, manually assigned"
    )
    name: str = Field(
        alias="Name",
        description="Collection method name (e.g. 'Grab', 'Composite24h')",
        max_length=50,
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Explanation of the collection method",
        max_length=200,
    )


class SampleMethodCreate(SampleMethodBase):
    pass


class SampleMethod(SampleMethodBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HydrologicalCharacteristicsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    urbanarea: Optional[Any] = Field(
        alias="UrbanArea", description="Percentage [%] of urban areas"
    )
    forest: Optional[Any] = Field(
        alias="Forest", description="Percentage [%] of forest areas"
    )
    wetlands: Optional[Any] = Field(
        alias="Wetlands", description="Percentage [%] of wetlands"
    )
    cropland: Optional[Any] = Field(
        alias="Cropland", description="Percentage [%] of croplands"
    )
    meadow: Optional[Any] = Field(
        alias="Meadow", description="Percentage [%] of meadow areas"
    )
    grassland: Optional[Any] = Field(
        alias="Grassland", description="Percentage [%] of grasslands"
    )


class HydrologicalCharacteristicsCreate(HydrologicalCharacteristicsBase):
    pass


class HydrologicalCharacteristics(HydrologicalCharacteristicsBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    watershedID: int = Field(
        alias="Watershed_ID", description="Linked to the Watershed table"
    )


class ValueBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    observationID: int = Field(
        alias="Observation_ID",
        description="Links this scalar value to its Observation (channel + timestamp)",
    )
    value: Optional[Any] = Field(alias="Value", description="Measured scalar value")


class ValueCreate(ValueBase):
    pass


class Value(ValueBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SignalInterfaceTypeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    signalinterfacetypeID: int = Field(
        alias="SignalInterfaceType_ID",
        description="Surrogate primary key, manually assigned",
    )
    name: str = Field(
        alias="Name", description="Short name for this interface type", max_length=50
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Explanation of what this interface type means",
        max_length=300,
    )


class SignalInterfaceTypeCreate(SignalInterfaceTypeBase):
    pass


class SignalInterfaceType(SignalInterfaceTypeBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SignalInterfacePortKindBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    signalinterfaceportkindID: int = Field(
        alias="SignalInterfacePortKind_ID",
        description="Surrogate primary key, manually assigned",
    )
    name: str = Field(
        alias="Name", description="Short name for this port kind", max_length=50
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Explanation of what this port kind means",
        max_length=200,
    )


class SignalInterfacePortKindCreate(SignalInterfacePortKindBase):
    pass


class SignalInterfacePortKind(SignalInterfacePortKindBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ChannelRoleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    channelroleID: int = Field(
        alias="ChannelRole_ID", description="Surrogate primary key, manually assigned"
    )
    name: str = Field(
        alias="Name",
        description="Role name (e.g. 'Value', 'Status', 'Alarm', 'Uncertainty')",
        max_length=50,
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Explanation of what this channel role represents",
        max_length=200,
    )


class ChannelRoleCreate(ChannelRoleBase):
    pass


class ChannelRole(ChannelRoleBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ValueImageBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    observationID: int = Field(
        alias="Observation_ID",
        description="Links this image to its Observation (channel + timestamp). Acts as both PK and FK — one image per observation.\n",
    )
    imagewidth: int = Field(
        alias="ImageWidth", description="Width of the image in pixels"
    )
    imageheight: int = Field(
        alias="ImageHeight", description="Height of the image in pixels"
    )
    numberofchannels: int = Field(
        alias="NumberOfChannels",
        description="Number of color channels (e.g. 3 for RGB, 1 for grayscale)",
        default=3,
    )
    imageformat: str = Field(
        alias="ImageFormat",
        description="Image file format (e.g. PNG, TIFF, JPEG)",
        max_length=20,
    )
    filesizebytes: Optional[Any] = Field(
        alias="FileSizeBytes", description="File size in bytes"
    )
    storagebackend: str = Field(
        alias="StorageBackend",
        description="Storage backend type (e.g. FileSystem, S3, Azure Blob)",
        max_length=50,
        default="'FileSystem'",
    )
    storagepath: str = Field(
        alias="StoragePath",
        description="Full path or URI to the stored image file",
        max_length=1000,
    )
    thumbnail: Optional[Any] = Field(
        alias="Thumbnail",
        description="Optional thumbnail image stored inline as binary",
    )
    qualitycode: Optional[int] = Field(
        alias="QualityCode", description="Quality flag for this image"
    )


class ValueImageCreate(ValueImageBase):
    pass


class ValueImage(ValueImageBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SchemaVersionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    version: str = Field(
        alias="Version", description="Schema version string (e.g. 1.0.1)", max_length=20
    )
    applieddatetime: datetime = Field(
        alias="AppliedDateTime",
        description="UTC datetime when this migration was applied (stored in UTC by convention)",
        default="CURRENT_TIMESTAMP",
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Human-readable description of what this migration does",
        max_length=500,
    )
    migrationscript: Optional[str] = Field(
        alias="MigrationScript",
        description="Filename of the migration script that was applied",
        max_length=200,
    )


class SchemaVersionCreate(SchemaVersionBase):
    pass


class SchemaVersion(SchemaVersionBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    versionid: int = Field(alias="VersionID", description="Surrogate primary key")


class CampaignBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    campaigntypeID: int = Field(
        alias="CampaignType_ID",
        description="Type of campaign (Experiment, Operations, Commissioning)",
    )
    siteID: int = Field(
        alias="Site_ID", description="Site where the campaign is conducted"
    )
    name: str = Field(
        alias="Name", description="Human-readable name for the campaign", max_length=200
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Detailed description of the campaign objectives and scope",
        max_length=2000,
    )
    campaignstartdatetime: Optional[datetime] = Field(
        alias="CampaignStartDateTime",
        description="Date and time the campaign began (UTC)",
    )
    campaignenddatetime: Optional[datetime] = Field(
        alias="CampaignEndDateTime",
        description="Date and time the campaign ended (UTC); NULL if ongoing",
    )
    responsiblepersonID: Optional[int] = Field(
        alias="ResponsiblePerson_ID",
        description="Person responsible for running the campaign",
    )


class CampaignCreate(CampaignBase):
    pass


class Campaign(CampaignBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    campaignID: int = Field(alias="Campaign_ID", description="Surrogate primary key")


class AnnotationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    channelID: int = Field(
        alias="Channel_ID", description="The time series this annotation applies to"
    )
    annotationtypeID: int = Field(
        alias="AnnotationType_ID", description="What kind of annotation this is"
    )
    starttime: datetime = Field(
        alias="StartTime", description="Start of the annotated time range"
    )
    endtime: Optional[datetime] = Field(
        alias="EndTime",
        description="End of the annotated range. NULL = point annotation or ongoing",
    )
    authorpersonID: Optional[int] = Field(
        alias="AuthorPerson_ID", description="Person who created this annotation"
    )
    campaignID: Optional[int] = Field(
        alias="Campaign_ID",
        description="Campaign this annotation is associated with, if any",
    )
    equipmenteventID: Optional[int] = Field(
        alias="EquipmentEvent_ID",
        description="Equipment event that caused this annotation, if any",
    )
    title: Optional[str] = Field(
        alias="Title", description="Short title for the annotation", max_length=200
    )
    comment: Optional[str] = Field(
        alias="Comment", description="Detailed free-text comment", max_length=None
    )
    createddatetime: datetime = Field(
        alias="CreatedDateTime",
        description="When this annotation was created",
        default="CURRENT_TIMESTAMP",
    )
    modifieddatetime: Optional[datetime] = Field(
        alias="ModifiedDateTime", description="When this annotation was last modified"
    )
    observationID: Optional[int] = Field(
        alias="Observation_ID",
        description="Optional link to a specific Observation for point-level annotations (e.g., 'wrong focal length on this image'). When NULL, the annotation applies to the time range [StartTime, EndTime] on the channel. When set, StartTime should match Observation.Timestamp.\n",
    )


class AnnotationCreate(AnnotationBase):
    pass


class Annotation(AnnotationBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    annotationID: int = Field(
        alias="Annotation_ID", description="Primary key, auto-incremented"
    )


class DataProvenanceBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    dataprovenanceName: str = Field(
        alias="DataProvenance_Name",
        description="Name of the provenance. Controlled vocabulary: Sensor, Laboratory, Manual Entry, Model Output, External Source, Forecast",
        max_length=50,
    )


class DataProvenanceCreate(DataProvenanceBase):
    pass


class DataProvenance(DataProvenanceBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    dataprovenanceID: int = Field(
        alias="DataProvenance_ID", description="Surrogate primary key"
    )


class DatasetChannelBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    datasetID: int = Field(
        alias="Dataset_ID", description="The dataset this channel belongs to"
    )
    channelID: int = Field(
        alias="Channel_ID", description="The channel (signal) included in this dataset"
    )


class DatasetChannelCreate(DatasetChannelBase):
    pass


class DatasetChannel(DatasetChannelBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ValueBinBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    valuebinningaxisID: int = Field(
        alias="ValueBinningAxis_ID", description="References the parent binning axis"
    )
    binindex: int = Field(
        alias="BinIndex",
        description="0-based ordinal position of this bin within its axis",
    )
    lowerbound: Optional[Any] = Field(
        alias="LowerBound",
        description="Inclusive lower edge of this bin in the axis unit; NULL for 'nominal' mode bins",
    )
    upperbound: Optional[Any] = Field(
        alias="UpperBound",
        description="Exclusive upper edge of this bin in the axis unit; must be greater than LowerBound when set; NULL for 'nominal' mode bins",
    )
    nominalvalue: Optional[Any] = Field(
        alias="NominalValue",
        description="Nominal (center or exact) value of this bin in the axis unit; NULL for 'interval' mode bins",
    )


class ValueBinCreate(ValueBinBase):
    pass


class ValueBin(ValueBinBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    valuebinID: int = Field(alias="ValueBin_ID", description="Surrogate primary key")


class SiteBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    watershedID: Optional[int] = Field(
        alias="Watershed_ID", description="Linked to the Watershed table"
    )
    name: Optional[str] = Field(
        alias="Name", description="Name of the site", max_length=100
    )
    sitetypeID: Optional[int] = Field(
        alias="SiteKind_ID", description="Type of the site via SiteKind lookup"
    )
    description: Optional[str] = Field(
        alias="Description", description="Description of the site"
    )
    latitudewgs84: Optional[float] = Field(
        alias="LatitudeWGS84",
        description="Latitude of the site in WGS84 decimal degrees",
    )
    longitudewgs84: Optional[float] = Field(
        alias="LongitudeWGS84",
        description="Longitude of the site in WGS84 decimal degrees",
    )
    streetnumber: Optional[str] = Field(
        alias="StreetNumber",
        description="Address: number of the street",
        max_length=100,
    )
    streetname: Optional[str] = Field(
        alias="StreetName", description="Address: name of the street", max_length=100
    )
    city: Optional[str] = Field(
        alias="City", description="Address: name of the city", max_length=255
    )
    postcode: Optional[str] = Field(
        alias="PostCode", description="Address: postal code", max_length=100
    )
    province: Optional[str] = Field(
        alias="Province", description="Address: name of the province", max_length=255
    )
    country: Optional[str] = Field(
        alias="Country", description="Address: name of the country", max_length=255
    )


class SiteCreate(SiteBase):
    pass


class Site(SiteBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    siteID: int = Field(
        alias="Site_ID",
        description="A unique ID is generated automatically by the database",
    )


class EquipmentWiringHistoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmentID: int = Field(
        alias="Equipment_ID", description="The equipment whose wiring is recorded here"
    )
    signalinterfaceID: int = Field(
        alias="SignalInterface_ID",
        description="The SignalInterface this equipment is wired to during this period",
    )
    signalinterfaceportID: Optional[int] = Field(
        alias="SignalInterfacePort_ID",
        description="Specific port on the interface. NULL when the interface is a single-stream endpoint or the port is unknown.",
    )
    validfrom: datetime = Field(
        alias="ValidFrom", description="UTC datetime when this wiring became active"
    )
    validto: Optional[datetime] = Field(
        alias="ValidTo",
        description="UTC datetime when this wiring was removed. NULL = currently active.",
    )
    note: Optional[str] = Field(
        alias="Note",
        description="Free-text notes (e.g. reason for swap, calibration context)",
    )


class EquipmentWiringHistoryCreate(EquipmentWiringHistoryBase):
    pass


class EquipmentWiringHistory(EquipmentWiringHistoryBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmentwiringhistoryID: int = Field(
        alias="EquipmentWiringHistory_ID", description="Surrogate primary key"
    )


class ChannelPortHistoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    channelID: int = Field(
        alias="Channel_ID", description="Channel whose port binding is being recorded"
    )
    signalinterfaceportID: Optional[int] = Field(
        alias="SignalInterfacePort_ID",
        description="Port the channel is bound to during this period. NULL during a gating window when the stream is not active on any port.",
    )
    validfrom: datetime = Field(
        alias="ValidFrom", description="UTC datetime when this binding became active"
    )
    validto: Optional[datetime] = Field(
        alias="ValidTo",
        description="UTC datetime when this binding was superseded. NULL = currently active.",
    )
    gatingnote: Optional[str] = Field(
        alias="GatingNote",
        description="Free-text notes about gating (e.g. multiplexer routing rationale)",
    )


class ChannelPortHistoryCreate(ChannelPortHistoryBase):
    pass


class ChannelPortHistory(ChannelPortHistoryBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    channelporthistoryID: int = Field(
        alias="ChannelPortHistory_ID", description="Surrogate primary key"
    )


class LaboratoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str = Field(
        alias="Name", description="Name of the laboratory", max_length=200
    )
    siteID: Optional[int] = Field(
        alias="Site_ID",
        description="Site where the laboratory is located, if on-site. NULL for external labs.",
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Additional information about the laboratory",
        max_length=500,
    )


class LaboratoryCreate(LaboratoryBase):
    pass


class Laboratory(LaboratoryBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    laboratoryID: int = Field(
        alias="Laboratory_ID", description="Surrogate primary key"
    )


class AnnotationTypeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    annotationtypeID: int = Field(
        alias="AnnotationType_ID", description="Primary key, manually assigned"
    )
    annotationtypename: str = Field(
        alias="AnnotationTypeName",
        description="Human-readable name of the annotation type",
        max_length=100,
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Explanation of when to use this annotation type",
        max_length=500,
    )
    color: Optional[str] = Field(
        alias="Color",
        description="Hex color code for UI rendering, e.g. '#FF6B6B'",
        max_length=7,
    )


class AnnotationTypeCreate(AnnotationTypeBase):
    pass


class AnnotationType(AnnotationTypeBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProcessingLineageBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    processingstepID: int = Field(
        alias="ProcessingStep_ID",
        description="The processing step that consumed or produced the Channel entry",
    )
    channelID: int = Field(
        alias="Channel_ID",
        description="The Channel entry (time series) that participates in this lineage edge",
    )
    roleinprocessingstep: str = Field(
        alias="RoleInProcessingStep",
        description="Whether this Channel entry was an Input (consumed by the step) or an Output (produced by the step). CHECK constraint enforces 'Input' or 'Output'.\n",
        max_length=10,
    )
    starttime: Optional[datetime] = Field(
        alias="StartTime",
        description="Start of the data slice that was consumed or produced by this step (UTC). NULL means the edge applies to the entire channel from the beginning.\n",
    )
    endtime: Optional[datetime] = Field(
        alias="EndTime",
        description="End of the data slice that was consumed or produced by this step (UTC). NULL means the slice is open-ended (ongoing online processing).\n",
    )


class ProcessingLineageCreate(ProcessingLineageBase):
    pass


class ProcessingLineage(ProcessingLineageBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    processinglineageID: int = Field(
        alias="ProcessingLineage_ID", description="Surrogate primary key"
    )


class PersonBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    lastname: Optional[str] = Field(
        alias="LastName", description="Last name of the person", max_length=100
    )
    firstname: Optional[str] = Field(
        alias="FirstName", description="First name of the person", max_length=255
    )
    company: Optional[str] = Field(
        alias="Company", description="Affiliated organisation or company"
    )
    role: Optional[str] = Field(
        alias="Role",
        description="Role of the person. Controlled vocabulary: MSc, Postdoc, Intern, PhD, Professor, Research Professional, Technician, Administrator, Guest",
        max_length=255,
    )
    function: Optional[str] = Field(
        alias="Function",
        description="Detailed description of the person's assigned duties",
    )
    email: Optional[str] = Field(
        alias="Email", description="E-mail address", max_length=100
    )
    phone: Optional[str] = Field(
        alias="Phone", description="Phone number", max_length=100
    )
    linkedin: Optional[str] = Field(
        alias="Linkedin", description="LinkedIn profile URL", max_length=100
    )
    website: Optional[str] = Field(
        alias="Website",
        description="Personal or organisation website URL",
        max_length=60,
    )


class PersonCreate(PersonBase):
    pass


class Person(PersonBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    personID: int = Field(alias="Person_ID", description="Surrogate primary key")


class DataAcquisitionSystemBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    parentsystemID: Optional[int] = Field(
        alias="ParentSystem_ID",
        description="Optional parent DAS in a hierarchy (e.g. plant SCADA containing a PLC sub-system)",
    )
    name: str = Field(
        alias="Name",
        description="Human-readable name of the system (e.g. 'Plant SCADA', 'CommCube-A')",
        max_length=200,
    )
    dataacquisitionsystemkindID: Optional[int] = Field(
        alias="DataAcquisitionSystemKind_ID",
        description="Category of DAS (FK to DataAcquisitionSystemKind)",
    )
    manufacturer: Optional[str] = Field(
        alias="Manufacturer",
        description="Manufacturer or vendor of the system",
        max_length=100,
    )
    model: Optional[str] = Field(
        alias="Model", description="Model name or version of the system", max_length=100
    )
    description: Optional[str] = Field(
        alias="Description", description="Free-text notes about this DAS"
    )


class DataAcquisitionSystemCreate(DataAcquisitionSystemBase):
    pass


class DataAcquisitionSystem(DataAcquisitionSystemBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    dataacquisitionsystemID: int = Field(
        alias="DataAcquisitionSystem_ID", description="Surrogate primary key"
    )


class ChannelBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    signalinterfaceID: int = Field(
        alias="SignalInterface_ID",
        description="The SignalInterface this channel flows through (stable upstream identity). Equipment behind the interface is tracked via EquipmentWiringHistory, allowing probes to be swapped without breaking the Channel.\n",
    )
    tagname: str = Field(
        alias="TagName",
        description="Tag string as published by the upstream interface (case-preserved; lookups are case-insensitive trimmed). Forms part of the channel unique key together with SignalInterface_ID, Parameter_ID, DataProvenance_ID, and ProcessingDegree_ID.",
        max_length=200,
    )
    signalinterfaceportID: Optional[int] = Field(
        alias="SignalInterfacePort_ID",
        description="Optional specific port on the interface. NULL when the interface is a single-stream endpoint or the port is unknown.",
    )
    parentchannelID: Optional[int] = Field(
        alias="ParentChannel_ID",
        description="Parent Channel for sub-signals (Status, Alarm, Uncertainty). NULL for primary value channels.",
    )
    channelroleID: int = Field(
        alias="ChannelRole_ID",
        description="Functional role of this channel (FK to ChannelRole lookup). 1=Value (default), 2=Status, 3=Alarm, 4=Uncertainty.",
        default=1,
    )
    parameterID: Optional[int] = Field(
        alias="Parameter_ID",
        description="Measured analyte or parameter (e.g. TSS, pH). Part of the channel unique key.",
    )
    dataprovenanceID: Optional[int] = Field(
        alias="DataProvenance_ID",
        description="How this data was produced (Sensor=1, Laboratory=2, Manual Entry=3, Model Output=4, External Source=5, Forecast=6). Part of the channel unique key.\n",
    )
    processingdegreeID: Optional[int] = Field(
        alias="ProcessingDegree_ID",
        description="Level of processing applied to this time series (FK to ProcessingDegree lookup). Ground truth is the DataLineage graph; this field exists for fast filtering. Set once at row creation — if the processing degree changes, a new Channel row is created. Default 1 = Raw. Part of the channel unique key.\n",
        default=1,
    )
    valuetypeID: int = Field(
        alias="ValueType_ID",
        description="Shape of stored values (1=Scalar, 2=Vector, 3=Matrix, 4=Image)",
        default=1,
    )
    unitID: Optional[int] = Field(
        alias="Unit_ID",
        description="Unit of measurement for values stored in this channel (e.g. mg/L, NTU). Set at channel creation via the ingestion pipeline and treated as immutable thereafter — a unit change requires a new Channel row.\n",
    )


class ChannelCreate(ChannelBase):
    pass


class Channel(ChannelBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    channelID: int = Field(alias="Channel_ID", description="Surrogate primary key")


class SamplingPointBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    siteID: int = Field(
        alias="Site_ID", description="Site this sampling point belongs to"
    )
    samplingpoint: str = Field(
        alias="SamplingPoint",
        description='Name of the sampling location. For example: "Inlet", "Outlet" or "Upstream"',
        max_length=100,
    )
    samplinglocation: Optional[str] = Field(
        alias="SamplingLocation",
        description='Where the sample was taken. For example: "Biofiltration", "Sewer 01" or "Retention Tank"',
        max_length=100,
    )
    latitudewgs84: Optional[float] = Field(
        alias="LatitudeWGS84",
        description="WGS84 latitude in decimal degrees. For example: 45.9070",
    )
    longitudewgs84: Optional[float] = Field(
        alias="LongitudeWGS84",
        description="WGS84 longitude in decimal degrees. For example: -73.7833",
    )
    description: Optional[str] = Field(
        alias="Description", description="Description of the sampling point"
    )
    pictures: Optional[Any] = Field(alias="Pictures", description="Picture of the site")
    validfrom: Optional[datetime] = Field(
        alias="ValidFrom",
        description="Date from which this sampling point record is considered valid (UTC). NULL means valid from the beginning of records.",
    )
    validto: Optional[datetime] = Field(
        alias="ValidTo",
        description="Date until which this sampling point record is valid (UTC). NULL means currently active.",
    )
    createdbycampaignID: Optional[int] = Field(
        alias="CreatedByCampaign_ID",
        description="Campaign during which this sampling point was first established (if applicable)",
    )


class SamplingPointCreate(SamplingPointBase):
    pass


class SamplingPoint(SamplingPointBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    samplingpointID: int = Field(
        alias="SamplingPoint_ID", description="Link to the SamplingPoint table"
    )


class CampaignTypeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    campaigntypeName: str = Field(
        alias="CampaignType_Name",
        description="Name of the campaign type. Controlled vocabulary: Experiment, Operations, Commissioning",
        max_length=100,
    )


class CampaignTypeCreate(CampaignTypeBase):
    pass


class CampaignType(CampaignTypeBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    campaigntypeID: int = Field(
        alias="CampaignType_ID", description="Surrogate primary key"
    )


class ValueTypeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    valuetypeName: str = Field(
        alias="ValueType_Name",
        description="Human-readable name of the value type (Scalar, Vector, Matrix, or Image)",
        max_length=50,
    )


class ValueTypeCreate(ValueTypeBase):
    pass


class ValueType(ValueTypeBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    valuetypeID: int = Field(alias="ValueType_ID", description="Surrogate primary key")


class ProceduresBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    procedurename: Optional[str] = Field(
        alias="ProcedureName", description="Title name of the procedure", max_length=100
    )
    proceduretype: Optional[str] = Field(
        alias="ProcedureType",
        description="Type of the procedure. For example, SOP",
        max_length=255,
    )
    description: Optional[str] = Field(
        alias="Description", description="Description of the procedure"
    )
    procedurelocation: Optional[str] = Field(
        alias="ProcedureLocation",
        description="Where is the procedure stored",
        max_length=100,
    )


class ProceduresCreate(ProceduresBase):
    pass


class Procedures(ProceduresBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    procedureID: int = Field(
        alias="Procedure_ID", description="Link to the Procedures table"
    )


class BinModeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    binmodeID: int = Field(
        alias="BinMode_ID", description="Surrogate primary key, manually assigned"
    )
    name: str = Field(
        alias="Name",
        description="Mode name (e.g. 'interval', 'nominal', 'interval_with_nominal')",
        max_length=30,
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Explanation of what this bin mode means",
        max_length=200,
    )


class BinModeCreate(BinModeBase):
    pass


class BinMode(BinModeBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CampaignSamplingLocationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    campaignID: int = Field(
        alias="Campaign_ID", description="Campaign using this sampling location"
    )
    samplingpointID: int = Field(
        alias="SamplingPoint_ID", description="Sampling location used by the campaign"
    )
    role: Optional[str] = Field(
        alias="Role",
        description="Role of this location in the campaign (e.g., 'Inlet', 'Reference')",
        max_length=100,
    )


class CampaignSamplingLocationCreate(CampaignSamplingLocationBase):
    pass


class CampaignSamplingLocation(CampaignSamplingLocationBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ValueBinningAxisBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str = Field(
        alias="Name",
        description="Human-readable name identifying this axis configuration (e.g. 'S::CAN spectro::lyser UV-Vis')",
        max_length=200,
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Optional description of this axis",
        max_length=500,
    )
    numberofbins: int = Field(
        alias="NumberOfBins", description="Total number of bins defined on this axis"
    )
    unitID: int = Field(
        alias="Unit_ID",
        description="Physical unit of the axis coordinates (e.g. nm, µm, m/s) — distinct from the measured value unit stored in Channel",
    )
    binmodeID: int = Field(
        alias="BinMode_ID",
        description="Declares how all bins on this axis are specified; FK to BinMode (1=interval, 2=interval_with_nominal, 3=nominal)",
        default=1,
    )


class ValueBinningAxisCreate(ValueBinningAxisBase):
    pass


class ValueBinningAxis(ValueBinningAxisBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    valuebinningaxisID: int = Field(
        alias="ValueBinningAxis_ID", description="Surrogate primary key"
    )


class CampaignEquipmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    campaignID: int = Field(
        alias="Campaign_ID", description="Campaign using this equipment"
    )
    equipmentID: int = Field(
        alias="Equipment_ID", description="Equipment deployed during the campaign"
    )
    role: Optional[str] = Field(
        alias="Role",
        description="Role of this equipment in the campaign (e.g., 'Primary sensor', 'Auto-sampler')",
        max_length=100,
    )


class CampaignEquipmentCreate(CampaignEquipmentBase):
    pass


class CampaignEquipment(CampaignEquipmentBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WatershedBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: Optional[str] = Field(
        alias="Name", description="Name of the watershed", max_length=100
    )
    description: Optional[str] = Field(
        alias="Description", description="Description of the watershed"
    )
    surfacearea: Optional[Any] = Field(
        alias="SurfaceArea", description="Surface area of the watershed [ha]"
    )
    concentrationtime: Optional[int] = Field(
        alias="ConcentrationTime", description="Concentration time in minutes [min]"
    )
    impervioussurface: Optional[Any] = Field(
        alias="ImperviousSurface",
        description="Percentage of the impervious surface of the watershed in percentage [%]",
    )


class WatershedCreate(WatershedBase):
    pass


class Watershed(WatershedBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    watershedID: int = Field(
        alias="Watershed_ID", description="Linked to the Watershed table"
    )


class ValueVectorBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    observationID: int = Field(
        alias="Observation_ID",
        description="References the Observation (channel + timestamp) for this measurement",
    )
    valuebinID: int = Field(
        alias="ValueBin_ID",
        description="References the bin (and through it, the axis) for this value",
    )
    value: Optional[Any] = Field(
        alias="Value", description="Measured value at this bin"
    )
    qualitycode: Optional[int] = Field(
        alias="QualityCode", description="Quality flag for this measurement"
    )


class ValueVectorCreate(ValueVectorBase):
    pass


class ValueVector(ValueVectorBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EquipmentModelHasParameterBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmentmodelID: int = Field(
        alias="EquipmentModel_ID", description="Link to the Equipment model table"
    )
    parameterID: int = Field(
        alias="Parameter_ID", description="Link to the Parameter table"
    )


class EquipmentModelHasParameterCreate(EquipmentModelHasParameterBase):
    pass


class EquipmentModelHasParameter(EquipmentModelHasParameterBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SampleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    parentsampleID: Optional[int] = Field(
        alias="ParentSample_ID",
        description="Parent sample this was derived from (e.g., an aliquot of a master standard). NULL for primary samples.",
    )
    sampletypeID: Optional[int] = Field(
        alias="SampleType_ID",
        description="Nature of the sample (FK to SampleType lookup table)",
    )
    samplingpointID: int = Field(
        alias="SamplingPoint_ID",
        description="Sampling location where the sample was collected or prepared",
    )
    sampledbypersonID: Optional[int] = Field(
        alias="SampledByPerson_ID", description="Person who collected the sample"
    )
    campaignID: Optional[int] = Field(
        alias="Campaign_ID", description="Campaign this sample belongs to"
    )
    sampledatetimestart: datetime = Field(
        alias="SampleDateTimeStart", description="Date and time sampling began (UTC)"
    )
    sampledatetimeend: Optional[datetime] = Field(
        alias="SampleDateTimeEnd",
        description="Date and time sampling ended (UTC). NULL for instantaneous grab samples.",
    )
    samplemethodID: Optional[int] = Field(
        alias="SampleMethod_ID",
        description="Method of sample collection (FK to SampleMethod lookup table)",
    )
    sampleequipmentID: Optional[int] = Field(
        alias="SampleEquipment_ID",
        description="Equipment used to collect the sample (e.g., auto-sampler)",
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Additional notes about the sample",
        max_length=500,
    )


class SampleCreate(SampleBase):
    pass


class Sample(SampleBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    sampleID: int = Field(alias="Sample_ID", description="Surrogate primary key")


class LabValueBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    labanalysisID: int = Field(
        alias="LabAnalysis_ID", description="The analysis run this value belongs to"
    )
    parameterID: int = Field(
        alias="Parameter_ID", description="Measured analyte (e.g. TSS, COD)"
    )
    labresult: Any = Field(
        alias="LabResult", description="Numerical result of the measurement"
    )
    replicate: int = Field(
        alias="Replicate",
        description="Replicate number (1 = primary measurement, 2+ = duplicates)",
        default=1,
    )
    qualitycodeID: Optional[int] = Field(
        alias="QualityCode_ID",
        description="Optional quality flag. NULL means no quality assessment has been recorded.",
    )
    comment: Optional[str] = Field(
        alias="Comment",
        description="Optional free-text comment reference",
        max_length=None,
    )


class LabValueCreate(LabValueBase):
    pass


class LabValue(LabValueBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    labvalueID: int = Field(alias="LabValue_ID", description="Surrogate primary key")


class SignalInterfaceBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    dataacquisitionsystemID: int = Field(
        alias="DataAcquisitionSystem_ID", description="The DAS that owns this interface"
    )
    signalinterfacetypeID: int = Field(
        alias="SignalInterfaceType_ID",
        description="Kind of upstream interface (PLC, SCADA, Basestation, DirectConnect, ...)",
    )
    name: str = Field(
        alias="Name",
        description="Human-readable interface name, unique within its parent DAS",
        max_length=200,
    )
    make: Optional[str] = Field(
        alias="Make",
        description="Manufacturer / make of the upstream interface",
        max_length=100,
    )
    model: Optional[str] = Field(
        alias="Model",
        description="Model or product name of the upstream interface",
        max_length=100,
    )
    serialnumber: Optional[str] = Field(
        alias="SerialNumber",
        description="Serial number of the upstream interface",
        max_length=100,
    )
    description: Optional[str] = Field(
        alias="Description", description="Free-text notes about this interface"
    )
    isactive: bool = Field(
        alias="IsActive",
        description="Whether this interface is currently expected to publish data. Set to false when retired.",
        default=True,
    )


class SignalInterfaceCreate(SignalInterfaceBase):
    pass


class SignalInterface(SignalInterfaceBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    signalinterfaceID: int = Field(
        alias="SignalInterface_ID", description="Surrogate primary key"
    )


class SignalInterfacePortBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    signalinterfaceID: int = Field(
        alias="SignalInterface_ID",
        description="The SignalInterface this port belongs to",
    )
    portidentifier: str = Field(
        alias="PortIdentifier",
        description="Identifier of the port within its interface (e.g. terminal label, channel number, mux slot)",
        max_length=100,
    )
    signalinterfaceportkindID: int = Field(
        alias="SignalInterfacePortKind_ID",
        description="Physical kind of the port (AnalogIn, Serial, Virtual, ...)",
    )
    description: Optional[str] = Field(
        alias="Description", description="Free-text notes about this port"
    )
    isactive: bool = Field(
        alias="IsActive",
        description="Whether this port is currently expected to receive data. Set to false when retired.",
        default=True,
    )


class SignalInterfacePortCreate(SignalInterfacePortBase):
    pass


class SignalInterfacePort(SignalInterfacePortBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    signalinterfaceportID: int = Field(
        alias="SignalInterfacePort_ID", description="Surrogate primary key"
    )


class EquipmentEventTypeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmenteventtypeName: str = Field(
        alias="EquipmentEventType_Name",
        description="Name of the event type. Controlled vocabulary: Calibration, Validation, Maintenance, Installation, Removal, Firmware Update, Failure, Repair",
        max_length=100,
    )


class EquipmentEventTypeCreate(EquipmentEventTypeBase):
    pass


class EquipmentEventType(EquipmentEventTypeBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmenteventtypeID: int = Field(
        alias="EquipmentEventType_ID", description="Surrogate primary key"
    )


class SampleTypeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    sampletypeID: int = Field(
        alias="SampleType_ID", description="Surrogate primary key, manually assigned"
    )
    name: str = Field(
        alias="Name",
        description="Sample type name (e.g. 'Field', 'Blank')",
        max_length=50,
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Explanation of what this sample type represents",
        max_length=200,
    )


class SampleTypeCreate(SampleTypeBase):
    pass


class SampleType(SampleTypeBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EquipmentModelBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmentmodel: Optional[str] = Field(
        alias="EquipmentModel",
        description="Name of the equipment model. For example: ammo::lyser",
        max_length=100,
    )
    method: Optional[str] = Field(
        alias="Method", description="Method behind the equipment", max_length=100
    )
    functions: Optional[str] = Field(
        alias="Functions", description="Description of the functions of the equipment"
    )
    manufacturer: Optional[str] = Field(
        alias="Manufacturer", description="Name of the manufacturer", max_length=100
    )
    manuallocation: Optional[str] = Field(
        alias="ManualLocation",
        description="Location where the manual is stored",
        max_length=100,
    )


class EquipmentModelCreate(EquipmentModelBase):
    pass


class EquipmentModel(EquipmentModelBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmentmodelID: int = Field(
        alias="EquipmentModel_ID", description="Link to the Equipment model table"
    )


class LabAnalysisBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    sampleID: int = Field(
        alias="Sample_ID", description="The physical sample that was analysed"
    )
    laboratoryID: Optional[int] = Field(
        alias="Laboratory_ID", description="Laboratory where the analysis was performed"
    )
    analystpersonID: Optional[int] = Field(
        alias="AnalystPerson_ID", description="Person who performed the analysis"
    )
    procedureID: Optional[int] = Field(
        alias="Procedure_ID",
        description="Standard operating procedure used for this analysis",
    )
    analysisdatetime: datetime = Field(
        alias="AnalysisDateTime",
        description="UTC datetime when the analysis was performed. If it's a long analysis, record the beginning.",
        default="SYSUTCDATETIME()",
    )
    campaignID: Optional[int] = Field(
        alias="Campaign_ID", description="Campaign this analysis was part of, if any"
    )
    notes: Optional[str] = Field(
        alias="Notes",
        description="Free-text notes about this analysis run",
        max_length=None,
    )


class LabAnalysisCreate(LabAnalysisBase):
    pass


class LabAnalysis(LabAnalysisBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    labanalysisID: int = Field(
        alias="LabAnalysis_ID", description="Surrogate primary key"
    )


class LandUseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    commercial: Optional[Any] = Field(
        alias="Commercial",
        description="Percentage [%] of commercial areas. For example stores or bank areas",
    )
    greenspaces: Optional[Any] = Field(
        alias="GreenSpaces", description="Percentage [%] of green spaces"
    )
    industrial: Optional[Any] = Field(
        alias="Industrial",
        description="Percentage [%] of industrial areas. For example factories",
    )
    institutional: Optional[Any] = Field(
        alias="Institutional",
        description="Percentage [%] of institutional areas. For example schools, police stations or city hall",
    )
    residential: Optional[Any] = Field(
        alias="Residential",
        description="Percentage [%] of residential areas. For example houses or apartment buildings",
    )
    agricultural: Optional[Any] = Field(
        alias="Agricultural",
        description="Percentage [%] of agricultural land use. For example farm land",
    )
    recreational: Optional[Any] = Field(
        alias="Recreational",
        description="Percentage [%] of recreational areas. For example parks or sport fields",
    )


class LandUseCreate(LandUseBase):
    pass


class LandUse(LandUseBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    watershedID: int = Field(
        alias="Watershed_ID", description="Linked to the Watershed table"
    )


class ProcessingStepBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str = Field(
        alias="Name",
        description="Human-readable name for this processing step (e.g. 'Outlier removal — Hampel filter')",
        max_length=200,
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Free-text description of what this step does and why it was applied",
        max_length=None,
    )
    methodname: Optional[str] = Field(
        alias="MethodName",
        description="Machine-readable method identifier (e.g. 'outlier_removal', 'linear_interpolation'). Maps to a metEAUdata processing function name.",
        max_length=200,
    )
    methodversion: Optional[str] = Field(
        alias="MethodVersion",
        description="Version of the method or library used (e.g. 'meteaudata 0.5.1')",
        max_length=100,
    )
    processingkindid: Optional[int] = Field(
        alias="ProcessingKind_ID",
        description="Category of processing applied (FK to ProcessingKind lookup). Replaces former free-text ProcessingType column.\n",
    )
    parameters: Optional[str] = Field(
        alias="Parameters",
        description='JSON blob of method parameters (e.g. \'{"window": 5, "threshold": 3.0}\')',
    )
    executeddatetime: Optional[datetime] = Field(
        alias="ExecutedDateTime",
        description="UTC timestamp when this processing step was executed",
    )
    executedbypersonID: Optional[int] = Field(
        alias="ExecutedByPerson_ID",
        description="Person who ran or triggered this processing step. NULL for automated/unattended runs.",
    )
    datasetID: Optional[int] = Field(
        alias="Dataset_ID",
        description="The Dataset this processing step belongs to. NULL for steps that operate on a single channel without a named analysis context. Required for multivariate steps that consume or produce multiple channels.\n",
    )


class ProcessingStepCreate(ProcessingStepBase):
    pass


class ProcessingStep(ProcessingStepBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    processingstepID: int = Field(
        alias="ProcessingStep_ID", description="Surrogate primary key"
    )


class ControlLoopBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str = Field(
        alias="Name",
        description="Human-readable name for this control loop",
        max_length=200,
    )
    controllerkindID: int = Field(
        alias="ControllerKind_ID",
        description="Controller algorithm class (FK to ControllerKind)",
    )
    fallbackcontrolloopID: Optional[int] = Field(
        alias="FallbackControlLoop_ID",
        description="The control loop that takes over if this loop is deactivated. NULL = falls back to manual operation.",
    )
    algorithmreference: Optional[str] = Field(
        alias="AlgorithmReference",
        description="Path or repository URL for custom algorithm implementations",
        max_length=500,
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Narrative description of the loop, including notes on novel roles",
    )


class ControlLoopCreate(ControlLoopBase):
    pass


class ControlLoop(ControlLoopBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    controlloopID: int = Field(
        alias="ControlLoop_ID", description="Surrogate primary key"
    )


class SiteKindBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str = Field(
        alias="Name",
        description="Name of the site kind (e.g. Wastewater Treatment Plant)",
        max_length=100,
    )
    description: Optional[str] = Field(
        alias="Description", description="Detailed description of the site kind"
    )


class SiteKindCreate(SiteKindBase):
    pass


class SiteKind(SiteKindBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    sitekindID: int = Field(
        alias="SiteKind_ID", description="Primary key for the SiteKind lookup"
    )


class EquipmentEventBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmentID: int = Field(
        alias="Equipment_ID", description="Equipment on which the event occurred"
    )
    equipmenteventtypeID: int = Field(
        alias="EquipmentEventType_ID", description="Type of lifecycle event"
    )
    eventdatetimestart: datetime = Field(
        alias="EventDateTimeStart", description="Date and time the event began (UTC)"
    )
    eventdatetimeend: Optional[datetime] = Field(
        alias="EventDateTimeEnd",
        description="Date and time the event ended (UTC). NULL if instantaneous or ongoing.",
    )
    performedbypersonID: Optional[int] = Field(
        alias="PerformedByPerson_ID",
        description="Person who performed or recorded the event",
    )
    campaignID: Optional[int] = Field(
        alias="Campaign_ID",
        description="Campaign during which this event occurred (if applicable)",
    )
    notes: Optional[str] = Field(
        alias="Notes", description="Free-text notes about the event", max_length=None
    )


class EquipmentEventCreate(EquipmentEventBase):
    pass


class EquipmentEvent(EquipmentEventBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmenteventID: int = Field(
        alias="EquipmentEvent_ID", description="Surrogate primary key"
    )


class ChannelAxisBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    channelID: int = Field(
        alias="Channel_ID", description="References the measurement channel"
    )
    axisrole: int = Field(
        alias="AxisRole",
        description="Dimension role: 0 = primary/row axis, 1 = secondary/column axis (Matrix only)",
    )
    valuebinningaxisID: int = Field(
        alias="ValueBinningAxis_ID",
        description="References the binning axis for this role",
    )


class ChannelAxisCreate(ChannelAxisBase):
    pass


class ChannelAxis(ChannelAxisBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProcessingDegreeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    processingdegreeID: int = Field(
        alias="ProcessingDegree_ID",
        description="Surrogate primary key, manually assigned",
    )
    name: str = Field(
        alias="Name",
        description="Processing level name (e.g. 'Raw', 'Cleaned')",
        max_length=50,
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Explanation of what this processing level means",
        max_length=200,
    )


class ProcessingDegreeCreate(ProcessingDegreeBase):
    pass


class ProcessingDegree(ProcessingDegreeBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DatasetBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str = Field(
        alias="Name",
        description="Human-readable name for the dataset (e.g. 'WWTP Influent Q1-2024 Multivariate')",
        max_length=200,
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Detailed description of the dataset's contents, scope, and intended use",
        max_length=2000,
    )
    purpose: Optional[str] = Field(
        alias="Purpose",
        description="The analytical or processing objective this dataset was assembled for (e.g. 'Fault detection model training', 'Compliance reporting', 'Gap-filling pipeline').\n",
        max_length=500,
    )
    createdon: datetime = Field(
        alias="CreatedOn",
        description="UTC timestamp when this dataset was created",
        default="CURRENT_TIMESTAMP",
    )
    createdbypersonID: Optional[int] = Field(
        alias="CreatedByPerson_ID",
        description="Person who created this dataset. NULL for automated pipelines.",
    )


class DatasetCreate(DatasetBase):
    pass


class Dataset(DatasetBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    datasetID: int = Field(alias="Dataset_ID", description="Surrogate primary key")


class ValueMatrixBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    observationID: int = Field(
        alias="Observation_ID",
        description="References the Observation (channel + timestamp) for this measurement",
    )
    rowvaluebinID: int = Field(
        alias="RowValueBin_ID",
        description="References the bin on the row axis (AxisRole=0)",
    )
    colvaluebinID: int = Field(
        alias="ColValueBin_ID",
        description="References the bin on the column axis (AxisRole=1)",
    )
    value: Optional[Any] = Field(
        alias="Value", description="Measured value at this (row-bin, col-bin) cell"
    )
    qualitycode: Optional[int] = Field(
        alias="QualityCode", description="Quality flag for this measurement"
    )


class ValueMatrixCreate(ValueMatrixBase):
    pass


class ValueMatrix(ValueMatrixBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EquipmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmentmodelID: Optional[int] = Field(
        alias="EquipmentModel_ID", description="Link to the Equipment model table"
    )
    identifier: Optional[str] = Field(
        alias="Identifier",
        description="Identification name of the equipment",
        max_length=100,
    )
    serialnumber: Optional[str] = Field(
        alias="SerialNumber",
        description="Serial number of the equipment",
        max_length=100,
    )
    owner: Optional[str] = Field(
        alias="Owner", description="Name of the owner of the equipment"
    )
    storagelocation: Optional[str] = Field(
        alias="StorageLocation",
        description="Where the equipment is stored when not deployed",
        max_length=100,
    )
    purchasedate: Optional[Any] = Field(
        alias="PurchaseDate",
        description="Date when the equipment was bought: 'YYYY-MM-DD'",
    )
    isactive: bool = Field(
        alias="IsActive",
        description="Whether this equipment is currently in service. Set to false when decommissioned. Decommissioning should also be recorded as an EquipmentEvent for auditability. Enables fast active/inactive filtering without inspecting EquipmentWiringHistory.\n",
        default=True,
    )


class EquipmentCreate(EquipmentBase):
    pass


class Equipment(EquipmentBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmentID: int = Field(alias="Equipment_ID", description="Surrogate primary key")


class EquipmentModelHasProceduresBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    equipmentmodelID: int = Field(
        alias="EquipmentModel_ID", description="Link to the Equipment model table"
    )
    procedureID: int = Field(
        alias="Procedure_ID", description="Link to the Procedures table"
    )


class EquipmentModelHasProceduresCreate(EquipmentModelHasProceduresBase):
    pass


class EquipmentModelHasProcedures(EquipmentModelHasProceduresBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UnitBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    unit: Optional[str] = Field(
        alias="Unit", description="SI-units only", max_length=100
    )


class UnitCreate(UnitBase):
    pass


class Unit(UnitBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    unitID: int = Field(
        alias="Unit_ID",
        description="A unique ID is generated automatically by the database",
    )


class ControlLoopPortRoleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    controlloopportroleID: int = Field(
        alias="ControlLoopPortRole_ID",
        description="Surrogate primary key, manually assigned",
    )
    name: str = Field(
        alias="Name", description="Short name for this role", max_length=50
    )
    description: Optional[str] = Field(
        alias="Description",
        description="Explanation of the role within a control loop",
        max_length=200,
    )


class ControlLoopPortRoleCreate(ControlLoopPortRoleBase):
    pass


class ControlLoopPortRole(ControlLoopPortRoleBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ParameterBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    parameter: Optional[str] = Field(
        alias="Parameter", description="Name of the parameter", max_length=100
    )
    description: Optional[str] = Field(
        alias="Description", description="Description of the parameter"
    )


class ParameterCreate(ParameterBase):
    pass


class Parameter(ParameterBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    parameterID: int = Field(
        alias="Parameter_ID", description="Link to the Parameter table"
    )


class ControlLoopPortBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    controlloopID: int = Field(
        alias="ControlLoop_ID",
        description="The control loop this association belongs to",
    )
    channelID: int = Field(
        alias="Channel_ID", description="The channel participating in this control loop"
    )
    controlloopportroleID: int = Field(
        alias="ControlLoopPortRole_ID",
        description="The functional role of this channel within the loop",
    )


class ControlLoopPortCreate(ControlLoopPortBase):
    pass


class ControlLoopPort(ControlLoopPortBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    controlloopportID: int = Field(
        alias="ControlLoopPort_ID", description="Surrogate primary key"
    )


class ControlLoopApplicationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    controlloopID: int = Field(
        alias="ControlLoop_ID",
        description="The control loop this application configuration belongs to",
    )
    starttime: datetime = Field(
        alias="StartTime",
        description="UTC datetime when this configuration became active",
    )
    endtime: Optional[datetime] = Field(
        alias="EndTime",
        description="UTC datetime when this configuration was superseded. NULL = currently active.",
    )
    parameters: Optional[str] = Field(
        alias="Parameters",
        description='JSON blob of controller parameters for this application window. Examples: {"Kp":2.5,"Ki":0.1,"Kd":0.0} for PID; {"weights":{"DO":1.0,"NH4":0.5},"horizon":12} for MPC. Schema is controller-type-specific and deliberately unstructured.\n',
    )
    appliedbypersonID: Optional[int] = Field(
        alias="AppliedByPerson_ID",
        description="Person who activated this configuration",
    )
    notes: Optional[str] = Field(
        alias="Notes", description="Free-text notes about this configuration change"
    )


class ControlLoopApplicationCreate(ControlLoopApplicationBase):
    pass


class ControlLoopApplication(ControlLoopApplicationBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    controlloopapplicationID: int = Field(
        alias="ControlLoopApplication_ID", description="Surrogate primary key"
    )


class vw_ChannelStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    statuschannelid: Any = Field(
        alias="StatusChannelID", description="Channel_ID of the status time series"
    )
    measurementchannelid: Any = Field(
        alias="MeasurementChannelID",
        description="Channel_ID of the measurement channel this status describes",
    )
    equipmentid: Any = Field(
        alias="EquipmentID",
        description="Equipment ID of the currently-linked sensor (NULL if no active history row)",
    )
    equipmentname: Any = Field(
        alias="EquipmentName",
        description="Identifier of the currently-linked equipment",
    )
    measurementparameter: Any = Field(
        alias="MeasurementParameter",
        description="Name of the measured parameter (TSS, pH, etc.)",
    )
    timestamp: Any = Field(
        alias="Timestamp", description="Timestamp of the status observation"
    )
    statuscodeid: Any = Field(
        alias="StatusCodeID",
        description="Raw integer status code stored in the status Channel's Value rows",
    )


class vw_DeviceStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    statuschannelid: Any = Field(
        alias="StatusChannelID", description="Channel_ID of the status time series"
    )
    equipmentid: Any = Field(
        alias="EquipmentID", description="Equipment ID this status describes"
    )
    equipmentname: Any = Field(
        alias="EquipmentName", description="Identifier of the equipment"
    )
    timestamp: Any = Field(
        alias="Timestamp", description="Timestamp of the status observation"
    )
    statuscodeid: Any = Field(
        alias="StatusCodeID",
        description="Raw integer status code stored in the status Channel's Value rows",
    )
