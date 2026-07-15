"""Shared sentinel labels for dropdowns.

Two distinct meanings, two labels — never spell either one by hand:

* NONE_LABEL — the user picked no value (an optional FK stays unset).
* ALL_LABEL  — a filter is off, so every row passes.

Widgets own their sentinel row; callers pass only real options.
"""

from __future__ import annotations

NONE_LABEL = "— none —"
ALL_LABEL = "— all —"
