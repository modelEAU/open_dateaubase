# Value Sets

Controlled vocabularies used throughout database.


<span id="Part_type_set"></span>

## Part Type Set

Valid values for part types


| Value | Description |
|-------|-------------|
| <span id="table"></span>`table` | Represents a database table |
| <span id="key"></span>`key` | Represents a primary key |
| <span id="property"></span>`property` | Represents a column/field in a table |
| <span id="compositeKeyFirst"></span>`compositeKeyFirst` | First component of a composite primary key |
| <span id="compositeKeySecond"></span>`compositeKeySecond` | Second component of a composite primary key |
| <span id="parentKey"></span>`parentKey` | Hierarchical reference to parent record in same table |
| <span id="valueSet"></span>`valueSet` | Represents an enumeration or controlled vocabulary |
| <span id="valueSetMember"></span>`valueSetMember` | Individual value within a value set |
| <span id="view"></span>`view` | Represents a database view |
| <span id="viewColumn"></span>`viewColumn` | Represents a column in a database view |

<span id="campaign_type_set"></span>

## Campaign Type Set

Valid campaign type values


| Value | Description |
|-------|-------------|
| <span id="campaign_type_experiment"></span>`campaign_type_experiment` | Campaign type: Experiment |
| <span id="campaign_type_operations"></span>`campaign_type_operations` | Campaign type: Operations |
| <span id="campaign_type_commissioning"></span>`campaign_type_commissioning` | Campaign type: Commissioning |

<span id="data_provenance_set"></span>

## Data Provenance Set

Valid data provenance values describing how a measurement was produced


| Value | Description |
|-------|-------------|
| <span id="data_provenance_sensor"></span>`data_provenance_sensor` | Data provenance: Sensor |
| <span id="data_provenance_laboratory"></span>`data_provenance_laboratory` | Data provenance: Laboratory |
| <span id="data_provenance_manual_entry"></span>`data_provenance_manual_entry` | Data provenance: Manual Entry |
| <span id="data_provenance_model_output"></span>`data_provenance_model_output` | Data provenance: Model Output |
| <span id="data_provenance_external_source"></span>`data_provenance_external_source` | Data provenance: External Source |

<span id="equipment_event_type_set"></span>

## Equipment Event Type Set

Valid event types for equipment lifecycle events


| Value | Description |
|-------|-------------|
| <span id="equipment_event_type_calibration"></span>`equipment_event_type_calibration` | Equipment event type: Calibration |
| <span id="equipment_event_type_validation"></span>`equipment_event_type_validation` | Equipment event type: Validation |
| <span id="equipment_event_type_maintenance"></span>`equipment_event_type_maintenance` | Equipment event type: Maintenance |
| <span id="equipment_event_type_installation"></span>`equipment_event_type_installation` | Equipment event type: Installation |
| <span id="equipment_event_type_removal"></span>`equipment_event_type_removal` | Equipment event type: Removal |
| <span id="equipment_event_type_firmware_update"></span>`equipment_event_type_firmware_update` | Equipment event type: Firmware Update |
| <span id="equipment_event_type_failure"></span>`equipment_event_type_failure` | Equipment event type: Failure |
| <span id="equipment_event_type_repair"></span>`equipment_event_type_repair` | Equipment event type: Repair |

<span id="person_role_set"></span>

## Person Role Set

Valid role values for a Person record


| Value | Description |
|-------|-------------|
| <span id="person_role_msc"></span>`person_role_msc` | Person role: MSc |
| <span id="person_role_postdoc"></span>`person_role_postdoc` | Person role: Postdoc |
| <span id="person_role_intern"></span>`person_role_intern` | Person role: Intern |
| <span id="person_role_phd"></span>`person_role_phd` | Person role: PhD |
| <span id="person_role_professor"></span>`person_role_professor` | Person role: Professor |
| <span id="person_role_research_professional"></span>`person_role_research_professional` | Person role: Research Professional |
| <span id="person_role_technician"></span>`person_role_technician` | Person role: Technician |
| <span id="person_role_administrator"></span>`person_role_administrator` | Person role: Administrator |
| <span id="person_role_guest"></span>`person_role_guest` | Person role: Guest |

<span id="processing_degree_set"></span>

## Processing Degree Set

Valid processing degree values describing the level of processing applied to a measurement series


| Value | Description |
|-------|-------------|
| <span id="processing_degree_raw"></span>`processing_degree_raw` | Data as received directly from the instrument with no post-processing |
| <span id="processing_degree_cleaned"></span>`processing_degree_cleaned` | Outliers, artefacts or invalid values have been removed or flagged |
| <span id="processing_degree_validated"></span>`processing_degree_validated` | Data has been reviewed and accepted by a human analyst |
| <span id="processing_degree_interpolated"></span>`processing_degree_interpolated` | Gaps in the time series have been filled by interpolation |
| <span id="processing_degree_aggregated"></span>`processing_degree_aggregated` | Values have been time-averaged or otherwise aggregated from higher-frequency data |

<span id="sample_category_set"></span>

## Sample Category Set

Nature of a sample (field collection, prepared standard, blank, etc.)


| Value | Description |
|-------|-------------|
| <span id="sample_category_field"></span>`sample_category_field` | Sample category: Field |
| <span id="sample_category_synthetic"></span>`sample_category_synthetic` | Sample category: Synthetic |
| <span id="sample_category_master_standard"></span>`sample_category_master_standard` | Sample category: Master Standard |
| <span id="sample_category_derived_standard"></span>`sample_category_derived_standard` | Sample category: Derived Standard |
| <span id="sample_category_blank"></span>`sample_category_blank` | Sample category: Blank |

<span id="sample_type_set"></span>

## Sample Type Set

Valid sample collection method values


| Value | Description |
|-------|-------------|
| <span id="sample_type_grab"></span>`sample_type_grab` | Sample type: Grab |
| <span id="sample_type_composite24h"></span>`sample_type_composite24h` | Sample type: Composite24h |
| <span id="sample_type_composite8h"></span>`sample_type_composite8h` | Sample type: Composite8h |
| <span id="sample_type_passive"></span>`sample_type_passive` | Sample type: Passive |
| <span id="sample_type_other"></span>`sample_type_other` | Sample type: Other |