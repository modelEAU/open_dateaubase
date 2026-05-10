
# Pre-release bug-fixing spree

[ ] CampaignEquipment
    [ ] Role field should go away
    [ ] the API and UI behave as though the table had a notes filed but it doesn't. The UI and API should be updated (not the data model)
[ ] CampaignSamplingLocation
    [ ] [ ] Role field should go away
    [ ] the API and UI behave as though the table had a notes filed but it doesn't. The UI and API should be updated (not the data model)
[ ] Channel
    [ ] Reading the description made me realize that the fact that the SignalInterface is part of the channel identity means that the channel is invariant only if the sensor's wiring is not changed. There should be a page in the app (and possibly a history table too) to explicitly We need to think about whether we need to create a new page OR if the mere fact of changing the import configuration is a sufficient mechanism tio express the change. Looking more carefully, it seems ChannelPortHostory does this already, but we need to investigate.

[ ] The ProcessingKindID entry in Channel bothers me a bit because the value here is a lookup, but there is another table that has more detailed (possible different) info???

[ ] ProcessingKind: The values here are not correct. Processing Kind should have values like Raw, Free of outliers, Free of drift, Free of faults, smoothed, interpolated, predicted, derived.

[ ] We still need an example of matrix/ multidimensional data. A simple example would be to take image data and decompose it into X (axis 1), Y (axis 2), R(axis3), G(axis3), B (axis 5). If we can't do more than 2 axes, we write that down as a limitation. Makes sense?

[ ] ChannelPortHistory has a field called GatingNote which I don't understand. We ned to either make its purpose way clearer or just discard it.

[ ] ControllerType (in Control table) should be a ControllerKind and be a controlled dictionary.

[ ] SetPoint should be a ChannelKind (Per the ControlLoopApplication table description)

[ ] MPC Trajectory should also be a ChannelKind (A vector channel, with "Time horizon" being the bin axis)

[ ] SystemType should be a controlled vocabulary and renamed DataAcquisitionSystemKind

[ ] API/UI/import script design : Make sure that the timezones are well -handled.
    [ ] Import scripts should declare the time zone of the data in the config
    [ ] Fields filled in by a user in the UI should be converted from their browser's time zone to UTC when ingested.
    [ ] Time data displayed to the user should also be converted to their local time zone

[ ] Not too too sure about how we integrate metEAUdata and the data model of this project. We need a proper example of:
    [ ] meteaudata Signal processing. Say gap-filling + smoothing
        [ ] time-bounded
        [ ] ongoing
    [ ] metEAUdata Dataset processing, say, gap-filling+smoothing of 3 channels (signals) creation of PC1 and PC2 channels (signals) from that
        [ ] time-bounded
        [ ] ongoing
One thing that seems missing from the data model to represent this correctly is time boundaries in DatasetChannel, but that probably is not the only thing.

[ ] Owner field in the Equipment Table should not be free text. Should probably point to an Oraganisation Table and be renamed OwningOrganizationID. The Persons table and the Lab table should also probably have links to that Org table (replacing/renaming Company field).

[ ] Do we have a view where the Equipment events can be visualized? It would be great if we had a view where we could see a campaign (or an org, or a site or sampling locations)'s equipments, check one and see the time series of their raw data channels, with annotations for each event. The interface would allow the user to add events by creating a time selection on the graph (lime in the data explorer). Or is that already functionally taken care of in the explorer tab? To be checked.

[ ] I don't like this:
[ ] name: EventDateTimeEnd
      logical_type: timestamp
      precision: 7
      nullable: true
      description: "Date and time the event ended (UTC). NULL if instantaneous or ongoing."

How can we model ongoing event differently from instantaneous events?

[ ]     name: PerformedByPerson_ID
      logical_type: integer
      nullable: true
      description: "Person who performed or recorded the event"
      foreign_key:
        table: Person
        column: Person_ID
PerformedBy and RecordedBy should be different fields

[ ] The campaignID should not be recorded here. The campaign already registers the equipment, so in principle, all equipment events that span the campaign duration should be related to the campaign. Plus, campaigns can overlap and use the same equipment at the same time, causing ambiguities.

-EquipmentEventKind should not have validation in its controlled dictionary, it's too ambiguous. What happens physically to the sensor during validation? Nothing. DAta points collected to help validate/calibrate the sensor are already collected as lab data.

[ ] Would be great to add to the Watershed table a field to allow storage of the watershed's geographical data (maybe storing a geojson with WSG84 coordinates). The interface could visualize it on a map with sites (maybe even allow editing of the shape in the future?)

[ ] Watersheds should be able to have parent watersheds (subcatchement-catchemtn relationships)

[ ] In Observation, the DataType field should be a reference to ValueKind, not free text.

[ ] In Parameter, the dictionary entries have a manuel_units field, which is not present in the table definition. It should be removed. The units table stores the units, not the parameters table! Unless you can explain to me why it's needed

[ ] In Person, Function is too easy to confuse with Role. Should be renamed AssignedFunctions (plural).

[ ] ProcedureType should be renamed ProcedureKind and become a controlled dictionary
    [ ] Maintenance and Cleaning Protocol
    [ ] Calibration Protocol
    [ ] Validation Protocol
    [ ] Laboratory Method Protocol
    [ ] Software Manual

[ ] Is procvessingLineage going to work well if two users at different times use a channel in different workflows?

[ ] Channel: I think ProcessingKind should NOT be part of the channel identity. Many users will process a channel to the same level in different ways, leading to identity collisions in the channel table. Insead, the linkage should be with ProcessingLineage. That way, if Channel A is brought to "Validated" Processing Kind level once by a student in 2025 and another time by another student in 2026, the lineages are different so the channels don't collide but both stay "Validated".
    [ ] ProcessingKind becomes the controlled dictionary for processing step kinds. Should match the processing type enum of metEAUdata. That means ProcessingType in ProcessingStep becomes a reference to ProcessingKind

[ ] Parameters in ProcessingStep becomes MethodParameters to avoid confusion with Parameters table.

[ ] QualityCode should be renamed to reflect its scope (LabQualityCode)

[ ] SamplingPoint and SamplingLocation are redundant. Only keep SamplingPoint.

[ ] In SignalInterface, Make should be renamed Manufacturer

[ ] SignalInterfaceKind (and its reference in SignalInterface) should be removed. Too obtuse.

[ ] SignalInterfacePortKind should be removed too. Wayy too obtuse

[ ] Urban Characteristics should be renamed LandUse.

[ ] ValueMatrix should either be either refactored to allow for multi-dimensional data or renamed ValueMatrix2D and then more and more tables be created for other dimensionalities.
