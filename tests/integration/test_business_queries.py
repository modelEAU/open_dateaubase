"""Business query tests — the living proof behind docs/reference/sample_data.md.

Every test here corresponds to a named query (BQ-xx) or integrity check (IC-xx)
in the documentation. If a migration silently breaks a business capability, one
of these tests will fail with a clear message.

All tests use the `db_at_v110` fixture (fully-migrated database with all seed
data). Tests for queries that only need v1.0.2 data still work against v1.1.0
because the seed data is additive.

Run with:
    uv run pytest tests/integration/test_business_queries.py -m db -v
"""

import pytest

from .conftest import get_table_row_count

pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _query(conn, sql: str, *params) -> list[tuple]:
    """Run a SELECT and return all rows."""
    cursor = conn.cursor()
    cursor.execute(sql, *params)
    return cursor.fetchall()


def _scalar(conn, sql: str, *params):
    """Run a SELECT that returns a single value."""
    rows = _query(conn, sql, *params)
    assert len(rows) == 1, f"Expected 1 row, got {len(rows)}"
    return rows[0][0]


# ---------------------------------------------------------------------------
# BQ-01  All TSS measurements at WWTP-IN-01
# ---------------------------------------------------------------------------


class TestBQ01AllTSSAtWWTPInlet:
    """BQ-01: What are all TSS measurements at WWTP-IN-01?"""

    SQL = """
        SELECT v.[Value_ID], v.[Value], v.[Timestamp]
        FROM [dbo].[Value] v
        JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
        JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]     = p.[Parameter_ID]
        JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID]= sp.[Sampling_point_ID]
        WHERE p.[Parameter]       = 'TSS'
          AND sp.[Sampling_point] = 'WWTP-IN-01'
        ORDER BY v.[Timestamp]
    """

    def test_returns_six_rows(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 6, f"Expected 6 TSS rows at WWTP-IN-01, got {len(rows)}"

    def test_values_include_known_measurements(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        values = {row[0]: row[1] for row in rows}  # {Value_ID: Value}
        assert values[1] == pytest.approx(185.0)
        assert values[2] == pytest.approx(210.5)
        assert values[3] == pytest.approx(192.3)
        assert values[18] == pytest.approx(200.0)
        assert values[19] == pytest.approx(145.2)
        assert values[20] == pytest.approx(160.8)

    def test_null_timestamp_row_is_present(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        null_ts_rows = [r for r in rows if r[2] is None]
        assert len(null_ts_rows) == 1, "Expected exactly one NULL-timestamp row"


# ---------------------------------------------------------------------------
# BQ-02  TSS at WWTP-IN-01 in January 2024
# ---------------------------------------------------------------------------


class TestBQ02TSSDateRange:
    """BQ-02: Filter TSS measurements at WWTP-IN-01 to January 2024."""

    SQL = """
        SELECT v.[Value_ID], v.[Value]
        FROM [dbo].[Value] v
        JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
        JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]     = p.[Parameter_ID]
        JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID]= sp.[Sampling_point_ID]
        WHERE p.[Parameter]       = 'TSS'
          AND sp.[Sampling_point] = 'WWTP-IN-01'
          AND v.[Timestamp] >= '2024-01-15T00:00:00.0000000+00:00'
          AND v.[Timestamp] <  '2024-01-17T00:00:00.0000000+00:00'
        ORDER BY v.[Timestamp]
    """

    def test_returns_three_rows(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 3

    def test_values_are_correct(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        values = [row[1] for row in rows]
        assert values[0] == pytest.approx(185.0)
        assert values[1] == pytest.approx(210.5)
        assert values[2] == pytest.approx(192.3)


# ---------------------------------------------------------------------------
# BQ-03  Average TSS per sampling point
# ---------------------------------------------------------------------------


class TestBQ03AverageTSSPerLocation:
    """BQ-03: Average TSS concentration grouped by sampling point."""

    SQL = """
        SELECT sp.[Sampling_point], AVG(v.[Value]) AS avg_tss, COUNT(v.[Value_ID]) AS n
        FROM [dbo].[Value] v
        JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
        JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]     = p.[Parameter_ID]
        JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID]= sp.[Sampling_point_ID]
        WHERE p.[Parameter] = 'TSS'
        GROUP BY sp.[Sampling_point]
        ORDER BY sp.[Sampling_point]
    """

    def test_three_sampling_points_have_tss(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 3
        locations = [r[0] for r in rows]
        assert "CSO-12-OUT" in locations
        assert "WWTP-IN-01" in locations
        assert "WWTP-OUT-01" in locations

    def test_wwtp_inlet_average_and_count(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        inlet = next(r for r in rows if r[0] == "WWTP-IN-01")
        # avg of 185.0, 210.5, 192.3, 200.0, 145.2, 160.8 = 1093.8 / 6 ≈ 182.3
        assert inlet[1] == pytest.approx(182.3, abs=0.1)
        assert inlet[2] == 6

    def test_wwtp_effluent_average_and_count(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        effluent = next(r for r in rows if r[0] == "WWTP-OUT-01")
        # avg of 12.5, 15.0 = 13.75
        assert effluent[1] == pytest.approx(13.75)
        assert effluent[2] == 2

    def test_cso_count(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        cso = next(r for r in rows if r[0] == "CSO-12-OUT")
        assert cso[2] == 3


# ---------------------------------------------------------------------------
# BQ-04  Equipment capable of measuring TSS
# ---------------------------------------------------------------------------


class TestBQ04EquipmentForTSS:
    """BQ-04: Which equipment models can measure TSS?"""

    SQL = """
        SELECT DISTINCT e.[identifier], em.[Equipment_model]
        FROM [dbo].[Equipment]                  e
        JOIN [dbo].[EquipmentModel]             em  ON e.[model_ID]           = em.[Equipment_model_ID]
        JOIN [dbo].[EquipmentModelHasParameter] ehp ON em.[Equipment_model_ID]= ehp.[Equipment_model_ID]
        JOIN [dbo].[Parameter]                  p   ON ehp.[Parameter_ID]     = p.[Parameter_ID]
        WHERE p.[Parameter] = 'TSS'
        ORDER BY e.[identifier]
    """

    def test_only_isco_can_measure_tss(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 1
        assert rows[0][0] == "ISCO-001"
        assert rows[0][1] == "ISCO 6712"


# ---------------------------------------------------------------------------
# BQ-05  All parameters per equipment model
# ---------------------------------------------------------------------------


class TestBQ05ParametersPerEquipmentModel:
    """BQ-05: What can each equipment model measure?"""

    SQL = """
        SELECT em.[Equipment_model], p.[Parameter]
        FROM [dbo].[EquipmentModel]             em
        JOIN [dbo].[EquipmentModelHasParameter] ehp ON em.[Equipment_model_ID]= ehp.[Equipment_model_ID]
        JOIN [dbo].[Parameter]                  p   ON ehp.[Parameter_ID]     = p.[Parameter_ID]
        ORDER BY em.[Equipment_model], p.[Parameter]
    """

    def test_five_capability_records(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 5

    def test_isco_measures_cod_and_tss(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        isco = [(r[0], r[1]) for r in rows if r[0] == "ISCO 6712"]
        params = {r[1] for r in isco}
        assert params == {"COD", "TSS"}

    def test_ysi_measures_three_params(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        ysi = [(r[0], r[1]) for r in rows if r[0] == "YSI ProDSS"]
        params = {r[1] for r in ysi}
        assert params == {"Conductivity", "pH", "Temperature"}


# ---------------------------------------------------------------------------
# BQ-06  Equipment deployment history
# ---------------------------------------------------------------------------


class TestBQ06EquipmentDeploymentHistory:
    """BQ-06: Where has ISCO-001 been deployed (which projects)?"""

    SQL = """
        SELECT e.[identifier], p.[name] AS project
        FROM [dbo].[Equipment]           e
        JOIN [dbo].[ProjectHasEquipment] phe ON e.[Equipment_ID] = phe.[Equipment_ID]
        JOIN [dbo].[Project]             p   ON phe.[Project_ID] = p.[Project_ID]
        ORDER BY e.[identifier], p.[name]
    """

    def test_isco_deployed_in_two_projects(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        isco = [r[1] for r in rows if r[0] == "ISCO-001"]
        assert len(isco) == 2
        assert "CSO Event Study 2024" in isco
        assert "WWTP Inlet Monitoring 2024" in isco

    def test_total_deployments(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 4  # ISCO×2, YSI×1, HACH×1


# ---------------------------------------------------------------------------
# BQ-07  Sampling points in a project
# ---------------------------------------------------------------------------


class TestBQ07SamplingPointsInProject:
    """BQ-07: What sampling points exist in the WWTP Inlet Monitoring 2024 project?"""

    SQL = """
        SELECT sp.[Sampling_point], s.[name] AS site
        FROM [dbo].[SamplingPoints]           sp
        JOIN [dbo].[ProjectHasSamplingPoints] phs ON sp.[Sampling_point_ID]= phs.[Sampling_point_ID]
        JOIN [dbo].[Project]                  p   ON phs.[Project_ID]       = p.[Project_ID]
        JOIN [dbo].[Site]                     s   ON sp.[Site_ID]           = s.[Site_ID]
        WHERE p.[name] = 'WWTP Inlet Monitoring 2024'
        ORDER BY sp.[Sampling_point]
    """

    def test_two_sampling_points(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 2
        names = [r[0] for r in rows]
        assert "WWTP-IN-01" in names
        assert "WWTP-OUT-01" in names


# ---------------------------------------------------------------------------
# BQ-08  Measurement counts per parameter and sampling point in a watershed
# ---------------------------------------------------------------------------


class TestBQ08MeasurementCountsPerWatershed:
    """BQ-08: Measurement counts per parameter × sampling point in Saint-Charles watershed."""

    SQL = """
        SELECT p.[Parameter], sp.[Sampling_point], COUNT(v.[Value_ID]) AS n
        FROM [dbo].[Value] v
        JOIN [dbo].[MetaData]       m  ON v.[Metadata_ID]      = m.[Metadata_ID]
        JOIN [dbo].[Parameter]      p  ON m.[Parameter_ID]     = p.[Parameter_ID]
        JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID]= sp.[Sampling_point_ID]
        JOIN [dbo].[Site]           s  ON sp.[Site_ID]         = s.[Site_ID]
        JOIN [dbo].[Watershed]      w  ON s.[Watershed_ID]     = w.[Watershed_ID]
        WHERE w.[name] = 'Riviere Saint-Charles'
        GROUP BY p.[Parameter], sp.[Sampling_point]
        ORDER BY p.[Parameter], sp.[Sampling_point]
    """

    def test_six_parameter_location_combinations(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 6

    def test_tss_inlet_count(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        row = next(r for r in rows if r[0] == "TSS" and r[1] == "WWTP-IN-01")
        assert row[2] == 6  # 3 from v1.0.0 + 1 NULL-ts + 2 from v1.0.2

    def test_cod_count(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        row = next(r for r in rows if r[0] == "COD")
        assert row[2] == 3  # 2 from v1.0.0 + 1 from v1.0.2

    def test_ph_count(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        row = next(r for r in rows if r[0] == "pH")
        assert row[2] == 5  # 4 from v1.0.0 + 1 from v1.0.2


# ---------------------------------------------------------------------------
# BQ-09  Contacts in a project
# ---------------------------------------------------------------------------


class TestBQ09ContactsInProject:
    """BQ-09: Who is responsible for data in the CSO Event Study?"""

    SQL = """
        SELECT c.[First_name], c.[Last_name]
        FROM [dbo].[Contact]           c
        JOIN [dbo].[ProjectHasContact] phc ON c.[Contact_ID]  = phc.[Contact_ID]
        JOIN [dbo].[Project]           p   ON phc.[Project_ID] = p.[Project_ID]
        WHERE p.[name] = 'CSO Event Study 2024'
        ORDER BY c.[Last_name]
    """

    def test_one_contact_in_cso_project(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 1
        assert rows[0][0] == "Pierre"
        assert rows[0][1] == "Gagnon"


# ---------------------------------------------------------------------------
# BQ-10  Measurements with QA/QC comments
# ---------------------------------------------------------------------------


class TestBQ10MeasurementsWithComments:
    """BQ-10: Which measurements carry a QA/QC annotation?"""

    SQL = """
        SELECT v.[Value_ID], c.[Comment]
        FROM [dbo].[Value]    v
        JOIN [dbo].[Comments] c ON v.[Comment_ID] = c.[Comment_ID]
        WHERE c.[Comment] IS NOT NULL
        ORDER BY v.[Value_ID]
    """

    def test_four_annotated_rows(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 4

    def test_drift_flag_on_value_9(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        row = next(r for r in rows if r[0] == 9)
        assert "drift" in row[1].lower()

    def test_duplicate_flag_on_value_12(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        row = next(r for r in rows if r[0] == 12)
        assert "duplicate" in row[1].lower() or "qa" in row[1].lower()


# ---------------------------------------------------------------------------
# BQ-11  Duplicate measurements at same timestamp
# ---------------------------------------------------------------------------


class TestBQ11DuplicateTimestamps:
    """BQ-11: Are there duplicate measurements at the same location and timestamp?"""

    SQL = """
        SELECT m.[Metadata_ID], v.[Timestamp], COUNT(*) AS n
        FROM [dbo].[Value] v
        JOIN [dbo].[MetaData] m ON v.[Metadata_ID] = m.[Metadata_ID]
        WHERE v.[Timestamp] IS NOT NULL
        GROUP BY m.[Metadata_ID], v.[Timestamp]
        HAVING COUNT(*) > 1
    """

    def test_exactly_one_duplicate_group(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 1

    def test_duplicate_is_at_cso_metadata(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert rows[0][0] == 4   # Metadata_ID=4 (TSS, CSO during rain)
        assert rows[0][2] == 2   # exactly 2 rows at that timestamp


# ---------------------------------------------------------------------------
# BQ-12  MetaData completeness audit
# ---------------------------------------------------------------------------


class TestBQ12MetaDataCompleteness:
    """BQ-12: Which MetaData entries are missing key context?"""

    SQL = """
        SELECT
            m.[Metadata_ID],
            CASE WHEN m.[Contact_ID]   IS NULL THEN 1 ELSE 0 END AS no_contact,
            CASE WHEN m.[Equipment_ID] IS NULL THEN 1 ELSE 0 END AS no_equipment,
            CASE WHEN m.[Condition_ID] IS NULL THEN 1 ELSE 0 END AS no_weather
        FROM [dbo].[MetaData] m
        WHERE m.[Contact_ID] IS NULL
           OR m.[Equipment_ID] IS NULL
           OR m.[Condition_ID] IS NULL
        ORDER BY m.[Metadata_ID]
    """

    def test_six_incomplete_metadata_rows(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 6

    def test_metadata_3_missing_only_weather(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        row = next(r for r in rows if r[0] == 3)
        assert row[1] == 0  # contact ok
        assert row[2] == 0  # equipment ok
        assert row[3] == 1  # weather missing

    def test_metadata_5_missing_contact_and_equipment(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        row = next(r for r in rows if r[0] == 5)
        assert row[1] == 1  # contact missing
        assert row[2] == 1  # equipment missing

    def test_polymorphic_metadata_missing_only_equipment(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        poly_ids = {r[0] for r in rows if r[0] in (7, 8, 9, 10)}
        assert poly_ids == {7, 8, 9, 10}
        for row in rows:
            if row[0] in (7, 8, 9, 10):
                assert row[1] == 0   # contact ok
                assert row[2] == 1   # equipment missing (expected for vector/image/matrix)


# ---------------------------------------------------------------------------
# BQ-13  Value types per sampling point (v1.1.0)
# ---------------------------------------------------------------------------


class TestBQ13ValueTypesPerLocation:
    """BQ-13: What kinds of data (Scalar, Vector, Matrix, Image) exist per location?"""

    SQL = """
        SELECT sp.[Sampling_point], vt.[ValueType_Name], COUNT(*) AS n
        FROM [dbo].[MetaData]       m
        JOIN [dbo].[SamplingPoints] sp ON m.[Sampling_point_ID] = sp.[Sampling_point_ID]
        JOIN [dbo].[ValueType]      vt ON m.[ValueType_ID]      = vt.[ValueType_ID]
        WHERE m.[Sampling_point_ID] IS NOT NULL
        GROUP BY sp.[Sampling_point], vt.[ValueType_Name]
        ORDER BY sp.[Sampling_point], vt.[ValueType_Name]
    """

    def test_six_location_type_combinations(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        # WWTP-IN-01: Scalar(4), Vector(2), Matrix(1) = 3 combos
        # CSO-12-OUT: Scalar(1), Image(1) = 2 combos
        # WWTP-OUT-01: Scalar(2) = 1 combo
        assert len(rows) == 6

    def test_wwtp_inlet_has_scalar_vector_matrix(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        inlet = {r[1]: r[2] for r in rows if r[0] == "WWTP-IN-01"}
        assert inlet["Scalar"] == 4
        assert inlet["Vector"] == 2   # UV-Vis + PSD
        assert inlet["Matrix"] == 1

    def test_cso_has_scalar_and_image(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        cso = {r[1]: r[2] for r in rows if r[0] == "CSO-12-OUT"}
        assert cso["Scalar"] == 1
        assert cso["Image"] == 1


# ---------------------------------------------------------------------------
# BQ-14  UV-Vis spectrum at a specific timestamp (v1.1.0)
# ---------------------------------------------------------------------------


class TestBQ14UVVisSpectrum:
    """BQ-14: Full UV-Vis spectrum at WWTP-IN-01 at the morning timestamp."""

    SQL = """
        SELECT vb.[BinIndex], vb.[LowerBound], vb.[UpperBound], vv.[Value], vv.[QualityCode]
        FROM [dbo].[ValueVector] vv
        JOIN [dbo].[ValueBin]    vb ON vv.[ValueBin_ID] = vb.[ValueBin_ID]
        WHERE vv.[Metadata_ID] = 7
          AND vv.[Timestamp]   = '2025-09-10T10:00:00.0000000-04:00'
        ORDER BY vb.[BinIndex]
    """

    def test_seven_bins_at_morning_timestamp(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 7

    def test_first_bin_bounds_and_absorbance(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        first = rows[0]
        assert first[0] == 0                        # BinIndex
        assert first[1] == pytest.approx(197.5)     # LowerBound (nm)
        assert first[2] == pytest.approx(202.5)     # UpperBound (nm)
        assert first[3] == pytest.approx(2.85)      # absorbance value

    def test_all_bins_have_no_quality_flag(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert all(r[4] is None for r in rows)

    def test_afternoon_spectrum_has_three_bins_and_one_flag(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(
            conn,
            """
            SELECT vb.[BinIndex], vv.[Value], vv.[QualityCode]
            FROM [dbo].[ValueVector] vv
            JOIN [dbo].[ValueBin]    vb ON vv.[ValueBin_ID] = vb.[ValueBin_ID]
            WHERE vv.[Metadata_ID] = 7
              AND vv.[Timestamp]   = '2025-09-10T14:00:00.0000000-04:00'
            ORDER BY vb.[BinIndex]
            """,
        )
        assert len(rows) == 3
        flagged = [r for r in rows if r[2] is not None]
        assert len(flagged) == 1
        assert flagged[0][2] == 1  # QualityCode = 1


# ---------------------------------------------------------------------------
# BQ-15  Total particle concentration per timestamp from PSD array (v1.1.0)
# ---------------------------------------------------------------------------


class TestBQ15ParticleSizeDistribution:
    """BQ-15: Total particle concentration (sum of all PSD fractions) per timestamp."""

    SQL = """
        SELECT vv.[Timestamp], SUM(vv.[Value]) AS total_mg_L, COUNT(*) AS n_fractions
        FROM [dbo].[ValueVector] vv
        WHERE vv.[Metadata_ID] = 9
        GROUP BY vv.[Timestamp]
        ORDER BY vv.[Timestamp]
    """

    def test_two_timestamps(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 2

    def test_each_timestamp_has_four_fractions(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert all(r[2] == 4 for r in rows)

    def test_morning_total_concentration(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        # 45.2 + 28.1 + 12.5 + 5.8 = 91.6
        morning = rows[0]
        assert morning[1] == pytest.approx(91.6, abs=0.01)

    def test_afternoon_total_concentration(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        # 52.0 + 33.4 + 15.1 + 7.2 = 107.7
        afternoon = rows[1]
        assert afternoon[1] == pytest.approx(107.7, abs=0.01)


# ---------------------------------------------------------------------------
# BQ-16  Particle size-velocity joint distribution (v1.1.0)
# ---------------------------------------------------------------------------


class TestBQ16ParticleSizeVelocityMatrix:
    """BQ-16: Joint size-velocity distribution for MetaData ID=10 at the morning timestamp."""

    SQL = """
        SELECT rb.[BinIndex]                               AS size_bin_index,
               cb.[BinIndex]                               AS vel_bin_index,
               rb.[LowerBound]                             AS size_lower_um,
               rb.[UpperBound]                             AS size_upper_um,
               cb.[LowerBound]                             AS vel_lower_ms,
               cb.[UpperBound]                             AS vel_upper_ms,
               vm.[Value],
               vm.[QualityCode]
        FROM [dbo].[ValueMatrix] vm
        JOIN [dbo].[ValueBin]    rb ON vm.[RowValueBin_ID] = rb.[ValueBin_ID]
        JOIN [dbo].[ValueBin]    cb ON vm.[ColValueBin_ID] = cb.[ValueBin_ID]
        WHERE vm.[Metadata_ID] = 10
          AND vm.[Timestamp]   = '2025-09-10T09:00:00.0000000-04:00'
        ORDER BY rb.[BinIndex], cb.[BinIndex]
    """

    def test_six_cells_at_morning_timestamp(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert len(rows) == 6  # 3 size bins x 2 velocity bins

    def test_smallest_size_slow_velocity_cell(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        # First cell: size bin 0 (<63 µm), velocity bin 0 (slow)
        first = rows[0]
        assert first[0] == 0                    # size_bin_index
        assert first[1] == 0                    # vel_bin_index
        assert first[2] == pytest.approx(0.0)   # size lower bound
        assert first[3] == pytest.approx(63.0)  # size upper bound
        assert first[6] == pytest.approx(22.1)  # count/mL

    def test_all_cells_have_no_quality_flag(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(conn, self.SQL)
        assert all(r[7] is None for r in rows)


# ---------------------------------------------------------------------------
# IC-01  Watersheds without hydrological characteristics
# ---------------------------------------------------------------------------


class TestIC01HydrologicalCharacteristics:
    """IC-01: Every watershed must have exactly one HydrologicalCharacteristics row."""

    def test_no_watershed_missing_hydro_data(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(
            conn,
            """
            SELECT w.[name]
            FROM [dbo].[Watershed] w
            LEFT JOIN [dbo].[HydrologicalCharacteristics] hc ON w.[Watershed_ID] = hc.[Watershed_ID]
            WHERE hc.[Watershed_ID] IS NULL
            """,
        )
        assert len(rows) == 0, f"Watersheds missing hydro data: {[r[0] for r in rows]}"

    def test_no_watershed_missing_urban_data(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(
            conn,
            """
            SELECT w.[name]
            FROM [dbo].[Watershed] w
            LEFT JOIN [dbo].[UrbanCharacteristics] uc ON w.[Watershed_ID] = uc.[Watershed_ID]
            WHERE uc.[Watershed_ID] IS NULL
            """,
        )
        assert len(rows) == 0, f"Watersheds missing urban data: {[r[0] for r in rows]}"


# ---------------------------------------------------------------------------
# IC-03  pH values within physical range 0–14
# ---------------------------------------------------------------------------


class TestIC03PHRange:
    """IC-03: All pH values must fall within 0–14."""

    def test_no_out_of_range_ph_values(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(
            conn,
            """
            SELECT v.[Value_ID], v.[Value]
            FROM [dbo].[Value] v
            JOIN [dbo].[MetaData]  m ON v.[Metadata_ID]  = m.[Metadata_ID]
            JOIN [dbo].[Parameter] p ON m.[Parameter_ID] = p.[Parameter_ID]
            WHERE p.[Parameter] = 'pH'
              AND v.[Value] IS NOT NULL
              AND (v.[Value] < 0 OR v.[Value] > 14)
            """,
        )
        assert len(rows) == 0, f"Out-of-range pH values: {rows}"

    def test_all_ph_values_are_realistic(self, db_at_v110):
        """All pH values should also be in a realistic wastewater range (5–10)."""
        conn, _ = db_at_v110
        rows = _query(
            conn,
            """
            SELECT v.[Value]
            FROM [dbo].[Value] v
            JOIN [dbo].[MetaData]  m ON v.[Metadata_ID]  = m.[Metadata_ID]
            JOIN [dbo].[Parameter] p ON m.[Parameter_ID] = p.[Parameter_ID]
            WHERE p.[Parameter] = 'pH'
              AND v.[Value] IS NOT NULL
            """,
        )
        for (val,) in rows:
            assert 5.0 <= val <= 10.0, f"Unexpected pH value: {val}"


# ---------------------------------------------------------------------------
# IC-04  Unit consistency — MetaData unit matches Parameter default unit
# ---------------------------------------------------------------------------


class TestIC04UnitConsistency:
    """IC-04: The unit in MetaData must match the default unit of the Parameter."""

    def test_no_unit_mismatches(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(
            conn,
            """
            SELECT v.[Value_ID], p.[Parameter], pu.[Unit] AS param_unit, mu.[Unit] AS meta_unit
            FROM [dbo].[Value] v
            JOIN [dbo].[MetaData]  m  ON v.[Metadata_ID]  = m.[Metadata_ID]
            JOIN [dbo].[Parameter] p  ON m.[Parameter_ID] = p.[Parameter_ID]
            JOIN [dbo].[Unit]      pu ON p.[Unit_ID]      = pu.[Unit_ID]
            JOIN [dbo].[Unit]      mu ON m.[Unit_ID]      = mu.[Unit_ID]
            WHERE m.[Parameter_ID] IS NOT NULL
              AND m.[Unit_ID]      IS NOT NULL
              AND p.[Unit_ID]     != m.[Unit_ID]
            """,
        )
        assert len(rows) == 0, (
            f"Unit mismatches between Parameter and MetaData: {rows}"
        )


# ---------------------------------------------------------------------------
# IC-05  Equipment in MetaData registered to same project
# ---------------------------------------------------------------------------


class TestIC05EquipmentProjectConsistency:
    """IC-05: Equipment referenced in MetaData must be registered to the same project."""

    def test_no_unregistered_equipment_in_metadata(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(
            conn,
            """
            SELECT m.[Metadata_ID], e.[identifier]
            FROM [dbo].[MetaData]  m
            JOIN [dbo].[Equipment] e ON m.[Equipment_ID] = e.[Equipment_ID]
            LEFT JOIN [dbo].[ProjectHasEquipment] phe
                ON  e.[Equipment_ID] = phe.[Equipment_ID]
                AND m.[Project_ID]   = phe.[Project_ID]
            WHERE m.[Equipment_ID] IS NOT NULL
              AND m.[Project_ID]   IS NOT NULL
              AND phe.[Equipment_ID] IS NULL
            """,
        )
        assert len(rows) == 0, (
            f"Equipment in MetaData not registered to project: {rows}"
        )


# ---------------------------------------------------------------------------
# IC-06  Spectrum MetaData must have a WavelengthAxis (v1.1.0)
# ---------------------------------------------------------------------------


class TestIC06VectorMatrixRequiresMetaDataAxis:
    """IC-06: Every Vector- or Matrix-type MetaData must have at least one MetaDataAxis row."""

    def test_no_vector_metadata_without_axis(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(
            conn,
            """
            SELECT m.[Metadata_ID]
            FROM [dbo].[MetaData]  m
            JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID]
            WHERE vt.[ValueType_Name] IN ('Vector', 'Matrix')
              AND NOT EXISTS (
                  SELECT 1 FROM [dbo].[MetaDataAxis] ma
                  WHERE ma.[Metadata_ID] = m.[Metadata_ID]
              )
            """,
        )
        assert len(rows) == 0, (
            f"Vector/Matrix MetaData missing MetaDataAxis entry: {[r[0] for r in rows]}"
        )


# ---------------------------------------------------------------------------
# IC-07  Scalar MetaData must not have data in polymorphic tables (v1.1.0)
# ---------------------------------------------------------------------------


class TestIC07ScalarMetaDataIsolation:
    """IC-07: Scalar MetaData must not have rows in ValueVector or ValueMatrix."""

    def test_no_scalar_metadata_in_value_vector(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(
            conn,
            """
            SELECT m.[Metadata_ID]
            FROM [dbo].[MetaData]  m
            JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID]
            WHERE vt.[ValueType_Name] = 'Scalar'
              AND EXISTS (
                  SELECT 1 FROM [dbo].[ValueVector] vv
                  WHERE vv.[Metadata_ID] = m.[Metadata_ID]
              )
            """,
        )
        assert len(rows) == 0

    def test_no_scalar_metadata_in_value_matrix(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(
            conn,
            """
            SELECT m.[Metadata_ID]
            FROM [dbo].[MetaData]  m
            JOIN [dbo].[ValueType] vt ON m.[ValueType_ID] = vt.[ValueType_ID]
            WHERE vt.[ValueType_Name] = 'Scalar'
              AND EXISTS (
                  SELECT 1 FROM [dbo].[ValueMatrix] vm
                  WHERE vm.[Metadata_ID] = m.[Metadata_ID]
              )
            """,
        )
        assert len(rows) == 0


# ---------------------------------------------------------------------------
# IC-08  No orphaned Value rows
# ---------------------------------------------------------------------------


class TestIC08OrphanedValues:
    """IC-08: Every Value row must reference an existing MetaData row."""

    def test_no_orphaned_value_rows(self, db_at_v110):
        conn, _ = db_at_v110
        rows = _query(
            conn,
            """
            SELECT v.[Value_ID]
            FROM [dbo].[Value] v
            LEFT JOIN [dbo].[MetaData] m ON v.[Metadata_ID] = m.[Metadata_ID]
            WHERE v.[Metadata_ID] IS NOT NULL
              AND m.[Metadata_ID] IS NULL
            """,
        )
        assert len(rows) == 0, f"Orphaned Value rows: {[r[0] for r in rows]}"
