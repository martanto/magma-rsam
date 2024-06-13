import pandas as pd
import os
import numpy as np
from .validator import validate_matrices, validate_directory, validate_directory_structure
from .database import db, RsamCSV
from obspy import read, Trace, Stream, UTCDateTime
from obspy.clients.filesystem.sds import Client
from datetime import timedelta
from typing import Dict, List, Self, Any

bands: dict[str, list[float]] = {
    'VLP': [0.02, 0.2],
    'LP': [0.5, 4.0],
    'VT': [5.0, 18.0]
}


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


def trimming_trace(stream: Stream, start_time: UTCDateTime,
                   end_time: UTCDateTime) -> Stream:
    """Trim a stream of traces.

    Args:
        stream (Stream): Stream to trim.
        start_time (UTCDateTime): Start time of the date.
        end_time (UTCDateTime): End time of the date.

    Returns:
        Stream: Trimmed stream.
    """
    stream = remove_trace(stream)
    if stream.count() > 0:
        stream.trim(starttime=start_time, endtime=end_time)
        stream.merge(fill_value=0)
    return stream


def remove_trace(stream: Stream) -> Stream:
    """Remove traces from a stream.

    Args:
        stream (Stream): Stream to remove traces from.

    Returns:
        Stream: Stream with traces removed.
    """
    for trace in stream:
        if trace.stats.sampling_rate < 50.0:
            stream.remove(trace)
    return stream


class RSAM:
    def __init__(self, directory_structure: str, seismic_dir: str, station: str = '*',
                 date_str: str = None, network: str = 'VG', channel: str = '*', location: str = '*',
                 update_db: bool = True):
        """Calculate RSAM value for one day"""
        validate_directory_structure(directory_structure)
        validate_directory(seismic_dir)

        self.directory_structure = directory_structure
        self.seismic_dir: str = seismic_dir

        self.station: str = station
        self.network: str = network
        self.channel: str = channel
        self.location: str = location

        self.select = {
            'network': network,
            'station': station,
            'location': location,
            'channel': channel,
        }

        self.date_str: str | None = date_str if date_str is not None else None
        self.date_obj: UTCDateTime | None = UTCDateTime(date_str) if date_str is not None else None

        self.resample: str = '10min'
        self.stream: Stream | None = self._stream(directory_structure) if date_str is not None else None
        self.results: Dict[str, pd.DataFrame] = {}
        self.csvs: List[Dict[str, Any]] = []

        if update_db:
            db.connect(reuse_if_open=True)
            db.create_tables([RsamCSV])
            db.close()

        self.update_db: bool = update_db

    def _sds(self) -> Stream:
        """Returns Stream from Seiscomp Data Structure (SDS)

        Returns:
            Stream: Stream from Seiscomp Data Structure (SDS)
        """
        client = Client(self.seismic_dir)
        return client.get_waveforms(
            station=self.station,
            network=self.network,
            channel=self.channel,
            location=self.location,
            starttime=self.date_obj,
            endtime=self.date_obj + timedelta(days=1),
        )

    def merged(self, stream: Stream) -> Stream:
        """Merging seismic data into daily seismic data.

        Args:
            stream (Stream): Stream object

        Returns:
            Stream: Stream object
        """
        start_time: UTCDateTime = self.date_obj
        end_time: UTCDateTime = self.date_obj + timedelta(days=1)
        return trimming_trace(stream, start_time, end_time)

    def _seisan(self) -> Stream:
        """Read seisan data structure.

        Returns:
            Stream: Stream object
        """
        wildcard: str = "{}*".format(self.date_str)
        seismic_dir: str = os.path.join(self.seismic_dir, wildcard)

        try:
            stream: Stream = read(seismic_dir)
            stream = stream.select(**self.select)
            return self.merged(stream)
        except Exception as e:
            print(f'⛔ {self.date_str} - self.seisan():: {e}')
            return Stream()

    def _stream(self, directory_structure: str) -> Stream:
        """Return Stream from directory structure.

        Returns:
            Stream: Stream object
        """
        stream = Stream()
        if directory_structure == 'sds':
            stream = self._sds()
        if directory_structure == 'seisan':
            stream = self._seisan()

        self.stream = stream
        return stream

    def date(self, date_str: str) -> Self:
        """Set date.

        Args:
            date_str (str): Date string

        Returns:
            Self
        """
        self.date_str: str = date_str
        self.date_obj: UTCDateTime = UTCDateTime(date_str)
        self.stream: Stream = self._stream(self.directory_structure)
        return self

    def resample(self, resample: str) -> Self:
        """Set resample value. Refer to pandas resample rules

        Args:
            resample (str): Resampling rule, Default 10min

        Returns:
            Self
        """
        self.resample = resample
        return self

    def apply_filter(self, freq_min: float, freq_max: float, corners: int = 4) -> Self:
        """Apply filter to Stream.

        Args:
            freq_min (float): Minimum frequency.
            freq_max (float): Maximum frequency.
            corners (int): Number of corners.

        Returns:
            Self
        """
        stream = self._stream(self.directory_structure)

        self.stream = stream.filter('bandpass', freqmin=freq_min,
                                    freqmax=freq_max, corners=corners)
        return self

    def calculate(self, matrices=None) -> Self:
        """Calculate RSAM values.

        Returns:
            Self
        """
        if matrices is None:
            matrices = ['min', 'mean', 'max', 'median', 'std']

        if matrices is not None:
            validate_matrices(matrices)

        stream = self.stream

        if stream.count() == 0:
            print(f'⚠️ {self.date_str} No data found. Skipped,')
            return self

        for trace in stream:
            df: pd.DataFrame = pd.DataFrame()
            print("⌚ Calculating {} for {}".format(self.date_str, trace.id))
            trace = trace.detrend(type='demean')
            series = trace_to_series(trace).resample(self.resample)

            for metric in matrices:
                df[metric] = series.apply(metric)

            self.results[trace.id] = df

        return self

    def update_database(self, nslc: str, date: str, file_location: str) -> None:
        if self.update_db:
            (RsamCSV
             .insert(
                nslc=nslc,
                date=date,
                file_location=file_location
            )
             .on_conflict(
                conflict_target=[RsamCSV.nslc, RsamCSV.date],
                preserve=[RsamCSV.nslc, RsamCSV.date],
                update={RsamCSV.file_location: file_location})
             .execute())

            db.close()

    def save(self, output_dir: str = None) -> Self:
        """Save RSAM results to directory as CSV.

        Args:
            output_dir (str, optional): Directory to save RSAM results to. Defaults to None.

        Returns:
            Self
        """
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), 'output', 'rsam')

        os.makedirs(output_dir, exist_ok=True)

        for trace_id, df in self.results.items():

            if not df.empty:

                date_str = str(df.first_valid_index()).split(' ')[0]

                csv_dir: str = os.path.join(output_dir, trace_id, self.resample)
                os.makedirs(csv_dir, exist_ok=True)

                csv_file = os.path.join(csv_dir, f'{trace_id}_{date_str}.csv')

                # Saving to CSV
                df.to_csv(csv_file)

                # csv_dict: Dict[str, Any] = {
                #     'nslc': trace_id,
                #     'date': date_str,
                #     'file_location': csv_file
                # }

                # Return CSV location
                # self.csvs.append(csv_dict)

                if self.update_db:
                    self.update_database(trace_id, date_str, csv_file)

                print("💾 Saved to {}".format(csv_file))
            else:
                print(f'⚠️ Not saved. Not enough data for {trace_id}')
        return self
