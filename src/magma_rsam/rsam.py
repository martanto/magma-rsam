import pandas as pd
from .rsam_trace import RsamTrace
from .validator import validate_dates
from obspy import UTCDateTime, Stream
from obspy.clients.filesystem.sds import Client
from typing import Dict, List, Self
from datetime import date


class RSAM:
    def __init__(self, seismic_dir: str, station: str,
                 channel: str = '*', network: str = 'VG', location: str = '00',
                 start_date: str = None, end_date: str = None, directory_structure: str = 'sds',
                 update_db: bool = True, resample: str = '10min'):
        self.start_date = start_date
        self.end_date = end_date
        self.station: str = station
        self.channel: str = channel
        self.network: str = network
        self.location: str = location
        self.seismic_dir: str = seismic_dir
        self.nslc: str = f"{network}.{station}.{location}.{channel}"
        self.directory_structure: str = directory_structure
        self.rsam: Dict[str, RsamTrace] = {}

        self.filter_is_on: bool = False
        self.update_db: bool = update_db
        self.resample: str = resample
        self.corners = None
        self.freq_max = None
        self.freq_min = None
        self.files: Dict[str, List[Dict[str, str]]] = {}

    def from_date(self, start_date: str) -> Self:
        assert date.fromisoformat(start_date), f"❌ date format must be yyyy-mm-dd"
        self.start_date = start_date
        return self

    def to_date(self, end_date: str) -> Self:
        assert date.fromisoformat(end_date), f"❌ date format must be yyyy-mm-dd"
        self.end_date = end_date
        return self

    def from_sds(self, date_str: str) -> Stream:
        start_time: UTCDateTime = UTCDateTime(f"{date_str}T00:00:00")
        end_time: UTCDateTime = UTCDateTime(f"{date_str}T23:59:59")

        client = Client(sds_root=self.seismic_dir)
        stream: Stream = client.get_waveforms(
            station=self.station,
            channel=self.channel,
            network=self.network,
            location=self.location,
            starttime=start_time,
            endtime=end_time,
        )

        if len(stream) > 0:
            return stream

        return Stream()

    def apply_filter(self, freq_min: float, freq_max: float, corners: int = 4) -> Self:
        self.freq_min = freq_min
        self.freq_max = freq_max
        self.corners = corners
        self.filter_is_on = True
        return self

    def run(self) -> Self:
        start_date = self.start_date
        end_date = self.end_date
        validate_dates(start_date, end_date)

        # TODO: looping through date
        dates = pd.date_range(start_date, end_date, freq='1D')

        for date_obj in dates:
            date_str: str = date_obj.strftime('%Y-%m-%d')
            stream: Stream = Stream()

            if self.directory_structure.lower() == 'sds':
                stream = self.from_sds(date_str)

            if len(stream) == 0:
                print(f"⚠️ {date_str} :: Skip. No traces found")
                continue

            if self.filter_is_on is True:
                stream.filter('bandpass', freqmin=self.freq_min,
                              freqmax=self.freq_max, corners=self.corners)

            for trace in stream:
                rsam_trace = RsamTrace(trace, update_db=self.update_db)
                rsam_trace.set_resample(self.resample).calculate().save()

                self.files[trace.id].append({date_str : rsam_trace.csv_file})

        return self
