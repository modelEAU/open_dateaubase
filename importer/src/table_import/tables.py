from typing import List

import pandas as pd


class ValueTable(pd.DataFrame):
    acceptable_columns: List[str] = ["Timestamp", "Value"]

    def __init__(self, df: pd.DataFrame) -> None:
        if df is None:
            df = pd.DataFrame(data=[], columns=self.acceptable_columns)
        if sorted(list(df.columns)) != sorted(self.acceptable_columns):
            raise ValueError(
                f"ValueTable expects columns {self.acceptable_columns}, "
                f"got {sorted(df.columns.tolist())}"
            )
        super().__init__(df)
