# magma-rsam
Python package to calculating RSAM Value

```python
from magma_rsam import RSAM, PlotRsam

rsam = RSAM(
    seismic_dir="G:\\Output\\Converted\\SDS",
    station='AWU1',
    channel='EHZ',
    network = 'VG',
    location = '00',
    start_date = '2024-01-01',
    end_date = '2024-07-31',
    directory_structure = 'sds' # check https://github.com/martanto/magma-converter for supported directory
)
```

Apply filter:
```python
rsam.apply_filter(freq_min=5.0, freq_max=18.0)
```

Run RSAM calculation:
```python
rsam.run()
```

## Plot RSAM
```python
plot_rsam = PlotRsam(
    station = 'AWU1',
    channel = 'EHZ',
    network = 'VG',
    location = '00',
    start_date = '2024-01-01',
    end_date = '2024-07-31',
    resample = '10min'
)
```

Plot using filter:
```python
plot_rsam.with_filter(
    freq_min=5.0,
    freq_max=18.0
)
```

Set `y_limit`:
```python
plot_rsam.set_y_lim(
    y_min=0,
    y_max=1200
)
```

Run plot:
```python
plot_rsam.run(
    metrics = ['mean', 'median'],
    windows = ['1d'],
    plot_as_log = False,
    datetime_interval = 7,
    colors = ['#FFEB3B', '#F44336'] # colors must have the same length of metrics*windows
)
```