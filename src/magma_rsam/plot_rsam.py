import pandas as pd
import matplotlib.pyplot as plt
import os
from .validator import validate_dates


class PlotRsam:
    def __init__(self, start_date: str, end_date: str, station: str, channel: str,
                 network: str = 'VG', location: str = '00', freq_min: float = None,
                 freq_max: float = None, resample: str = '10min', rsam_dir: str = None):
        validate_dates(start_date, end_date)

        self.start_date = start_date
        self.end_date = end_date
        self.station = station
        self.channel = channel
        self.network = network
        self.location = location
        self.freq_min = float(freq_min)
        self.freq_max = float(freq_max)
        self.resample = resample

        if rsam_dir is None:
            rsam_dir: str = os.path.join(os.getcwd(), 'output', 'rsam')

        nslc = f"{network}.{station}.{location}.{channel}"

        filtered_dir: str = 'not_filtered'
        if (freq_min is not None) and (freq_max is not None):
            filtered_dir: str = f"filtered_{freq_min}_{freq_max}"

        self.rsam_dir: str = os.path.join(rsam_dir, nslc, filtered_dir, resample)
