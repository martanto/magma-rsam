import pandas as pd
import matplotlib.pyplot as plt
import os
from .database import db, RsamCSV
from .validator import validate_dates
from typing import List


class PlotRsam:
    def __init__(self,
                 start_date: str,
                 end_date: str,
                 station: str,
                 channel: str,
                 network: str = 'VG',
                 location: str = '00',
                 freq_min: float = None,
                 freq_max: float = None,
                 resample: str = '10min'):

        validate_dates(start_date, end_date)
        self.start_date = start_date
        self.end_date = end_date
        self.station = station
        self.channel = channel
        self.network = network
        self.location = location
        self.freq_min: float | None = float(freq_min) if isinstance(freq_min, float) else None
        self.freq_max: float | None = float(freq_max) if isinstance(freq_max, float) else None
        self.resample = resample
        self.nslc = f"{network}.{station}.{location}.{channel}"

        rsam_dir: str = os.path.join(os.getcwd(), 'output', 'rsam')

        nslc = f"{network}.{station}.{location}.{channel}"

        filtered_dir: str = 'not_filtered'
        if (freq_min is not None) and (freq_max is not None):
            filtered_dir: str = f"filtered_{freq_min}_{freq_max}"

        self.filtered_dir: str = os.path.join(rsam_dir, nslc, filtered_dir)
        self.rsam_dir: str = os.path.join(self.filtered_dir, resample)

        print(f"ℹ️ Start Date: {start_date}")
        print(f"ℹ️ End Date: {end_date}")
        print(f"ℹ️ Station: {station}")
        print(f"ℹ️ Channel: {channel}")
        print(f"ℹ️ Network: {network}")
        print(f"ℹ️ Location: {location}")
        print(f"ℹ️ Freq Min: {freq_min}")
        print(f"ℹ️ Freq Max: {freq_max}")
        print(f"ℹ️ Resample: {resample}")

        if not os.path.isdir(self.rsam_dir):
            raise NotADirectoryError(f"⛔ The directory {self.rsam_dir} does not exist!"
                                     f" Please run RSAM with the current parameters")

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
    def filename(self) ->str:
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

    def run(self, save_figure: bool = True):
        df = self.df
        self.concat_csv(df=df)
        return df
