# 5. ProcessingKind split into OperationKind, ChannelTrait, and LabAnalysis review columns

Date: 2026-06-11

## Status

Accepted.

## Context

`ProcessingKind` was a single lookup table serving three conflated roles:

1. **Step classifier** — on `ProcessingStep.ProcessingKind_ID`, it described what
   a processing step *does* (outlier removal, smoothing, …).
2. **Channel state shortcut** — the description in `Channel.yaml` says
   "ProcessingKind is not stored on Channel — query via ProducedByStep_ID →
   ProcessingStep.ProcessingKind_ID." This means a Channel that accumulated
   multiple cleaning operations (outlier removal *then* drift correction) had no
   way to express both traits simultaneously — the scalar FK only captured the
   last step.
3. **Lab series discriminator** — `AnalysisSeries.ProcessingKind_ID` was part of
   the identity uniqueness constraint, creating separate series for "raw" vs.
   "cleaned" lab data.

Problems:
- Multiple processing states can be simultaneously true on a Channel (outlier-free
  AND drift-corrected). A scalar FK cannot represent this.
- The vocabulary entries ("Free of outliers", "Free of drift") described
   *accumulated data state*, not the operation a step performs. These are
   different concepts.
- Review/approval status for lab data is a *per-measurement* concern, not a
  *per-series* concern. Using `ProcessingKind_ID` as a series discriminator put
  this at the wrong granularity level — a raw and a reviewed measurement of TSS
  at Effluent are the same series, just with different point-level statuses.
- Attempts to extend the vocabulary for "Predicted", "Derived", "Reconstituted",
  "Synthetic" fail because the epistemic boundary between these categories is not
  stable — the same channel can be simultaneously "smoothed" (operation) and
  "modelled" (provenance), and different data creators classify identically
  produced channels differently. The lineage DAG is the authoritative provenance
  record; vocabulary labels are a lossy summary.

## Decision

`ProcessingKind` is retired and replaced by three targeted mechanisms:

### 1. OperationKind (replaces ProcessingKind on ProcessingStep)

A renamed and restructured lookup table. Each `ProcessingStep` carries exactly
one `OperationKind_ID` — a step does exactly one type of operation.

Vocabulary (6 entries):

| ID | Name | Description |
|---|---|---|
| 1 | Unprocessed | No operations applied — used for raw channel trait only |
| 2 | OutlierRemoval | Spikes and statistical outliers removed or flagged |
| 3 | DriftCorrection | Sensor drift or baseline shift corrected |
| 4 | FaultRemoval | Instrument faults and implausible values removed |
| 5 | Smoothing | Noise reduced by a smoothing or averaging algorithm |
| 6 | Interpolation | Missing values filled by interpolation or reconstruction |

"Predicted" and "Derived" are retired. Derived channels are identified by
`ProducedByStep_ID IS NOT NULL`; their deeper provenance lives in the lineage DAG
and in `DataProvenanceKind`.

### 2. ChannelTrait junction table (new)

A many-to-many table `(Stream_ID FK → Stream, OperationKind_ID FK → OperationKind)`
that records the accumulated set of operations applied to a Channel across its
full lineage. Multiple traits can be simultaneously true (AND semantics), unlike
the former scalar FK.

**Population rule:** computed once at Channel creation by unioning the trait sets
of all input channels and adding the producing step's OperationKind. Raw sensor
channels receive a single `Unprocessed` trait. The trait set is immutable after
creation — Channels are immutable, so their trait set cannot change.

This is a denormalized fast-filter cache. The lineage DAG is authoritative; the
trait set is a deterministic projection of it.

### 3. Review columns on LabAnalysis (replaces series-level ProcessingKind)

`ProcessingKind_ID` is removed from `AnalysisSeries` entirely. The identity
uniqueness constraint simplifies to `(Parameter_ID, SamplingPoint_ID, ValueKind_ID)`.

All measurements of the same parameter at the same location share one
AnalysisSeries, regardless of review state. Review status is a point-level
attribute, parallel to `QualityCode_ID`:

- `ReviewStatus` — Pending / Approved / Rejected
- `ReviewedByPerson_ID FK → Person` — nullable; NULL means unreviewed
- `ReviewDateTime` — nullable timestamp of the review event

The `AuditLog` table captures historical changes if review status is amended.
A separate review table was considered but rejected: the lab workflow is
single-round, single-reviewer; corrections require a new `LabAnalysis` row
(new replicate), not amendment. Three columns provide all needed query
surface without an extra join.

## Consequences

- `ProcessingKind` table and all references to it are removed. `OperationKind`
  replaces it with renamed entries and a cleaner vocabulary.
- `AnalysisSeries` uniqueness constraint narrows from 4 columns to 3. Existing
  series that were differentiated only by `ProcessingKind_ID` must be merged or
  migrated before this change is deployed.
- The `ingestion_repository.find_or_create_derived_metadata` function gains
  responsibility for computing and writing the ChannelTrait set at Channel
  creation time.
- `load_signal_context` in `meteaudata_bridge.py` changes from returning a single
  `processing_kind_name` string to a list of trait names.
- Lab ingest forms lose the `processing_kind_id` dropdown for AnalysisSeries.
  They gain `ReviewStatus` controls on individual measurements.
- Filtering "show me only approved lab data" moves from a series-picker filter to
  an observation-level `WHERE ReviewStatus = 'Approved'` clause.

## Known limitation / future work

The initial implementation of the ChannelTrait population rule computes the trait
set from a **single** primary input (`find_or_create_derived_metadata(source_channel_id=…)`).
The rule as specified is the union over *all* inputs of a producing step. For
multi-input transforms (PCA, sensor fusion, lab-series-fed gap-filling), the
derived Channel's denormalized trait set is therefore under-populated — though the
`ProcessingLineage` DAG still records every input edge authoritatively, so no
provenance is lost (only the fast-filter cache is incomplete).

Closing this requires computing the trait union from `ProcessingLineage`
(`JOIN ChannelTrait` over all input `Stream_ID`s of the step) rather than from one
source channel. No schema change is needed — `ChannelTrait` already supports it.
This was deferred from the v2.0 stabilization because it touches the ingest API
contract and lineage-write ordering, not the schema.
