#!/usr/bin/env python
# -*- coding: utf-8 -*-

from magma_rsam.rsam import RSAM
from magma_rsam.dash import app
from magma_rsam.plot_rsam import PlotRsam
from pkg_resources import get_distribution

__version__ = get_distribution("magma-rsam").version
__author__ = "Martanto"
__author_email__ = "martanto@live.com"
__license__ = "MIT"
__copyright__ = "Copyright (c) 2024, MAGMA Indonesia"
__url__ = "https://github.com/martanto/magma-rsam"

__all__ = [
    "RSAM",
    "PlotRsam",
]
