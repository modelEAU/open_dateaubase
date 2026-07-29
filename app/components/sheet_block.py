"""Reading spreadsheets and cutting a table block out of a raw grid.

A *raw grid* is a worksheet read with ``header=None``: nothing is interpreted,
every row is present, including banners, help text and blanks. A *block* is
what the user pointed at — a header row, a first data row, and the columns in
between.

Pure: no Streamlit, no database.
"""

from __future__ import annotations

import datetime as dt
import re
from collections import Counter
from dataclasses import dataclass

import pandas as pd

# ponytail: a column counts as native-datetime when nearly all of its values
# are real datetimes — a handful of stray text cells is normal in a real sheet.
_NATIVE_DATETIME_SHARE = 0.9


def read_grids(source, filename: str) -> dict[str, pd.DataFrame]:
    """Return ``{sheet name: raw grid}`` for a CSV or Excel file."""
    if filename.lower().endswith(".csv"):
        return {"CSV": pd.read_csv(source, header=None, dtype=object)}
    return pd.read_excel(source, sheet_name=None, header=None)


def one_line(value) -> str:
    """Collapse a cell to a single line of text."""
    return re.sub(r"\s+", " ", str(value)).strip()


@dataclass(frozen=True)
class SheetBlock:
    """One table cut out of a raw grid.

    ``columns``, ``headers`` and ``banners`` are parallel. Everything is keyed
    by the **source column index**, never by header text: a sheet may repeat a
    header name several times and each occurrence stays independently
    addressable.
    """

    header_row: int
    data_start_row: int
    columns: tuple[int, ...]
    headers: tuple[str, ...]
    banners: tuple[tuple[str, ...], ...]
    data: pd.DataFrame  # column labels are source column indices, index is the source row
    datetime_columns: frozenset[int]

    def labels(self) -> list[str]:
        """Display labels, unique even when the sheet repeats a header name."""
        counts = Counter(self.headers)
        used: set[str] = set()
        out: list[str] = []
        for col, head, banner in zip(self.columns, self.headers, self.banners):
            label = head
            if counts[head] > 1 and banner:
                label = f"{head} · {banner[-1]}"
            if label in used:
                label = f"{label} [{col}]"
            used.add(label)
            out.append(label)
        return out

    def banner_path(self, column: int) -> str:
        """The banner context above one column, e.g. ``PCR › SARS-CoV-2 (N1)``."""
        return " › ".join(self.banners[self.columns.index(column)])


def extract_block(
    grid: pd.DataFrame,
    header_row: int,
    data_start_row: int,
    columns=None,
) -> SheetBlock:
    """Cut the block the user pointed at out of ``grid``.

    Rows between the header and the first data row — help text, type
    annotations, blanks — are skipped. Rows above the header are forward-filled
    and kept as per-column context.
    """
    if data_start_row <= header_row:
        raise ValueError("the first data row must be below the header row")
    cols = tuple(grid.columns if columns is None else columns)

    header_cells = grid.iloc[header_row]
    headers = tuple(
        one_line(header_cells[c]) if pd.notna(header_cells[c]) else f"Column {c}"
        for c in cols
    )

    above = grid.iloc[:header_row].ffill(axis=1)
    banners = tuple(
        tuple(one_line(v) for v in above[c] if pd.notna(v)) for c in cols
    )

    data = grid.iloc[data_start_row:].loc[:, list(cols)]
    return SheetBlock(
        header_row=header_row,
        data_start_row=data_start_row,
        columns=cols,
        headers=headers,
        banners=banners,
        data=data,
        datetime_columns=frozenset(c for c in cols if _is_native_datetime(data[c])),
    )


def _is_native_datetime(values: pd.Series) -> bool:
    present = values.dropna()
    if present.empty:
        return False
    hits = sum(isinstance(v, (pd.Timestamp, dt.datetime, dt.date)) for v in present)
    return hits / len(present) >= _NATIVE_DATETIME_SHARE
