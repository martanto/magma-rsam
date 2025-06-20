import pandas as pd
import numpy as np
import os
from obspy import Trace, UTCDateTime
from datetime import datetime, timedelta, timezone
from typing import List, Self
from .validator import validate_matrices
from magma_database import RsamCSV
from magma_database.database import db


class RsamTrace:
    matrices: List[str] = ["min", "mean", "max", "median", "std"]
    df: pd.DataFrame = pd.DataFrame()

    def __init__(
        self,
        trace: Trace,
        update_db: bool = True,
        is_filtered: bool = False,
        freq_min: float = None,
        freq_max: float = None,
        resample: str = "10min",
        overwrite: bool = False,
        verbose: bool = True,
    ):
        self.trace_original: Trace = trace
        self.trace: Trace = trace.copy()

        self.start_datetime: UTCDateTime = self.trace.stats.starttime
        self.start_date: UTCDateTime = self.start_datetime + timedelta(seconds=10)
        self.start_date_str: str = self.start_date.strftime("%Y-%m-%d")

        self.end_datetime: UTCDateTime = self.trace.stats.endtime
        self.end_date: UTCDateTime = self.end_datetime + timedelta(seconds=10)
        self.end_date_str: str = self.end_date.strftime("%Y-%m-%d")

        self.id: str = f"{trace.id}_{self.start_date_str}"

        self.matrices: List[str] = RsamTrace.matrices
        self.is_filtered: bool = is_filtered
        self.resample: str = resample
        self.df: pd.DataFrame = RsamTrace.df

        if update_db is True:
            db.connect(reuse_if_open=True)
            db.create_tables([RsamCSV])
            db.close()

        self.freq_max = freq_max
        self.freq_min = freq_min
        self.update_db: bool = update_db
        self.csv_file: str | None = None
        self.overwrite: bool = overwrite
        self.verbose: bool = verbose

    def refresh(self) -> Self:
        """Refresh initial values of RSAM parameters

        Returns:
            Self
        """
        self.trace: Trace = self.trace_original.copy()

        self.start_datetime: UTCDateTime = self.trace.stats.starttime
        self.start_date: UTCDateTime = self.start_datetime + timedelta(seconds=10)
        self.start_date_str: str = self.start_date.strftime("%Y-%m-%d")

        self.end_datetime: UTCDateTime = self.trace.stats.endtime
        self.end_date: UTCDateTime = self.end_datetime + timedelta(seconds=10)
        self.end_date_str: str = self.end_date.strftime("%Y-%m-%d")

        self.id: str = f"{self.trace.id}_{self.start_date_str}"

        self.matrices: List[str] = RsamTrace.matrices
        self.is_filtered: bool = self.is_filtered
        self.resample: str = self.resample
        self.df: pd.DataFrame = RsamTrace.df

        self.freq_max = None
        self.freq_min = None
        self.update_db: bool = True
        self.csv_file: str | None = None
        return self

    def set_matrices(self, matrices: List[str]) -> Self:
        """Set calculation matrices.

        Args:
            matrices (List[str]): List of matrices to calculate.

        Returns:
            Self
        """
        validate_matrices(matrices)
        self.matrices = matrices
        return self

    def set_filter(self, freq_min: float, freq_max: float, corners: int = 4) -> Self:
        """Apply filter to trace.

        Args:
            freq_min (float): Minimum frequency.
            freq_max (float): Maximum frequency.
            corners (int): Number of corners.

        Returns:
            Self
        """
        self.trace = self.trace.filter(
            "bandpass", freqmin=freq_min, freqmax=freq_max, corners=corners
        )

        self.freq_min: float = freq_min
        self.freq_max: float = freq_max
        self.is_filtered = True
        return self

    def set_resample(self, resample: str) -> Self:
        """Set resample value. Refer to pandas resample rules

        Args:
            resample (str): Resampling rule, Default 10min

        Returns:
            Self
        """
        self.resample = resample
        return self

    def trace_to_series(self, trace: Trace = None) -> pd.Series:
        """Convert trace to series.

        Args:
            trace (Trace): trace to convert.

        Returns:
            pd.Series
        """
        if trace is None:
            trace = self.trace

        index_time = pd.date_range(
            start=trace.stats.starttime.datetime,
            periods=trace.stats.npts,
            freq="{}ms".format(trace.stats.delta * 1000),
        )

        _series = pd.Series(
            data=np.abs(trace.data),
            index=index_time,
            name="values",
            dtype=trace.data.dtype,
        )

        _series.index.name = "datetime"

        return _series

    def calculate(self) -> Self:
        """Calculate RSAM

        Returns:
            Self
        """
        if self.verbose:
            print("⌚ {} Calculating for {}".format(self.start_date_str, self.trace.id))

        df: pd.DataFrame = pd.DataFrame()
        matrices = self.matrices
        trace = self.trace.detrend(type="demean")
        series = self.trace_to_series(trace).resample(self.resample)

        for metric in matrices:
            df[metric] = series.apply(metric)

        self.df = df
        return self

    def update_database(
        self, nslc: str, date: str, resample: str, file_location: str
    ) -> None:
        filtered: str = f"_{self.freq_min}_{self.freq_max}"
        key: str = f"{nslc}_{date}_{resample}{filtered}"

        _rsam, exists = RsamCSV.get_or_create(
            key=key,
            date=date,
            defaults={
                "nslc": nslc,
                "resample": resample,
                "freq_min": self.freq_min,
                "freq_max": self.freq_max,
                "file_location": file_location,
                "created_at": datetime.now(tz=timezone.utc),
            },
        )

        rsam_id = _rsam.get_id()

        if exists and not self.overwrite:
            if self.verbose:
                print(f"✅ Created RSAM ID: {rsam_id}")
            return rsam_id

        if self.verbose:
            print(f"⌛ Updating RSAM ID: {rsam_id} ... ", end="")

        _rsam.key = key
        _rsam.nslc = nslc
        _rsam.date = date
        _rsam.resample = resample
        _rsam.freq_min = self.freq_min
        _rsam.freq_max = self.freq_max
        _rsam.file_location = file_location
        _rsam.updated_at = datetime.now(tz=timezone.utc)

        _rsam.save()

        db.close()

        if self.verbose:
            print(f"Done ✅")

        return rsam_id

    def save(self, output_dir: str = None) -> Self:
        """Save RSAM results to directory as CSV.

        Args:
            output_dir (str, optional): Directory to save RSAM results to. Defaults to None.

        Returns:
            Self
        """
        if not self.df.empty:

            if output_dir is None:
                output_dir = os.path.join(os.getcwd(), "output", "rsam")
            os.makedirs(output_dir, exist_ok=True)

            filtered_dir: str = "not_filtered"
            if self.is_filtered:
                filtered_dir: str = f"filtered_{self.freq_min}_{self.freq_max}"

            csv_dir: str = os.path.join(
                output_dir, self.trace.id, filtered_dir, self.resample
            )
            os.makedirs(csv_dir, exist_ok=True)

            csv_file = os.path.join(csv_dir, f"{self.start_date_str}.csv")

            self.df.to_csv(csv_file)
            self.csv_file = csv_file

            if self.update_db:
                self.update_database(
                    self.trace.id, self.start_date_str, self.resample, csv_file
                )

            if self.verbose:
                print("💾 Saved to {}".format(csv_file))
        else:
            if self.verbose:
                print(f"⚠️ Not saved. Not enough data for {self.id}")
        return self
