import pandas as pd
import os
import numpy as np
from obspy import Trace, Stream, UTCDateTime
from obspy.clients.filesystem.sds import Client
from datetime import timedelta
from typing import Dict, List, Self

bands: dict[str, list[float]] = {
    'VLP': [0.02, 0.2],
    'LP': [0.5, 4.0],
    'VT': [5.0, 18.0]
}


def validate_matrices(matrices: List[str]) -> bool | ValueError:
    default_matrices: List[str] = ['min', 'mean', 'max', 'median', 'std']
    for metric in matrices:
        if metric not in default_matrices:
            raise ValueError(f"Metric {metric} is not valid. Please use one of {default_matrices}")
    return True


def trace_to_series(trace: Trace) -> pd.Series:
    index_time = pd.date_range(
        start=trace.stats.starttime.datetime,
        periods=trace.stats.npts,
        freq="{}ms".format(trace.stats.delta * 1000)
    )

    _series = pd.Series(
        data=np.abs(trace.data),
        index=index_time,
        name='values',
        dtype=trace.data.dtype)

    _series.index.name = 'datetime'

    return _series


class RSAM:
    def __init__(self, sds_dir: str, date_str: str, station: str = '*', network: str = 'VG',
                 channel: str = '*', location: str = '*'):
        """Calculate RSAM value for one day"""

        self.date_str: str = date_str
        self.date_obj: UTCDateTime = UTCDateTime(date_str)

        self.resample: str = '10min'

        self.client = Client(sds_dir)
        self.stream: Stream = self.client.get_waveforms(
            network=network,
            station=station,
            location=location,
            channel=channel,
            starttime=self.date_obj,
            endtime=self.date_obj + timedelta(days=1)
        )

        self.results: Dict[str, pd.DataFrame] = {}
        self.csv: List[str] = []

    def resample(self, resample: str) -> Self:
        self.resample = resample
        return self

    def apply_filter(self, freq_min: float, freq_max: float, corners: int = 4) -> Self:
        self.stream.filter('bandpass', freqmin=freq_min,
                           freqmax=freq_max, corners=corners)
        return self

    def calculate(self, resample: str = '10min', matrices=None) -> Self:
        self.resample = resample

        if matrices is None:
            matrices = ['min', 'mean', 'max', 'median', 'std']

        if matrices is not None:
            validate_matrices(matrices)

        for trace in self.stream:
            df: pd.DataFrame = pd.DataFrame()
            date_string = trace.stats.starttime.strftime('%Y-%m-%d')
            print("⌚ Calculating {} for {}".format(date_string, trace.id))
            trace = trace.detrend(type='demean')
            series = trace_to_series(trace).resample(self.resample)

            for metric in matrices:
                df[metric] = series.apply(metric)

            self.results[trace.id] = df

        return self

    def save(self, output_dir: str = None) -> Self:

        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), 'output', 'rsam')

        os.makedirs(output_dir, exist_ok=True)

        for station, df in self.results.items():

            if not df.empty:

                date_str = str(df.first_valid_index()).split(' ')[0]

                csv_dir: str = os.path.join(output_dir, station, self.resample)
                os.makedirs(csv_dir, exist_ok=True)

                csv_file = os.path.join(csv_dir, f'{station}_{date_str}.csv')

                # Saving to CSV
                df.to_csv(csv_file)

                # Return CSV location
                self.csv.append(csv_file)
                print("💾 Saved to {}".format(csv_file))
            else:
                print(f'⚠️ Not saved. Not enough data for {station}')
        return self
