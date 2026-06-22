"""
Utility functions for the data pipeline.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Setup logging
def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure logging for the pipeline."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger("datapipeline")

logger = setup_logging()


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


def get_pipeline_root() -> Path:
    """Get the datapipeline root directory."""
    return Path(__file__).resolve().parent.parent


def load_yaml_config(config_name: str) -> Dict[str, Any]:
    """Load a YAML configuration file from the config directory."""
    config_path = get_pipeline_root() / "config" / config_name
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_regions_config() -> Dict[str, Any]:
    """Load the regions configuration."""
    return load_yaml_config("regions.yaml")


def load_settings() -> Dict[str, Any]:
    """Load the settings configuration."""
    return load_yaml_config("settings.yaml")


def get_region_config(country: str, state: Optional[str] = None) -> Dict[str, Any]:
    """
    Get configuration for a specific region.
    
    Args:
        country: Country key (e.g., 'germany', 'austria')
        state: Optional state key for countries with states (e.g., 'bayern')
    
    Returns:
        Region configuration dictionary
    """
    regions = load_regions_config()
    
    if country not in regions:
        available = list(regions.keys())
        raise ValueError(f"Country '{country}' not found. Available: {available}")
    
    country_config = regions[country]
    
    if state:
        if "states" not in country_config:
            raise ValueError(f"Country '{country}' does not have state subdivisions")
        
        if state not in country_config["states"]:
            available = list(country_config["states"].keys())
            raise ValueError(f"State '{state}' not found in {country}. Available: {available}")
        
        state_config = country_config["states"][state]
        # Inherit country-level settings
        return {
            "country": country,
            "country_name": country_config["name"],
            "state": state,
            "name": state_config["name"],
            "osm_relation_id": state_config["osm_relation_id"],
            "geofabrik_url": state_config.get("geofabrik_url", country_config.get("geofabrik_url")),
            "crs": country_config.get("crs", "EPSG:3035"),
            "nuts_code": state_config.get("nuts_code"),
            "ags": state_config.get("ags")
        }
    
    return {
        "country": country,
        "name": country_config["name"],
        "osm_relation_id": country_config["osm_relation_id"],
        "geofabrik_url": country_config["geofabrik_url"],
        "crs": country_config.get("crs", "EPSG:3035"),
        "nuts_code": country_config.get("nuts_code")
    }


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_directory() -> Path:
    """
    Get the cache directory for PBF files.
    
    Returns:
        Path to the cache directory
    """
    settings = load_settings()
    cache_dir = get_pipeline_root() / settings["geofabrik"]["cache_dir"]
    return ensure_directory(cache_dir)


def get_pbf_cache_path(region_config: Dict[str, Any]) -> Path:
    """
    Get the cached PBF file path for a region.
    
    Args:
        region_config: Region configuration from get_region_config()
    
    Returns:
        Path to the cached PBF file
    """
    cache_dir = get_cache_directory()
    geofabrik_url = region_config["geofabrik_url"]
    pbf_name = geofabrik_url.split("/")[-1]
    return cache_dir / pbf_name


def get_output_directory(region_config: Dict[str, Any], data_type: str) -> Path:
    """
    Get the output directory for a specific data type and region.
    
    Args:
        region_config: Region configuration from get_region_config()
        data_type: Type of data (e.g., 'transformers', 'buildings', 'ways')
    
    Returns:
        Path to the output directory
    """
    settings = load_settings()
    base_dir = get_pipeline_root() / settings["output"]["base_dir"]
    
    # Create region-specific path
    if "state" in region_config:
        region_path = base_dir / region_config["country"] / region_config["state"]
    else:
        region_path = base_dir / region_config["country"]
    
    output_path = region_path / data_type
    return ensure_directory(output_path)


def list_available_regions() -> Dict[str, Any]:
    """List all available regions and states."""
    regions = load_regions_config()
    result = {}
    
    for country_key, country_data in regions.items():
        if "states" in country_data:
            result[country_key] = {
                "name": country_data["name"],
                "states": {k: v["name"] for k, v in country_data["states"].items()}
            }
        else:
            result[country_key] = {"name": country_data["name"]}
    
    return result


def copy_local_pbf(source_path: Path, region_config: Dict[str, Any]) -> Path:
    """
    Copy a local PBF file to the cache directory.
    
    Args:
        source_path: Path to the local PBF file
        region_config: Region configuration
    
    Returns:
        Path to the cached PBF file
    """
    import shutil
    
    if not source_path.exists():
        raise FileNotFoundError(f"PBF file not found: {source_path}")
    
    cache_path = get_pbf_cache_path(region_config)
    
    if cache_path.exists():
        logger.info(f"PBF already in cache: {cache_path}")
        return cache_path
    
    logger.info(f"Copying PBF to cache: {source_path} -> {cache_path}")
    shutil.copy2(source_path, cache_path)
    
    return cache_path
