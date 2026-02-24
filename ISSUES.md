ConditionID should be removed from metadataTable.
Condition is unknown at the time of recording data.
It is instead computed later on based on precipitation data (sometimes available, sometimes not.)
Condition should be replaced by a WeatherEvent table that tags spans of time for each site as "dry" or "wet" weather (to be discussed)
Purpose should be removed -- it's redundant with Provenance and the name doesn't convey its meaning


The current equipment -> parameter -> metadata ID is a bad abstraction. 

What really is going on is 
Equipment carry channels -> channels have a health status
                            channels have measurements 
                                                          -> both health status and measurements behave as time series.
Equipment is positioned at a sampling location
Sampling locations exist within a site
Equipment-location couples are decided for a campaign
Campaigns also occur at a site.
When recording a stream of measurements and a stream of health statuses, we do so from an equipment channel.
The data can be stored as that equipment-channel couple (with the added fact that it's RAW (Prcessing degree))
The other tables tell us what is the rest of the context (sampling location based on time, active campaign, and campaign-equipment-location binding)

But that's NOT what happens. Instead, incoming data has to be matched with a sampling location at ingestion time (based on the same information) and then a lookup happens in the metadata ID table to see of the equipment sampling location channel processing degree combination exists, and if so, we use that metadata id, and if not, we add another and use that.
