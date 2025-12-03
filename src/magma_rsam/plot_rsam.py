import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import random
from magma_database import RsamCSV
from .validator import validate_dates
from typing import List, Self
from material_color.color import get_color_list
from datetime import datetime


class PlotRsam:
    def __init__(
        self,
        start_date: str,
        end_date: str,
        station: str,
        channel: str,
        rsam_dir: str = None,
        figures_dir: str = None,
        network: str = "VG",
        location: str = "00",
        resample: str = "10min",
        verbose: bool = False,
    ):

        validate_dates(start_date, end_date)
        self.start_date = start_date
        self.end_date = end_date
        self.station = station
        self.channel = channel
        self.network = network
        self.location = location
        self.resample = resample
        self.verbose = verbose

        self.freq_min: float | None = None
        self.freq_max: float | None = None
        self.nslc = f"{network}.{station}.{location}.{channel}"

        if rsam_dir is None:
            rsam_dir: str = os.path.join(os.getcwd(), "output", "rsam")

        if figures_dir is None:
            figures_dir: str = os.path.join(os.getcwd(), "output", "figures", "rsam")
        os.makedirs(figures_dir, exist_ok=True)
        self.figures_dir = figures_dir

        nslc = f"{network}.{station}.{location}.{channel}"

        filtered_dir: str = "not_filtered"
        self.filtered_dir: str = os.path.join(rsam_dir, nslc, filtered_dir)
        self.rsam_dir: str = os.path.join(self.filtered_dir, resample)

        print(f"ℹ️ Start Date: {start_date}")
        print(f"ℹ️ End Date: {end_date}")
        print(f"ℹ️ Station: {station}")
        print(f"ℹ️ Channel: {channel}")
        print(f"ℹ️ Network: {network}")
        print(f"ℹ️ Location: {location}")
        print(f"ℹ️ Resample: {resample}")

        self.y_min = None
        self.y_max = None

    def with_filter(self, freq_min: float, freq_max: float) -> Self:
        """Set freq_min and freq_max to plot.

        Args:
            freq_min (float): Freq min
            freq_max (float): Freq max

        Returns:
            Self
        """
        assert freq_min < freq_max, ValueError(
            f"⛔ freq_min must be less than freq_max!"
        )
        self.freq_min: float = freq_min
        self.freq_max: float = freq_max

        rsam_dir: str = os.path.join(os.getcwd(), "output", "rsam")

        filtered_dir: str = f"filtered_{freq_min}_{freq_max}"
        self.filtered_dir: str = os.path.join(rsam_dir, self.nslc, filtered_dir)

        return self

    @property
    def rsam_models(self) -> List[RsamCSV]:
        """Return RSAM models from database.

        Returns:
            List[RsamCSV]
        """
        rsam_db = RsamCSV.select().where(
            (RsamCSV.nslc == self.nslc)
            & (RsamCSV.resample == self.resample)
            & (RsamCSV.date >= self.start_date)
            & (RsamCSV.date <= self.end_date)
            & (RsamCSV.freq_min == self.freq_min)
            & (RsamCSV.freq_max == self.freq_max)
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
            if not os.path.exists(csv):
                if self.verbose:
                    print(f"⚠️ File not found: {csv}")
                continue
            _df = pd.read_csv(csv)
            if not _df.empty:
                df_list.append(_df)

        df = pd.concat(df_list, ignore_index=True)
        df = df.dropna()
        df = df.sort_values(by=["datetime"])
        df = df.drop_duplicates(keep="last")
        df = df.set_index("datetime")
        df.index = pd.to_datetime(df.index)

        return df

    @property
    def filename(self) -> str:
        """Filename for file and figure

        Returns:
            str: Filename
        """
        suffix: str = "not-filtered"
        if (self.freq_min is not None) & (self.freq_max is not None):
            suffix = f"{self.freq_min}-{self.freq_max}Hz"

        filename = (
            f"{self.nslc}_{self.start_date}-{self.end_date}_{suffix}_{self.resample}"
        )

        return filename

    def concat_csv(self, df: pd.DataFrame = None) -> str:
        """Concat CSV files.

        Returns:
            str: Combined csv file location
        """
        if df is None:
            df = self.df

        combined_csv_file: str = os.path.join(
            self.filtered_dir, f"combined_{self.filename}.csv"
        )

        df.to_csv(combined_csv_file, index=True)
        print(f"✅ Combined CSV saved to : {combined_csv_file}")
        return combined_csv_file

    def handling_missing_data(self) -> Self:
        """Fill empty data with NaN, so it will plot gap nicely.

        Returns:
            Self
        """
        datetime_index: pd.DatetimeIndex = pd.date_range(
            start=self.start_date, end=self.end_date, freq=self.resample
        )

        self.df.reindex(datetime_index)
        return self

    @staticmethod
    def calculate_metric(df: pd.DataFrame, metric: str, window: str) -> pd.DataFrame:
        """Calculate metric.

        Args:
            df (pd.DataFrame): DataFrame
            metric (str): Matrix. Eg: 'mean' or 'median'
            window (str): Window. Eg: '10min', '5min', '15min', '30min', '6h', '1d'

        Returns:
            pd.DataFrame
        """
        _column_name = f"{metric}_{window}"

        if metric == "mean":
            df[_column_name] = df[metric].rolling(window=window, center=True).mean()

        if metric == "median":
            df[_column_name] = df[metric].rolling(window=window, center=True).median()

        return df

    def set_y_lim(self, y_min: int | float, y_max: int | float) -> Self:
        self.y_min = y_min
        self.y_max = y_max
        return self

    def plot(
        self,
        df: pd.DataFrame,
        metrics: List[str],
        windows: List[str],
        plot_as_log: bool = False,
        datetime_interval: int = 3,
        colors: List[str] = None,
    ) -> plt.Figure:

        _shape_metrics_windows = len(metrics) * len(windows)

        if colors is None:
            colors = ["#FFEB3B", "#F44336"]
        elif (colors is None) and (_shape_metrics_windows > 2):
            colors = get_color_list()
        else:
            assert len(colors) < _shape_metrics_windows, (
                f"Minimal {_shape_metrics_windows} colors must be exists in 'colors' parameter. "
                f"Default is ['#FFEB3B', '#F44336']"
            )

        fig, axs = plt.subplots(
            nrows=1, ncols=1, figsize=(12, 4), layout="constrained", sharex=True
        )

        axs.scatter(df.index, df["mean"], c="k", alpha=0.2, s=3, label="10 minutes")

        for metric in metrics:
            for window in windows:
                column_name: str = f"{metric}_{window}"
                label: str = f"{metric} {window}"

                color = random.choice(colors)

                if column_name == "median_1d":
                    color = "#FFEB3B"

                if column_name == "mean_1d":
                    color = "#F44336"

                if color in ["#FFEB3B", "#F44336"]:
                    colors.remove(color)

                axs.plot(df.index, df[column_name], c=color, label=label, alpha=1, lw=2)

        y_label = "Amplitude (count)"
        if plot_as_log is True:
            y_label = f"{y_label} log"
            axs.set_yscale("log")

        axs.set_ylabel(y_label)
        axs.xaxis.set_major_locator(mdates.DayLocator(interval=datetime_interval))
        axs.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

        if (self.y_min is not None) and (self.y_max is not None):
            axs.set_ylim(self.y_min, self.y_max)

        axs.set_xlim(
            datetime.strptime(self.start_date, "%Y-%m-%d"),
            datetime.strptime(self.end_date, "%Y-%m-%d"),
        )

        for _label in axs.get_xticklabels(which="major"):
            _label.set(rotation=30, horizontalalignment="right")

        axs.legend(loc="upper left", fontsize="10", ncol=4)

        save_path: str = os.path.join(self.figures_dir, f"{self.filename}.png")
        fig.savefig(save_path)
        print(f"📈 RSAM Figure saved to : {save_path}")

        return fig

    def run(
        self,
        metrics: List[str] = None,
        windows: List[str] = None,
        plot_as_log: bool = False,
        datetime_interval: int = 3,
        save_figure: bool = True,
        colors: List[str] = None,
    ):

        os.makedirs(self.filtered_dir, exist_ok=True)

        if windows is None:
            windows = ["1d"]
        if metrics is None:
            metrics = ["mean", "median"]

        assert len(metrics) > 0, ValueError(
            f"⛔ metrics cannot be empty! Use one of the value ['mean', 'median']"
        )
        assert len(windows) > 0, ValueError(
            f"⛔ windows cannot be empty! "
            f"See https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases"
        )

        self.concat_csv(df=self.df)

        df = self.handling_missing_data().df

        print(f"⬆️ Max Amplitude: {df['mean'].max()}")
        print(f"⬇️ Min Amplitude: {df['mean'].min()}")

        for metric in metrics:
            for window in windows:
                df = self.calculate_metric(df, metric, window)

        if save_figure is True:
            self.plot(
                df=df,
                metrics=metrics,
                windows=windows,
                plot_as_log=plot_as_log,
                datetime_interval=datetime_interval,
                colors=colors,
            )

        return df
