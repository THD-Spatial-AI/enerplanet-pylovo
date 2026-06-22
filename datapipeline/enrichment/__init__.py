"""
Enrichment modules for enhancing building data with external open datasets.

Available enrichers:
- BAG3DEnricher: 3D BAG data (floors, height, construction year, BAG ID)
- EPOnlineEnricher: EP-Online energy labels
- CBSEnricher: CBS population and household statistics
- EUBUCCOEnricher: EUBUCCO building characteristics (floors, height, age)
- CUZKLidarEnricher: CUZK LiDAR 3D height data (Czech Republic)
- NRWLidarEnricher: NRW DOM1/DGM1 LiDAR-derived building heights
- SachsenLidarEnricher: Saxony official DGM1/DOM1 LiDAR-derived building heights
- ThueringenLidarEnricher: Thuringia official DGM1/DOM1 LiDAR-derived building heights
"""

from .bag3d import BAG3DEnricher
from .ep_online import EPOnlineEnricher
from .cbs import CBSEnricher
from .eubucco import EUBUCCOEnricher

# Lazy import: CUZKLidarEnricher requires laspy/rasterstats which may not be installed
try:
    from .cuzk_lidar import CUZKLidarEnricher
except ImportError:
    CUZKLidarEnricher = None

# Lazy import: German LiDAR enrichers require rasterio which may not be installed
try:
    from .german_open_lidar import (
        NRWLidarEnricher,
        SachsenLidarEnricher,
        ThueringenLidarEnricher,
    )
except ImportError:
    NRWLidarEnricher = None
    SachsenLidarEnricher = None
    ThueringenLidarEnricher = None

__all__ = [
    "BAG3DEnricher",
    "EPOnlineEnricher",
    "CBSEnricher",
    "EUBUCCOEnricher",
    "CUZKLidarEnricher",
    "NRWLidarEnricher",
    "SachsenLidarEnricher",
    "ThueringenLidarEnricher",
]
