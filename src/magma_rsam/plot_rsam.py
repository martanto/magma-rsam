import pandas as pd
import matplotlib.pyplot as plt
import os
from .database import db, RsamCSV
from .validator import validate_dates
from typing import Dict, List, Self


class Plot:
    def __init__(self,
                 df: pd.DataFrame,
                 matrices: List[str] = ['mean', 'median'],
                 windows: List[str] = ['1d'],
                 datetime_interval: int = 3,):

        self.df = df
        self.matrices = matrices
        self.windows = windows
        self.datetime_interval = datetime_interval

        self.continuous_events: List[Dict[str, str | None | List[str]]] = []
        self.single_events: List[Dict[str, str]] = []

    def configure(self) -> Self:
        return self

    def add_continuous_events(self, continuous_events: List[Dict[str, str | None | List[str]]] = None) -> Self:
        """Add continuous events.

        Args:
            continuous_events (List[Dict[str, str | None | List[str]]]): Continuous events
                Example:
                continuous_events = [
                    {
                        'name': 'Eruption',
                        'dates': ['2024-04-16', '2024-04-16'],
                        'color': 'orange'
                    },
                    {
                        'name': 'Level II',
                        'dates': ['2024-04-16', '2024-04-18'],
                        'color': 'orange'
                    },
                    .....
                ]

        Returns:
            Self
        """
        self.continuous_events = self.continuous_events + continuous_events
        return self

    def add_single_events(self, single_events: List[Dict[str, str]] = None) -> Self:
        """Add single events.

        Args:
            single_events (List[Dict[str, str]]): Single events
                Example:
                    single_events = [
                        {
                            'name': 'Big Eruption',
                            'dates': '2024-04-16'
                        },
                        {
                            'name': 'Small Eruption',
                            'dates': '2024-04-16'
                        },
                    ]
        """
        self.single_events = self.single_events + single_events
        return self

    def plot(self,
             matrices: List[str] = ['mean', 'median'],
             windows: List[str] = ['1d'],
             datetime_interval: int = 3):

        df = self.df

        fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(12, 4),
                                layout="constrained", sharex=True)

        axs.set_ylabel('Amplitude (count)')

        axs.scatter(df.index, df['mean'], c='k', alpha=0.2, s=3, label='10 minutes')

        for matrix in matrices:
            color = 'red' if matrix == 'mean' else 'blue'
            for window in windows:
                _column_name = f"{matrix}_{window}"
                axs.plot(df.index, df[_column_name], c=color, label=_column_name, alpha=1, lw=2)


class PlotRsam:
    def __init__(self,
                 start_date: str,
                 end_date: str,
                 station: str,
                 channel: str,
                 network: str = 'VG',
                 location: str = '00',
                 resample: str = '10min'):

        validate_dates(start_date, end_date)
        self.start_date = start_date
        self.end_date = end_date
        self.station = station
        self.channel = channel
        self.network = network
        self.location = location
        self.resample = resample

        self.freq_min: float | None = None
        self.freq_max: float | None = None
        self.nslc = f"{network}.{station}.{location}.{channel}"

        rsam_dir: str = os.path.join(os.getcwd(), 'output', 'rsam')

        nslc = f"{network}.{station}.{location}.{channel}"

        filtered_dir: str = 'not_filtered'
        self.filtered_dir: str = os.path.join(rsam_dir, nslc, filtered_dir)
        self.rsam_dir: str = os.path.join(self.filtered_dir, resample)

        print(f"ℹ️ Start Date: {start_date}")
        print(f"ℹ️ End Date: {end_date}")
        print(f"ℹ️ Station: {station}")
        print(f"ℹ️ Channel: {channel}")
        print(f"ℹ️ Network: {network}")
        print(f"ℹ️ Location: {location}")
        print(f"ℹ️ Resample: {resample}")

        if not os.path.isdir(self.rsam_dir):
            raise NotADirectoryError(f"⛔ The directory {self.rsam_dir} does not exist!"
                                     f" Please run RSAM with the current parameters")

    def with_filter(self, freq_min: float, freq_max: float) -> Self:
        """Set freq_min and freq_max to plot.

        Args:
            freq_min (float): Freq min
            freq_max (float): Freq max

        Returns:
            Self
        """
        assert freq_min < freq_max, ValueError(f"⛔ freq_min must be less than freq_max!")
        self.freq_min: float = freq_min
        self.freq_max: float = freq_max

        filtered_dir: str = f"filtered_{freq_min}_{freq_max}"
        self.filtered_dir: str = os.path.join(self.rsam_dir, self.nslc, filtered_dir)

        return self

    @property
    def rsam_models(self) -> List[RsamCSV]:
        """Return RSAM models from database.

        Returns:
            List[RsamCSV]
        """
        rsam_db = RsamCSV.select().where(
            (RsamCSV.nslc == self.nslc) &
            (RsamCSV.resample >= self.resample) &
            (RsamCSV.date >= self.start_date) &
            (RsamCSV.date <= self.end_date) &
            (RsamCSV.freq_min == self.freq_min) &
            (RsamCSV.freq_max == self.freq_max)
        )

        rsam_models: List[RsamCSV] = [rsam for rsam in rsam_db]

        return rsam_models

    @property
    def csv_files(self) -> List[str]:
        """Return CSV file locations from database.

        Returns:
            List[str]
        """
        csv_files: List[str] = [rsam.file_location for rsam in self.rsam_models]
        return csv_files

    @property
    def df(self) -> pd.DataFrame:
        """Return concatenate DataFrame of CSVs.

        Returns:
            pd.DataFrame
        """
        df_list: List[pd.DataFrame] = []

        for csv in self.csv_files:
            _df = pd.read_csv(csv)
            if not _df.empty:
                df_list.append(_df)

        df = pd.concat(df_list, ignore_index=True)
        df = df.dropna()
        df = df.sort_values(by=['datetime'])
        df = df.drop_duplicates(keep='last')
        df = df.set_index('datetime')
        df.index = pd.to_datetime(df.index)

        return df

    @property
    def filename(self) -> str:
        """Filename for file and figure

        Returns:
            str: Filename
        """
        suffix: str = '_not_filtered'
        if (self.freq_min is not None) & (self.freq_max is not None):
            suffix = f"_{self.freq_min}Hz_{self.freq_max}Hz"

        filename = f"{self.start_date}_{self.end_date}_{self.resample}{suffix}"

        return filename

    def concat_csv(self, df: pd.DataFrame = None) -> str:
        """Concat CSV files.

        Returns:
            str: Combined csv file location
        """
        if df is None:
            df = self.df

        combined_csv_file: str = os.path.join(
            self.filtered_dir, f"combined_{self.filename}.csv")

        df.to_csv(combined_csv_file, index=True)
        print(f"✅ Combined CSV saved to : {combined_csv_file}")
        return combined_csv_file

    def handling_missing_data(self) -> Self:
        """Fill empty data with NaN so it will plot gap nicely.

        Returns:
            Self
        """
        datetime_index: pd.DatetimeIndex = pd.date_range(
            start=self.start_date, end=self.end_date, freq=self.resample)

        self.df.reindex(datetime_index, inplace=True)
        return self

    @staticmethod
    def calculate_matrix(df: pd.DataFrame, matrix: str, window: str) -> pd.DataFrame:
        """Calculate matrix.

        Args:
            df (pd.DataFrame): DataFrame
            matrix (str): Matrix. Eg: 'mean' or 'median'
            window (str): Window. Eg: '10min', '5min', '15min', '30min', '6h', '1d'

        Returns:
            pd.DataFrame
        """
        _column_name = f"{matrix}_{window}"

        if matrix is 'mean':
            df[_column_name] = df[matrix].rolling(window=window, center=True).mean()

        if matrix is 'median':
            df[_column_name] = df[matrix].rolling(window=window, center=True).mean()

        return df

    def run(self,
            matrices: List[str] = ['mean', 'median'],
            windows: List[str] = ['1d'],
            plot_as_log: bool = False,
            datetime_interval: int = 3,
            save_figure: bool = True,):

        assert len(matrices) > 0, ValueError(f"⛔ matrices cannot be empty! Use one of the value ['mean', 'median']")
        assert len(windows) > 0, ValueError(f"⛔ windows cannot be empty! "
                                            f"See https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases")

        self.concat_csv(df=self.df)

        df = self.handling_missing_data().df

        for matrix in matrices:
            for window in windows:
                df = self.calculate_matrix(df, matrix, window)

        self.plot(df=df, matrices=matrices, windows=windows)

        return df
