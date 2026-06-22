"""Common helper functions."""
from typing import Any, Optional
import math
import re

from src.config_loader import CONSUMER_CATEGORIES


def first_number(x: Any) -> Optional[float]:
    """Extract first numeric value from nested structure."""
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, list):
        for item in x:
            v = first_number(item)
            if v is not None:
                return v
    return None


def infer_input_srid(geom: dict) -> int:
    """Infer SRID from geometry coordinates.
    Polygons drawn in the UI sometimes come as EPSG:3857 (values >> 180).
    """
    first = first_number(geom.get("coordinates"))
    return 3857 if (first is not None and abs(first) > 180) else 4326


def safe_float(value) -> Optional[float]:
    """Convert NaN/None to None for JSON serialization."""
    if value is None:
        return None
    try:
        if math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _normalize_f_class(value: str) -> str:
    norm = (value or "").strip().lower()
    norm = re.sub(r"[\s\-/]+", "_", norm)
    norm = re.sub(r"[^a-z0-9_]", "", norm)
    norm = re.sub(r"_+", "_", norm).strip("_")
    return norm or "yes"


_CONSUMER_DEFINITIONS = set()
try:
    if CONSUMER_CATEGORIES is not None and not CONSUMER_CATEGORIES.empty:
        _CONSUMER_DEFINITIONS = {
            _normalize_f_class(str(v))
            for v in CONSUMER_CATEGORIES.get("definition", []).tolist()
        }
except Exception:
    _CONSUMER_DEFINITIONS = set()


def get_building_type_from_class(f_class: str, area: float) -> str:
    """Map custom-building f_class to a stored building_type value.

    For configured classes, keep the normalized granular f_class directly.
    This avoids collapsing hundreds of valid classes into a few legacy buckets.
    """
    fc = _normalize_f_class(f_class)
    aliases = {
        "semi_detached": "semidetached_house",
        "semi-detached": "semidetached_house",
        "town_house": "terrace",
        "community_center": "community_centre",
        "doctor": "doctors",
    }
    fc = aliases.get(fc, fc)

    if fc in _CONSUMER_DEFINITIONS:
        return fc

    # Legacy compatibility for coarse labels.
    if fc == "residential":
        if area < 150:
            return "house"
        if area < 400:
            return "terrace"
        return "apartments"
    if fc in {"commercial", "public", "industrial", "agricultural", "infrastructure"}:
        return fc
    return "commercial"


def get_building_icon(f_class: str) -> str:
    """Get default icon for building class."""
    fc = _normalize_f_class(f_class)
    icon_map = {
        'residential': 'home',
        'commercial': 'building-2',
        'industrial': 'industrial',
        'public': 'building-2',
        'agricultural': 'warehouse',
        'infrastructure': 'building-2',
    }
    if any(k in fc for k in ("house", "apartment", "residential", "dormitory", "villa", "terrace")):
        return 'home'
    return icon_map.get(fc, 'building-2')
