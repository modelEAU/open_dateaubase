"""Unit tests for the Pydantic row models after the Stream/OperationKind refactor (Slice 8).

The schema YAML was refactored across Slices 1-7 (Stream supertype, Channel and
AnalysisSeries as shared-PK subtypes, ProcessingKind -> OperationKind, ChannelTrait
junction, single Stream_ID FK on Annotation/ProcessingLineage, LabAnalysis review
columns). Slice 8 brings the ``table_models`` Pydantic models in line with that
schema. These tests pin the new model shapes (and the removal of the old ones).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import open_dateaubase.data_model.table_models as tm


class TestNewLookupAndSupertypeModels:
    def test_stream_models_exist(self):
        # Supertype Stream: Stream_ID PK + StreamKind_ID discriminator FK.
        stream = tm.Stream(Stream_ID=1, StreamKind_ID=2)
        assert stream.streamID == 1
        assert stream.streamkindID == 2

    def test_stream_kind_lookup_exists(self):
        kind = tm.StreamKind(StreamKind_ID=1, Name="Sensor", Description=None)
        assert kind.streamkindID == 1
        assert kind.name == "Sensor"

    def test_operation_kind_lookup_exists(self):
        op = tm.OperationKind(
            OperationKind_ID=2, Name="OutlierRemoval", Description=None
        )
        assert op.operationkindID == 2
        assert op.name == "OutlierRemoval"

    def test_channel_trait_junction_exists(self):
        trait = tm.ChannelTrait(Stream_ID=10, OperationKind_ID=5)
        assert trait.streamID == 10
        assert trait.operationkindID == 5

    def test_review_status_lookup_exists(self):
        rs = tm.ReviewStatus(ReviewStatus_ID=1, Name="Pending", Description=None)
        assert rs.reviewstatusID == 1
        assert rs.name == "Pending"

    def test_processing_kind_model_is_gone(self):
        # The retired ProcessingKind lookup must not have a model anymore.
        assert not hasattr(tm, "ProcessingKind")


class TestChannelModel:
    def test_channel_pk_is_stream_id(self):
        # The Channel PK is now Stream_ID (shared-PK TPT subtype of Stream).
        assert "streamID" in tm.Channel.model_fields
        assert tm.Channel.model_fields["streamID"].alias == "Stream_ID"

    def test_channel_has_no_channel_id_field(self):
        assert "channelID" not in tm.Channel.model_fields
        assert "Channel_ID" not in tm.Channel.model_fields


class TestAnalysisSeriesModel:
    def test_analysis_series_pk_is_stream_id(self):
        series = tm.AnalysisSeries(
            Stream_ID=42,
            Name="TSS Gravimetric",
            Parameter_ID=1,
            SamplingPoint_ID=1,
            Unit_ID=1,
        )
        assert series.streamID == 42

    def test_analysis_series_has_no_processing_kind(self):
        assert "processingkindID" not in tm.AnalysisSeries.model_fields
        assert "ProcessingKind_ID" not in tm.AnalysisSeries.model_fields


class TestAnnotationModel:
    def test_annotation_uses_stream_id(self):
        assert "streamID" in tm.Annotation.model_fields
        assert tm.Annotation.model_fields["streamID"].alias == "Stream_ID"

    def test_annotation_dropped_channel_and_analysis_series(self):
        assert "channelID" not in tm.Annotation.model_fields
        assert "analysisseriesID" not in tm.Annotation.model_fields


class TestProcessingStepModel:
    def test_processing_step_uses_operation_kind(self):
        assert "operationkindID" in tm.ProcessingStep.model_fields
        assert (
            tm.ProcessingStep.model_fields["operationkindID"].alias
            == "OperationKind_ID"
        )

    def test_processing_step_dropped_processing_kind(self):
        assert "processingkindid" not in tm.ProcessingStep.model_fields
        assert "ProcessingKind_ID" not in tm.ProcessingStep.model_fields


class TestProcessingLineageModel:
    def test_processing_lineage_input_edge_is_stream_id(self):
        assert "streamID" in tm.ProcessingLineage.model_fields
        assert (
            tm.ProcessingLineage.model_fields["streamID"].alias == "Stream_ID"
        )
        assert "channelID" not in tm.ProcessingLineage.model_fields


class TestLabAnalysisModel:
    def test_lab_analysis_has_review_fields(self):
        fields = tm.LabAnalysis.model_fields
        assert "reviewstatusID" in fields
        assert "reviewedbypersonID" in fields
        assert "reviewdatetime" in fields

    def test_lab_analysis_review_status_defaults_to_pending(self):
        analysis = tm.LabAnalysis(
            LabAnalysis_ID=1,
            LabExperiment_ID=1,
            AnalysisSeries_ID=1,
            Sample_ID=1,
        )
        assert analysis.reviewstatusID == 1
        assert analysis.reviewedbypersonID is None
        assert analysis.reviewdatetime is None
