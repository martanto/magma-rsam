from .rsam_trace import RsamTrace
from datetime import timedelta
from obspy import UTCDateTime, Stream
from obspy.clients.filesystem.sds import Client
from typing import Dict, Self


class RSAM:
    def __init__(self, seismic_dir: str, date: str, station: str,
                 channel: str = '*', network: str = 'VG', location: str = '00',
                 directory_structure: str = 'sds'):
        self.date: str = date
        self.station: str = station
        self.channel: str = channel
        self.network: str = network
        self.location: str = location
        self.seismic_dir: str = seismic_dir
        self.nslc: str = f"{network}.{station}.{location}.{channel}"
        self.directory_structure: str = directory_structure
        self.rsam: Dict[str, RsamTrace] = {}

    def from_sds(self) -> Stream:
        start_time: UTCDateTime = UTCDateTime(f"{self.date}T00:00:00")
        end_time: UTCDateTime = UTCDateTime(f"{self.date}T23:59:59")

        client = Client(sds_root=self.seismic_dir)
        stream: Stream = client.get_waveforms(
            station=self.station,
            channel=self.channel,
            network=self.network,
            location=self.location,
            starttime=start_time,
            endtime=end_time,
            # merge=True,
        )

        if len(stream) > 0:
            return stream

        return Stream()

    def run(self) -> Self:
        stream: Stream = Stream()

        if self.directory_structure == 'sds':
            stream = self.from_sds()

        if len(stream) == 0:
            print("⚠️ Skip. No traces found")
            return self

        for trace in stream:
            self.rsam[trace.id] = RsamTrace(trace).calculate().save()

        return self