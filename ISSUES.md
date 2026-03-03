- Comments table should be removed. Superceded by Annotations.

- EquipmentEventChannel should be removed. You link up channels and equipment events by loking up the channel's equipment ID. Removed
- Number_of_experiment should be removed. Replicates only make sense in Laboratory assays, and those have moved.
- Channel does NOT need unitID since parameter defines the units
- SampleCategory and SampleType seem redundant -- investigate
- Lookup tables should respect the A-Has-B convention
- Campaigns have no business having parameters since they have equipment. Lookup table was removed
- ParameterHas Procedures is not useful. Removed.


- QualityCode should be a controlled dictionary. Consider creating a QualityCode table with a lookup table.
- ProcessingDegree should be a controlled dictionary. Consider creating a ProcessingDegree table with a lookup table.
- SampleMethod and SampleType are controlled vocabularies. Consider creating a SampleMethods and SampleType lookup tables.

- The implementation of data lineage and processing steps needs to be reviewed. The issue is the following.
    - Raw channels are typically the original data source, but not the full channel. Processing tends to happen in batches, on specific spans of data and on specific channels. The current implementation assumes en entire channel is being processed as a whole, and it assumes a processing step can only be applied to a channle once. In fact, people sample a stretch of data, apply preprocessing steps (any combination, sometimes the same step several times across a pipeline) and then they save that. Some pipelines are offline, some are online. The implementation needs to be revisited to accommodate these realities. The metEAUdata package (github)'s concept of dataset, coupled with unique identifiers for each dataset-signal-processing step application could provide a good starting point for addressing these concerns.

