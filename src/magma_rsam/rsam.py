import pandas as pd

from .rsam_trace import RsamTrace
from .validator import validate_dates
from magma_database import RsamCSV, Station
from magma_database.database import db
from magma_converter.search import Search
from magma_converter.database import DatabaseConverter
from obspy import UTCDateTime, Stream
from obspy.clients.filesystem.sds import Client
from typing import Dict, List, Self
from datetime import date
from tqdm.notebook import tqdm


class RSAM:
    def __init__(
        self,
        start_date: str,
        seismic_dir: str,
        station: str,
        end_date: str = None,
        channel: str = "*",
        network: str = "VG",
        location: str = "00",
        directory_structure: str = "sds",
        update_db: bool = True,
        overwrite: bool = False,
        resample: str = "10min",
        verbose: bool = True,
    ):

        self.start_date = start_date
        self.end_date = end_date

        if end_date is None:
            self.end_date = date.today().strftime("%Y-%m-%d")

        self.station: str = station
        self.channel: str = channel
        self.network: str = network
        self.location: str = location
        self.seismic_dir: str = seismic_dir
        self.nslc: str = f"{network}.{station}.{location}.{channel}"
        self.directory_structure: str = directory_structure
        self.rsam: Dict[str, RsamTrace] = {}
        self.resample = resample

        self.filter_is_on: bool = False
        self.update_db: bool = update_db

        if update_db:
            db.create_tables([RsamCSV, Station])

        self.corners = None
        self.freq_max = None
        self.freq_min = None
        self.files: Dict[str, List[Dict[str, str]]] = {}
        self.overwrite = overwrite
        self.verbose: bool = verbose

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
        if self.verbose:
            print(f"ℹ️ Filter is on.")
        return self

    def rsam_already_running(self, station: str, date_str: str) -> RsamCSV | None:
        freq_min: float = self.freq_min
        freq_max: float = self.freq_max

        query = RsamCSV.select().where(
            (RsamCSV.key.contains(station))
            & (RsamCSV.date == date_str)
            & (RsamCSV.freq_min == freq_min)
            & (RsamCSV.freq_max == freq_max)
        )

        return query.first()

    def add_to_files(self, trace_id: str, date_str: str, file_location: str) -> Self:
        """Add to self.files

        Args:
            trace_id (str): trace id/nslc
            date_str (str): date string
            file_location (str): CSV file location

        Returns:
            Self: self
        """
        if trace_id not in self.files.keys():
            self.files[trace_id] = []

        self.files[trace_id].append({date_str: file_location})

        return self

    def run(self) -> Self:
        start_date = self.start_date
        end_date = self.end_date
        validate_dates(start_date, end_date)

        # TODO: looping through date
        dates = pd.date_range(start_date, end_date, freq="1D")

        for date_obj in tqdm(dates):
            date_str: str = date_obj.strftime("%Y-%m-%d")

            # Check existing calculated RSAM
            # If exist then, continue next date
            # else, calculate
            if not self.overwrite:
                rsam_csv = self.rsam_already_running(
                    station=self.station, date_str=date_str
                )

                if rsam_csv is not None:
                    if self.verbose:
                        print(
                            f"✅ {date_str} :: File RSAM for {rsam_csv} : {rsam_csv.file_location}"
                        )
                    self.add_to_files(
                        trace_id=rsam_csv.nslc,
                        date_str=date_str,
                        file_location=rsam_csv.file_location,
                    )
                    continue

            if self.directory_structure.lower() == "sds":
                stream = self.from_sds(date_str)
            else:
                stream = Search(
                    input_dir=self.seismic_dir,
                    directory_structure=self.directory_structure.lower(),
                    station=self.station,
                    channel=self.channel,
                    network=self.network,
                    location=self.location,
                    check_file_integrity=True,
                ).search(date_str=date_str)

            if len(stream) == 0:
                if self.verbose:
                    print(f"⚠️ {date_str} :: Skip. No traces found")
                continue

            if self.update_db:
                # Make sure station exists
                for trace in stream:
                    station = {
                        "nslc": trace.id,
                        "station": trace.stats.station,
                        "network": trace.stats.network,
                        "location": trace.stats.location,
                        "channel": trace.stats.channel,
                    }
                    DatabaseConverter.update_station(station=station)

            if self.filter_is_on:
                if self.verbose:
                    print(f"🔄️ Apply filter")
                stream.filter(
                    "bandpass",
                    freqmin=self.freq_min,
                    freqmax=self.freq_max,
                    corners=self.corners,
                )

            if len(stream) > 1:
                if self.verbose:
                    print(f"ℹ️ Found {len(stream)} traces. Merging... ", end="")
                stream = stream.merge(fill_value=0)
                if self.verbose:
                    print(f"✅")

            for trace in stream:
                rsam_trace = RsamTrace(
                    trace,
                    update_db=self.update_db,
                    is_filtered=self.filter_is_on,
                    freq_min=self.freq_min,
                    freq_max=self.freq_max,
                    verbose=self.verbose,
                )
                rsam_trace.calculate().save()

                self.add_to_files(
                    trace_id=trace.id,
                    date_str=date_str,
                    file_location=rsam_trace.csv_file,
                )

        return self
