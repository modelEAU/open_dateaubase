"""Unit tests for humanize_id_columns (pure pandas, no Streamlit)."""

import pandas as pd

from app.components.id_format import humanize_id_columns


def test_fk_pair_merges_into_label_id():
    df = pd.DataFrame(
        {"campaign_id": [7], "campaign_kind_id": [1], "campaign_kind_name": ["Monitoring"]}
    )
    out = humanize_id_columns(df, pk_field="campaign_id")
    assert "campaign_kind_name" not in out.columns
    assert out["Campaign kind"].tolist() == ["Monitoring (1)"]


def test_exact_base_sibling_merges():
    df = pd.DataFrame({"unit_id": [3], "unit": ["mg/L"]})
    out = humanize_id_columns(df)  # unit_id is FK here (no pk_field)
    assert out["Unit"].tolist() == ["mg/L (3)"]
    assert "unit" not in out.columns


def test_pk_field_left_raw():
    df = pd.DataFrame({"campaign_id": [7], "site_id": [2], "site_name": ["Plant A"]})
    out = humanize_id_columns(df, pk_field="campaign_id")
    assert out["campaign_id"].tolist() == [7]  # untouched
    assert out["Site"].tolist() == ["Plant A (2)"]


def test_orphan_resolved_via_injected_resolver():
    df = pd.DataFrame({"signal_interface_id": [5], "das_id": [1]})
    out = humanize_id_columns(
        df, pk_field="signal_interface_id", resolvers={"das_id": {1: "DAS A"}}
    )
    assert out["Das"].tolist() == ["DAS A (1)"]


def test_orphan_without_resolver_left_raw():
    df = pd.DataFrame({"channel_id": [4], "annotation_id": [9]})
    out = humanize_id_columns(df, pk_field="annotation_id", resolvers={})
    assert out["channel_id"].tolist() == [4]  # no resolver, no sibling -> raw


def test_null_id_and_label_safe():
    df = pd.DataFrame({"site_id": [None, 2], "site_name": ["Orphan label", None]})
    out = humanize_id_columns(df)
    assert out["Site"].tolist() == ["Orphan label", "2"]


def test_original_df_not_mutated():
    df = pd.DataFrame({"site_id": [2], "site_name": ["Plant A"]})
    before = df.copy()
    humanize_id_columns(df)
    pd.testing.assert_frame_equal(df, before)
