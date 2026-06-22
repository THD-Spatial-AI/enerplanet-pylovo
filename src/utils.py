import osm2geojson
import pandas as pd
import requests
import shutil
import math
from pathlib import Path
import logging


def reset_log_directory():
    # Delete and recreate the log directory (preserving .gitkeep)
    log_dir = Path("log")
    if log_dir.exists():
        # Remove all files except .gitkeep
        for item in log_dir.iterdir():
            if item.name != ".gitkeep":
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        # Ensure the directory exists
        log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir

def create_logger(name, log_file, log_level):
    log_file = log_file
    logger = logging.getLogger(name=name)
    logger.handlers.clear()  # Clear existing handlers to prevent duplication

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # to print log messages to a file
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # to print log messages to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.setLevel(log_level)
    logger.propagate = False

    return logger


def simultaneousPeakLoad(buildings_df, consumer_cat_df, vertice_ids):
    # Calculates the simultaneous peak load of buildings with given vertice ids
    _, total_sim_load = diversifiedLoadPerConsumer(
        buildings_df,
        consumer_cat_df,
        consumer_ids=vertice_ids,
        consumer_id_col="connection_point",
    )
    if pd.isna(total_sim_load):
        return 0
    return total_sim_load


def diversifiedLoadPerConsumer(buildings_df, consumer_cat_df, consumer_ids=None, consumer_id_col="vertice_id"):
    """Allocate diversified load to individual consumers while preserving cluster total.

    The cluster total is calculated with the same simultaneity logic used by clustering.
    That diversified total is then distributed back to consumers proportionally to
    their installed power within each parent category so downstream electrical models
    inject the same total load that clustering used for transformer sizing.
    """
    consumer_id_list = list(consumer_ids) if consumer_ids is not None else []
    if buildings_df is None or len(buildings_df) == 0:
        empty = {consumer_id: 0.0 for consumer_id in consumer_id_list}
        return empty, 0.0

    if consumer_id_col not in buildings_df.columns:
        raise KeyError(f"Missing consumer id column '{consumer_id_col}' in buildings dataframe")

    if consumer_ids is None:
        subset_df = buildings_df.copy()
        consumer_id_list = subset_df[consumer_id_col].dropna().tolist()
    else:
        subset_df = buildings_df[buildings_df[consumer_id_col].isin(consumer_id_list)].copy()

    diversified_by_consumer = {consumer_id: 0.0 for consumer_id in consumer_id_list}
    if subset_df.empty:
        return diversified_by_consumer, 0.0

    type_to_parent = _get_type_to_parent_map(consumer_cat_df)
    sim_factors = _get_sim_factors(consumer_cat_df)

    subset_df["parent_category"] = subset_df["f_class"].map(type_to_parent).fillna("commercial")
    subset_df["peak_load_in_kw"] = pd.to_numeric(subset_df["peak_load_in_kw"], errors="coerce").fillna(0.0)
    subset_df["households_per_building"] = pd.to_numeric(
        subset_df["households_per_building"], errors="coerce"
    ).fillna(0.0)

    total_sim_load = 0.0
    for parent_cat, group in subset_df.groupby("parent_category", dropna=False):
        installed_power = float(group["peak_load_in_kw"].sum())
        load_count = float(group["households_per_building"].sum())
        if installed_power <= 0 or load_count <= 0:
            continue

        sim_factor = sim_factors.get(parent_cat, 0.50)
        diversified_kw = float(oneSimultaneousLoad(installed_power, load_count, sim_factor))
        if diversified_kw <= 0:
            continue

        total_sim_load += diversified_kw
        weights = group["peak_load_in_kw"].clip(lower=0.0)
        weight_sum = float(weights.sum())
        if weight_sum <= 0:
            weights = pd.Series(1.0, index=group.index)
            weight_sum = float(len(group.index))

        allocations = diversified_kw * weights / weight_sum
        for consumer_id, consumer_kw in allocations.groupby(group[consumer_id_col]).sum().items():
            diversified_by_consumer[consumer_id] = diversified_by_consumer.get(consumer_id, 0.0) + float(consumer_kw)

    return diversified_by_consumer, total_sim_load


def _get_type_to_parent_map(consumer_cat_df):
    """Build parent_category lookup (cached-friendly helper)."""
    if 'parent_category' in consumer_cat_df.columns:
        return consumer_cat_df.set_index('definition')['parent_category'].to_dict()
    elif {'definition', 'load_method'}.issubset(set(consumer_cat_df.columns)):
        return {
            row['definition']: ('residential' if row.get('load_method') == 'household' else 'commercial')
            for _, row in consumer_cat_df.iterrows()
        }
    return {}


def _get_sim_factors(consumer_cat_df):
    """Extract sim_factor per parent_category."""
    if 'parent_category' in consumer_cat_df.columns:
        return consumer_cat_df.groupby('parent_category')['sim_factor'].first().to_dict()
    return {}


def precompute_node_loads(buildings_df, consumer_cat_df):
    """Precompute per-node aggregated loads for incremental sim load calculation.
    Returns dict: {node_id: {parent_cat: (installed_power, load_count)}}
    """
    type_to_parent = _get_type_to_parent_map(consumer_cat_df)
    df = buildings_df.copy()
    df['parent_category'] = df['f_class'].map(type_to_parent).fillna('commercial')

    node_loads = {}
    for node_id, group in df.groupby('connection_point'):
        cat_loads = {}
        for parent_cat, cat_group in group.groupby('parent_category'):
            installed_power = cat_group["peak_load_in_kw"].values.sum()
            load_count = cat_group['households_per_building'].values.sum()
            if load_count > 0:
                cat_loads[parent_cat] = (installed_power, load_count)
        node_loads[node_id] = cat_loads
    return node_loads


def incrementalSimLoad(cumulative_loads, sim_factors):
    """Calculate sim load from cumulative per-category (installed_power, load_count) totals."""
    total = 0
    for parent_cat, (power, count) in cumulative_loads.items():
        if count > 0:
            sf = sim_factors.get(parent_cat, 0.50)
            total += oneSimultaneousLoad(power, count, sf)
    if pd.isna(total):
        return 0
    return total


def oneSimultaneousLoad(installed_power, load_count, sim_factor):
    # calculation of the simultaneaous load of multiple consumers of the same kind (public, commercial or residential)
    # Safe guards: invalid/zero/negative inputs yield 0.
    if installed_power is None or load_count is None or sim_factor is None:
        return 0
    try:
        installed_power = float(installed_power)
        load_count = float(load_count)
        sim_factor = float(sim_factor)
    except (TypeError, ValueError):
        return 0
    if not (math.isfinite(installed_power) and math.isfinite(load_count) and math.isfinite(sim_factor)):
        return 0
    if installed_power <= 0 or load_count <= 0:
        return 0
    sim_load = installed_power * (sim_factor + (1 - sim_factor) * (load_count ** (-3 / 4)))
    if not math.isfinite(sim_load) or sim_load < 0:
        return 0

    return sim_load


def required_apparent_power_kva(real_power_kw, power_factor, loading_margin=1.0):
    """Convert diversified real power in kW to required transformer apparent power in kVA."""
    if real_power_kw is None or power_factor is None or loading_margin is None:
        return 0.0
    try:
        real_power_kw = float(real_power_kw)
        power_factor = float(power_factor)
        loading_margin = float(loading_margin)
    except (TypeError, ValueError):
        return 0.0
    if not (math.isfinite(real_power_kw) and math.isfinite(power_factor) and math.isfinite(loading_margin)):
        return 0.0
    if real_power_kw <= 0:
        return 0.0
    if power_factor <= 0 or power_factor > 1:
        apparent_power = real_power_kw
    else:
        apparent_power = real_power_kw / power_factor
    if loading_margin <= 0:
        loading_margin = 1.0
    return apparent_power * loading_margin


def required_line_current_ka(real_power_kw, voltage_v, power_factor, voltage_factor=1.0):
    """Convert diversified real power in kW to three-phase line current in kA."""
    if real_power_kw is None or voltage_v is None:
        return 0.0
    try:
        real_power_kw = float(real_power_kw)
        voltage_v = float(voltage_v)
        voltage_factor = float(voltage_factor)
    except (TypeError, ValueError):
        return 0.0
    if not (math.isfinite(real_power_kw) and math.isfinite(voltage_v) and math.isfinite(voltage_factor)):
        return 0.0
    if real_power_kw <= 0 or voltage_v <= 0:
        return 0.0
    apparent_kva = required_apparent_power_kva(real_power_kw, power_factor, loading_margin=1.0)
    effective_voltage = voltage_v * voltage_factor
    if effective_voltage <= 0:
        return 0.0
    return apparent_kva / (effective_voltage * math.sqrt(3))


def osmjson_to_geojson(osmjson: dict[str, str]) -> dict[str, str]:
    """Convert JSON dict received from overpass api to GeoJSON dictionary.

    Args:
        osmjson: JSON dictionary received from overpass api

    Returns:
        dict: GeoJSON representation of osmjson

    """
    geojson = osm2geojson.json2geojson(osmjson)

    # put attributes in "tags" directly into "properties"
    for feature in geojson['features']:
        if "tags" in feature["properties"]:
            feature["properties"].update(feature["properties"].pop("tags"))

    return geojson


def query_overpass_for_geojson(overpass_url: str, query: str) -> dict[str, str]:
    """Execute an overpass turbo query and convert results to GeoJSON.

    Args:
        overpass_url: Overpass API URL
        query: Query string

    Returns:
        dict: GeoJSON representation of overpass results

    """
    # call api for data
    response = requests.get(overpass_url, params={'data': query})
    response.raise_for_status()

    # convert JSON data to GeoJSON format
    osmjson = response.json()
    geojson = osmjson_to_geojson(osmjson)

    return geojson
