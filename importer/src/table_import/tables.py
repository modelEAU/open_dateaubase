from typing import List

import pandas as pd


class WrongColumnsException(Exception):
    """Gets called when trying to create a dataframe meant for the Values table of the datEaubase if the dataframe has the wrong columns"""
    pass


class ValueTable(pd.DataFrame):
    acceptable_columns: List[str] = ['Value_ID', 'Value', 'Number_of_experiment', 'Metadata_ID', 'Comment_ID', 'Timestamp']

    def __init__(self, df: pd.DataFrame) -> None:
        if df is None:
            df = pd.DataFrame(data=[], columns=self.acceptable_columns)
        if sorted(list(df.columns)) != sorted(self.acceptable_columns):
            raise WrongColumnsException('Dataframe does not contain the correct columns to be accepted into the Values table')
        super().__init__(df)
